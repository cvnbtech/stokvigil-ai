import json
import logging
import re
import time
import urllib.parse
import urllib.request
import concurrent.futures
from collections import OrderedDict
from datetime import timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from fastapi import APIRouter, HTTPException, Depends, Query, Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
import yfinance as yf

from app.core.rate_limiter import check_rate_limit
from app.core.dependencies import is_indian_market_open
from app.market_cache import market_cache
from app.engine.deterministic import compute_tactical_levels
from app.technical_engine import calculate_camarilla_pivots, calculate_vwap_bands, calculate_ttm_squeeze

logger = logging.getLogger("stokvigil.routers.stocks")
router = APIRouter(tags=["stocks"])

# Strict alphanumeric regex whitelist for stock symbols (supports .NS and .BO exchange suffixes)
STOCK_SYMBOL_REGEX = re.compile(r'^[A-Z0-9_\-&.]{1,25}$')

# In-memory bounded quote cache with max 2000 items (FIFO eviction) to prevent memory exhaustion
_QUOTE_CACHE: OrderedDict[str, Dict[str, Any]] = OrderedDict()
_QUOTE_CACHE_TTL = 20.0  # Default 20 seconds during market hours
_MAX_QUOTE_CACHE_SIZE = 2000

# Indian Standard Time (IST = UTC+5:30) for accurate market hour detection
IST = timezone(timedelta(hours=5, minutes=30))


def get_quote_cache_ttl() -> float:
    """
    Dynamic Market-Aware Cache TTL:
    - Active Market Hours (Mon-Fri 09:15-15:30 IST): 20.0 seconds.
    - Off-Market Hours & Weekends: 300.0 seconds (5 minutes).
    """
    return 20.0 if is_indian_market_open() else 300.0


# Singleton Keep-Alive HTTP Session with connection pooling across all worker threads
_QUOTE_HTTP_SESSION = requests.Session()
_adapter = HTTPAdapter(
    pool_connections=25,
    pool_maxsize=25,
    max_retries=Retry(total=1, backoff_factor=0.2, status_forcelist=[502, 503, 504])
)
_QUOTE_HTTP_SESSION.mount("https://", _adapter)
_QUOTE_HTTP_SESSION.mount("http://", _adapter)
_QUOTE_HTTP_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://finance.yahoo.com/"
})

# Persistent, bounded ThreadPoolExecutor for concurrent batch stock quote queries
# Eliminates per-request thread churn, reducing Cloud Run CPU spikes & latency
_STOCK_QUOTE_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=20,
    thread_name_prefix="stokvigil_quote_worker"
)


def shutdown_quote_executor():
    """Gracefully drains and terminates the persistent quote worker pool."""
    try:
        _STOCK_QUOTE_EXECUTOR.shutdown(wait=False, cancel_futures=True)
    except Exception as e:
        logger.debug(f"Note on shutting down quote executor: {e}")


def _cache_set_quote(sym: str, data: Dict[str, Any], timestamp: float):
    if len(_QUOTE_CACHE) >= _MAX_QUOTE_CACHE_SIZE:
        _QUOTE_CACHE.popitem(last=False)  # Evict oldest entry (FIFO)
    _QUOTE_CACHE[sym] = {"data": data, "timestamp": timestamp}


def _fetch_single_stock_quote(sym: str) -> Optional[Dict[str, Any]]:
    if not sym or not STOCK_SYMBOL_REGEX.match(sym):
        return None

    clean_sym = sym.replace(".NS", "").replace(".BO", "").strip().upper()
    is_explicit_bse = sym.endswith(".BO") or (clean_sym.isdigit() and len(clean_sym) == 6)
    candidate_suffixes = [(".BO", "BSE"), (".NS", "NSE")] if is_explicit_bse else [(".NS", "NSE"), (".BO", "BSE")]

    # Step 1: Check in-memory market cache first (< 0.05ms)
    cached_stock = market_cache.get_stock(clean_sym) or market_cache.get_stock(sym)
    if cached_stock:
        p = cached_stock.get("current_price") or cached_stock.get("price")
        if p and float(p) > 0:
            tech = cached_stock.get("technicals") or {}
            chg_pct = tech.get("change_pct")
            prev = tech.get("prev_close")
            if chg_pct is None and prev:
                chg_pct = round(((float(p) - float(prev)) / float(prev)) * 100, 2)

            if chg_pct is not None:
                day_high = tech.get("day_high")
                day_low = tech.get("day_low")

                cached_tactical = cached_stock.get("tactical_levels", {})
                t1 = cached_tactical.get("target_1")
                s1 = cached_tactical.get("protective_stop_loss")
                target_val = t1 if (t1 and t1 not in ["-", "₹0", "0"]) else None
                sl_val = s1 if (s1 and s1 not in ["-", "₹0", "0"]) else None
                trailing_sl = cached_tactical.get("atr_trailing_stop")
                volatility_regime = cached_tactical.get("volatility_regime") or "STANDARD_CAMARILLA"
                is_high_beta = bool(cached_tactical.get("is_high_beta_event", False))
                bias = cached_stock.get("action_bias")
                signal = None
                signal_type = None
                if bias and bias != "DATA_UNAVAILABLE":
                    if bias == "HOLD_NEUTRAL":
                        # ZERO-DEFAULT POLICY: HOLD_NEUTRAL represents neutral baseline, not an active trade signal
                        signal = None
                        signal_type = None
                    elif "BUY" in bias:
                        signal = bias.replace("_", " ")
                        signal_type = "strong_buy"
                    elif "SELL" in bias or "EXIT" in bias:
                        signal = bias.replace("_", " ")
                        signal_type = "sell"
                    else:
                        signal = None
                        signal_type = None

                if not signal:
                    target_val = None
                    sl_val = None
                    trailing_sl = None

                exch = "BSE" if is_explicit_bse else "NSE"
                cached_name = cached_stock.get("name") or (f"{clean_sym} (BSE)" if is_explicit_bse else f"{clean_sym} (NSE)")

                return {
                    "symbol": clean_sym,
                    "full_symbol": f"{clean_sym}.BO" if is_explicit_bse else f"{clean_sym}.NS",
                    "clean_symbol": clean_sym,
                    "name": cached_name,
                    "exchange": exch,
                    "price": round(float(p), 2),
                    "change_pct": round(float(chg_pct), 2),
                    "is_positive": float(chg_pct) >= 0,
                    "day_high": round(float(day_high), 2) if day_high is not None else None,
                    "day_low": round(float(day_low), 2) if day_low is not None else None,
                    "target": target_val,
                    "stop_loss": sl_val,
                    "trailing_sl": trailing_sl,
                    "volatility_regime": volatility_regime,
                    "is_high_beta": is_high_beta,
                    "buffered_breakout_level": cached_tactical.get("buffered_breakout_level"),
                    "buffered_breakdown_level": cached_tactical.get("buffered_breakdown_level"),
                    "signal": signal,
                    "signal_type": signal_type,
                    "disclaimer": "Mathematical volatility benchmarks (1.5x / 2.5x ATR). Not an advisory target or price promise."
                }

    # Step 2: Fetch via Yahoo Finance Chart API with pooled Keep-Alive session & dual-host fallbacks
    for suffix, exch in candidate_suffixes:
        for host in ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]:
            try:
                url = f"https://{host}/v8/finance/chart/{clean_sym}{suffix}?range=5d&interval=1d"
                res = _QUOTE_HTTP_SESSION.get(url, timeout=2.0)
                if res.status_code == 404:
                    break
                if res.status_code == 200:
                    data = res.json()
                    res_list = data.get("chart", {}).get("result")
                    if res_list and len(res_list) > 0:
                        meta = res_list[0].get("meta", {})
                        p = meta.get("regularMarketPrice")
                        if p is not None and float(p) > 0:
                            prev = meta.get("chartPreviousClose") or meta.get("previousClose") or p
                            chg_pct = round(((float(p) - float(prev)) / float(prev)) * 100, 2) if prev else 0.0
                            name = meta.get("shortName") or meta.get("longName") or f"{clean_sym} ({exch})"
                            raw_high = meta.get("regularMarketDayHigh")
                            raw_low = meta.get("regularMarketDayLow")
                            day_high = round(float(raw_high), 2) if raw_high is not None else None
                            day_low = round(float(raw_low), 2) if raw_low is not None else None

                            h_val = float(raw_high) if raw_high is not None else float(p)
                            l_val = float(raw_low) if raw_low is not None else float(p)
                            c_prev = float(prev) if prev is not None else float(p)

                            # Extract completed prior-day (D-1) bar for static horizontal Camarilla pivots
                            quotes = res_list[0].get("indicators", {}).get("quote", [{}])[0]
                            raw_highs = [float(v) for v in quotes.get("high", []) if v is not None and not (isinstance(v, float) and np.isnan(v))]
                            raw_lows = [float(v) for v in quotes.get("low", []) if v is not None and not (isinstance(v, float) and np.isnan(v))]
                            raw_closes = [float(v) for v in quotes.get("close", []) if v is not None and not (isinstance(v, float) and np.isnan(v))]

                            h_prev = None
                            l_prev = None
                            if len(raw_highs) >= 2 and len(raw_lows) >= 2:
                                h_prev = raw_highs[-2]
                                l_prev = raw_lows[-2]
                                if len(raw_closes) >= 2:
                                    c_prev = raw_closes[-2]
                            elif len(raw_highs) == 1 and len(raw_lows) == 1:
                                h_prev = raw_highs[0]
                                l_prev = raw_lows[0]

                            ref_high = h_prev if h_prev is not None else h_val
                            ref_low = l_prev if l_prev is not None else l_val
                            true_range = max(ref_high - ref_low, abs(ref_high - c_prev), abs(ref_low - c_prev)) if (float(p) > 0) else 0.0

                            h4 = round(c_prev + (true_range * 1.1 / 2.0), 2) if (true_range > 0 and c_prev > 0) else None
                            h3 = round(c_prev + (true_range * 1.1 / 4.0), 2) if (true_range > 0 and c_prev > 0) else None
                            l3 = round(c_prev - (true_range * 1.1 / 4.0), 2) if (true_range > 0 and c_prev > 0) else None
                            l4 = round(c_prev - (true_range * 1.1 / 2.0), 2) if (true_range > 0 and c_prev > 0) else None

                            cached_stock = market_cache.get_stock(clean_sym) or market_cache.get_stock(sym)
                            target_val = None
                            sl_val = None
                            signal = None
                            signal_type = None
                            if cached_stock:
                                cached_tactical = cached_stock.get("tactical_levels", {})
                                t1 = cached_tactical.get("target_1")
                                s1 = cached_tactical.get("protective_stop_loss")
                                target_val = t1 if (t1 and t1 not in ["-", "₹0", "0"]) else None
                                sl_val = s1 if (s1 and s1 not in ["-", "₹0", "0"]) else None
                                bias = cached_stock.get("action_bias")
                                if bias and bias != "DATA_UNAVAILABLE":
                                    if bias == "HOLD_NEUTRAL":
                                        signal = None
                                        signal_type = None
                                    elif "BUY" in bias:
                                        signal = bias.replace("_", " ")
                                        signal_type = "strong_buy"
                                    elif "SELL" in bias or "EXIT" in bias:
                                        signal = bias.replace("_", " ")
                                        signal_type = "sell"
                                    else:
                                        signal = None
                                        signal_type = None

                            trailing_sl_val = None
                            is_high_beta_val = False
                            regime_val = "STANDARD_CAMARILLA"
                            buf_h4_val = None
                            buf_l4_val = None

                            if (not target_val or not sl_val) and true_range > 0 and float(p) > 0 and h3 and l4:
                                tactical = compute_tactical_levels(
                                    current_price=float(p),
                                    atr_val=true_range,
                                    h3=h3,
                                    h4=h4,
                                    l3=l3,
                                    l4=l4,
                                    action_bias="HOLD_NEUTRAL",
                                    day_high=day_high,
                                    day_low=day_low
                                )
                                if tactical:
                                    target_val = tactical.get("target_1")
                                    sl_val = tactical.get("protective_stop_loss")
                                    trailing_sl_val = tactical.get("atr_trailing_stop")
                                    is_high_beta_val = bool(tactical.get("is_high_beta_event", False))
                                    regime_val = tactical.get("volatility_regime", "STANDARD_CAMARILLA")
                                    buf_h4_val = tactical.get("buffered_breakout_level")
                                    buf_l4_val = tactical.get("buffered_breakdown_level")
                                if l4 and float(p) <= float(l4):
                                    signal = "STOP LOSS EXIT"
                                    signal_type = "danger"
                                    target_val = "CUT RISK"
                                    sl_val = f"₹{l4:,.2f} BREACHED"
                                elif not signal and true_range > 0 and h3 and l3:
                                    atr_buf = (true_range * 0.25) if is_high_beta_val else (true_range * 0.10)
                                    raw_buf_h4 = (h4 + atr_buf) if h4 else None
                                    raw_buf_l4 = (l4 - atr_buf) if l4 else None
                                    if raw_buf_h4 and float(p) >= raw_buf_h4:
                                        signal = "STRONG BUY"
                                        signal_type = "strong_buy"
                                        target_val = f"₹{(h4 + (true_range * 0.5)):,.2f}"
                                        sl_val = f"₹{h3:,.2f}"
                                    elif h3 and float(p) >= float(h3):
                                        signal = "BUY"
                                        signal_type = "buy"
                                        target_val = f"₹{h4:,.2f}"
                                        sl_val = f"₹{l3:,.2f}"
                                    elif (raw_buf_l4 and float(p) <= raw_buf_l4) or (l4 and float(p) <= float(l4)):
                                        signal = "STOP LOSS EXIT"
                                        signal_type = "danger"
                                        target_val = "CUT RISK"
                                        sl_val = f"₹{l4:,.2f} BREACHED"
                                    elif l3 and float(p) <= float(l3):
                                        signal = "SELL"
                                        signal_type = "sell"
                                        target_val = f"₹{l4:,.2f}"
                                        sl_val = f"₹{h3:,.2f}"
                                    else:
                                        signal = None
                                        signal_type = None
                                        target_val = None
                                        sl_val = None
                                        trailing_sl_val = None
                                elif not signal:
                                    signal = None
                                    signal_type = None
                                    target_val = None
                                    sl_val = None
                                    trailing_sl_val = None

                            quote_result = {
                                "symbol": clean_sym,
                                "full_symbol": f"{clean_sym}{suffix}",
                                "clean_symbol": clean_sym,
                                "name": name,
                                "exchange": exch,
                                "price": round(float(p), 2),
                                "change_pct": chg_pct,
                                "is_positive": chg_pct >= 0,
                                "day_high": day_high,
                                "day_low": day_low,
                                "target": target_val,
                                "stop_loss": sl_val,
                                "trailing_sl": trailing_sl_val,
                                "volatility_regime": regime_val,
                                "is_high_beta": is_high_beta_val,
                                "buffered_breakout_level": buf_h4_val,
                                "buffered_breakdown_level": buf_l4_val,
                                "signal": signal,
                                "signal_type": signal_type,
                                "disclaimer": "Mathematical volatility benchmarks (1.5x / 2.5x ATR). Not an advisory target or price promise."
                            }

                            if not cached_stock:
                                market_cache.update_live_tick(clean_sym, ltp=float(p), high=day_high, low=day_low)

                            return quote_result
            except Exception:
                continue

    # Step 3: Fast yfinance history fallback
    for suffix, exch in candidate_suffixes:
        try:
            t = yf.Ticker(f"{clean_sym}{suffix}")
            df = t.history(period="5d", interval="1d")
            if not df.empty:
                last_row = df.iloc[-1]
                p = float(last_row["Close"])
                prev = float(last_row["Open"]) if "Open" in last_row else p
                chg_pct = round(((p - prev) / prev) * 100, 2) if prev else 0.0
                day_high = round(float(last_row["High"]), 2) if "High" in last_row else None
                day_low = round(float(last_row["Low"]), 2) if "Low" in last_row else None
                clean_name = f"{clean_sym} ({exch})"
                try:
                    fast = t.fast_info
                    clean_name = getattr(fast, "short_name", None) or getattr(fast, "long_name", None) or clean_name
                except Exception:
                    pass

                h_val = float(day_high) if day_high is not None else float(p)
                l_val = float(day_low) if day_low is not None else float(p)
                c_prev = float(prev) if prev is not None else float(p)

                # Extract completed prior-day (D-1) bar for static horizontal Camarilla pivots
                if len(df) >= 2:
                    ref_row = df.iloc[-2]
                    h_prev = float(ref_row["High"])
                    l_prev = float(ref_row["Low"])
                    c_prev = float(ref_row["Close"])
                else:
                    h_prev = h_val
                    l_prev = l_val

                true_range = max(h_prev - l_prev, abs(h_prev - c_prev), abs(l_prev - c_prev)) if (float(p) > 0) else 0.0

                h4 = round(c_prev + (true_range * 1.1 / 2.0), 2) if (true_range > 0 and c_prev > 0) else None
                h3 = round(c_prev + (true_range * 1.1 / 4.0), 2) if (true_range > 0 and c_prev > 0) else None
                l3 = round(c_prev - (true_range * 1.1 / 4.0), 2) if (true_range > 0 and c_prev > 0) else None
                l4 = round(c_prev - (true_range * 1.1 / 2.0), 2) if (true_range > 0 and c_prev > 0) else None

                cached_stock = market_cache.get_stock(clean_sym) or market_cache.get_stock(sym)
                target_val = None
                sl_val = None
                signal = None
                signal_type = None
                if cached_stock:
                    cached_tactical = cached_stock.get("tactical_levels", {})
                    t1 = cached_tactical.get("target_1")
                    s1 = cached_tactical.get("protective_stop_loss")
                    target_val = t1 if (t1 and t1 not in ["-", "₹0", "0"]) else None
                    sl_val = s1 if (s1 and s1 not in ["-", "₹0", "0"]) else None
                    bias = cached_stock.get("action_bias")
                    if bias and bias != "DATA_UNAVAILABLE":
                        if bias == "HOLD_NEUTRAL":
                            signal = None
                            signal_type = None
                        elif "BUY" in bias:
                            signal = bias.replace("_", " ")
                            signal_type = "strong_buy"
                        elif "SELL" in bias or "EXIT" in bias:
                            signal = bias.replace("_", " ")
                            signal_type = "sell"
                        else:
                            signal = None
                            signal_type = None

                trailing_sl_val = None
                is_high_beta_val = False
                regime_val = "STANDARD_CAMARILLA"
                buf_h4_val = None
                buf_l4_val = None

                if (not target_val or not sl_val) and true_range > 0 and float(p) > 0 and h3 and l4:
                    tactical = compute_tactical_levels(
                        current_price=float(p),
                        atr_val=true_range,
                        h3=h3,
                        h4=h4,
                        l3=l3,
                        l4=l4,
                        action_bias="HOLD_NEUTRAL",
                        day_high=day_high,
                        day_low=day_low
                    )
                    if tactical:
                        target_val = tactical.get("target_1")
                        sl_val = tactical.get("protective_stop_loss")
                        trailing_sl_val = tactical.get("atr_trailing_stop")
                        is_high_beta_val = bool(tactical.get("is_high_beta_event", False))
                        regime_val = tactical.get("volatility_regime", "STANDARD_CAMARILLA")
                        buf_h4_val = tactical.get("buffered_breakout_level")
                        buf_l4_val = tactical.get("buffered_breakdown_level")
                    if l4 and float(p) <= float(l4):
                        signal = "STOP LOSS EXIT"
                        signal_type = "danger"
                        target_val = "CUT RISK"
                        sl_val = f"₹{l4:,.2f} BREACHED"
                    elif not signal and true_range > 0 and h3 and l3:
                        atr_buf = (true_range * 0.25) if is_high_beta_val else (true_range * 0.10)
                        raw_buf_h4 = (h4 + atr_buf) if h4 else None
                        raw_buf_l4 = (l4 - atr_buf) if l4 else None
                        if raw_buf_h4 and float(p) >= raw_buf_h4:
                            signal = "STRONG BUY"
                            signal_type = "strong_buy"
                            target_val = f"₹{(h4 + (true_range * 0.5)):,.2f}"
                            sl_val = f"₹{h3:,.2f}"
                        elif h3 and float(p) >= float(h3):
                            signal = "BUY"
                            signal_type = "buy"
                            target_val = f"₹{h4:,.2f}"
                            sl_val = f"₹{l3:,.2f}"
                        elif (raw_buf_l4 and float(p) <= raw_buf_l4) or (l4 and float(p) <= float(l4)):
                            signal = "STOP LOSS EXIT"
                            signal_type = "danger"
                            target_val = "CUT RISK"
                            sl_val = f"₹{l4:,.2f} BREACHED"
                        elif l3 and float(p) <= float(l3):
                            signal = "SELL"
                            signal_type = "sell"
                            target_val = f"₹{l4:,.2f}"
                            sl_val = f"₹{h3:,.2f}"
                        else:
                            signal = None
                            signal_type = None
                            target_val = None
                            sl_val = None
                            trailing_sl_val = None
                    elif not signal:
                        signal = None
                        signal_type = None
                        target_val = None
                        sl_val = None
                        trailing_sl_val = None

                quote_result = {
                    "symbol": clean_sym,
                    "full_symbol": f"{clean_sym}{suffix}",
                    "clean_symbol": clean_sym,
                    "name": clean_name,
                    "exchange": exch,
                    "price": round(p, 2),
                    "change_pct": chg_pct,
                    "is_positive": chg_pct >= 0,
                    "day_high": day_high,
                    "day_low": day_low,
                    "target": target_val,
                    "stop_loss": sl_val,
                    "trailing_sl": trailing_sl_val,
                    "volatility_regime": regime_val,
                    "is_high_beta": is_high_beta_val,
                    "buffered_breakout_level": buf_h4_val,
                    "buffered_breakdown_level": buf_l4_val,
                    "signal": signal,
                    "signal_type": signal_type,
                    "disclaimer": "Mathematical volatility benchmarks (1.5x / 2.5x ATR). Not an advisory target or price promise."
                }

                if not cached_stock:
                    market_cache.update_live_tick(clean_sym, ltp=float(p), high=day_high, low=day_low)

                return quote_result
        except Exception:
            continue

    return None


@router.get("/api/stocks/search", dependencies=[Depends(check_rate_limit)])
def search_stocks(q: str = Query(..., min_length=1)):
    """
    Dynamically searches live NSE & BSE Indian stocks via Yahoo Finance API.
    Zero hardcoded stock names. Returns verified matching equities in real-time.
    """
    query = q.strip()
    if not query:
        return {"stocks": []}

    results = []
    seen_symbols = set()

    search_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    for host in ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]:
        try:
            url = f"https://{host}/v1/finance/search?q={urllib.parse.quote(query)}&quotesCount=10&newsCount=0"
            req = urllib.request.Request(url, headers=search_headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode('utf-8'))
                for item in data.get("quotes", []):
                    sym = item.get("symbol", "")
                    quote_type = item.get("quoteType", "")
                    if quote_type != "EQUITY":
                        continue

                    clean_sym = sym
                    exchange = "NSE"
                    if sym.endswith(".NS"):
                        clean_sym = sym[:-3]
                        exchange = "NSE"
                    elif sym.endswith(".BO"):
                        clean_sym = sym[:-3]
                        exchange = "BSE"
                    elif item.get("exchange") in ["NSI", "NSE"]:
                        exchange = "NSE"
                    elif item.get("exchange") in ["BOM", "BSE"]:
                        exchange = "BSE"
                    else:
                        continue

                    if clean_sym in seen_symbols or clean_sym.startswith("0P"):
                        continue
                    seen_symbols.add(clean_sym)

                    name = item.get("longname") or item.get("shortname") or clean_sym
                    sector = item.get("sector") or item.get("industry") or f"{exchange} Listed"

                    results.append({
                        "symbol": clean_sym,
                        "name": name,
                        "exchange": exchange,
                        "full_symbol": sym,
                        "sector": sector
                    })
                    if len(results) >= 5:
                        break
            if results:
                break
        except Exception as e:
            logger.warning(f"Live stock search on {host} failed for '{query}': {e}")

    # Fallback to direct yfinance validation if search query was exact symbol
    if not results and len(query) >= 2:
        clean_q = query.strip().upper()
        suffixes = [(".BO", "BSE"), (".NS", "NSE")] if (clean_q.isdigit() and len(clean_q) == 6) else [(".NS", "NSE"), (".BO", "BSE")]
        for suffix, exch in suffixes:
            try:
                t = yf.Ticker(f"{clean_q}{suffix}")
                fast = t.fast_info
                price = getattr(fast, "last_price", None)
                if price is not None and price > 0:
                    results.append({
                        "symbol": clean_q,
                        "name": f"{clean_q} ({exch})",
                        "exchange": exch,
                        "full_symbol": f"{clean_q}{suffix}",
                        "sector": f"{exch} Listed"
                    })
                    break
            except Exception:
                continue

    return {"stocks": results[:5]}


@router.get("/api/stocks/validate", dependencies=[Depends(check_rate_limit)])
def validate_stock(symbol: str = Query(..., min_length=1)):
    """
    Dynamically validates in real-time whether a ticker exists on NSE or BSE.
    Strictly returns is_valid: False for dummy or non-traded symbols (e.g. NE, ASDF).
    """
    sym = symbol.strip().upper()
    clean_sym = sym.replace(".NS", "").replace(".BO", "").strip().upper()
    is_explicit_bse = sym.endswith(".BO") or (clean_sym.isdigit() and len(clean_sym) == 6)
    candidate_suffixes = [(".BO", "BSE"), (".NS", "NSE")] if is_explicit_bse else [(".NS", "NSE"), (".BO", "BSE")]

    if len(clean_sym) < 2 and not clean_sym.isdigit():
        return {
            "is_valid": False,
            "symbol": clean_sym or sym,
            "error": f"'{sym}' is too short. Please enter a valid stock symbol."
        }

    if not STOCK_SYMBOL_REGEX.match(sym):
        return {
            "is_valid": False,
            "symbol": clean_sym or sym,
            "error": f"'{sym}' contains invalid characters. Use valid alphanumeric stock symbols."
        }

    search_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    }

    # 1. Fast quote API multi-exchange lookup (NSE and BSE)
    try:
        symbols_param = f"{clean_sym}.BO,{clean_sym}.NS" if is_explicit_bse else f"{clean_sym}.NS,{clean_sym}.BO"
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbols_param}"
        req = urllib.request.Request(url, headers=search_headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            results = data.get("quoteResponse", {}).get("result", [])
            for q in results:
                q_sym = q.get("symbol", "")
                price = q.get("regularMarketPrice")
                if price is not None and price > 0:
                    exch = "NSE" if q_sym.endswith(".NS") else "BSE"
                    name = q.get("shortName") or q.get("longName") or f"{clean_sym} ({exch})"
                    return {
                        "is_valid": True,
                        "symbol": clean_sym,
                        "clean_symbol": clean_sym,
                        "name": name,
                        "exchange": exch,
                        "price": price,
                        "full_symbol": q_sym
                    }
    except Exception as e:
        logger.warning(f"Fast quote validation for {sym} failed: {e}")

    # 2. Fast chart API validation
    for suffix, exch in candidate_suffixes:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{clean_sym}{suffix}?range=1d&interval=1d"
            req = urllib.request.Request(url, headers=search_headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                res_list = data.get("chart", {}).get("result")
                if res_list and len(res_list) > 0:
                    meta = res_list[0].get("meta", {})
                    price = meta.get("regularMarketPrice")
                    if price is not None and price > 0:
                        name = meta.get("shortName") or meta.get("longName") or f"{clean_sym} ({exch})"
                        return {
                            "is_valid": True,
                            "symbol": clean_sym,
                            "clean_symbol": clean_sym,
                            "name": name,
                            "exchange": exch,
                            "price": price,
                            "full_symbol": f"{clean_sym}{suffix}"
                        }
        except Exception:
            pass

    # 3. Direct fast_info ticker check
    for suffix, exch in candidate_suffixes:
        try:
            t = yf.Ticker(f"{clean_sym}{suffix}")
            fast = t.fast_info
            price = getattr(fast, "last_price", None)
            if price is not None and price > 0:
                clean_name = f"{clean_sym} ({exch})"
                try:
                    clean_name = getattr(fast, "short_name", None) or getattr(fast, "long_name", None) or clean_name
                except Exception:
                    pass
                return {
                    "is_valid": True,
                    "symbol": clean_sym,
                    "clean_symbol": clean_sym,
                    "name": clean_name,
                    "exchange": exch,
                    "price": float(price),
                    "full_symbol": f"{clean_sym}{suffix}"
                }
        except Exception:
            continue

    return {
        "is_valid": False,
        "symbol": clean_sym or sym,
        "error": f"'{sym}' is not a valid listed stock on NSE or BSE."
    }


@router.get("/api/stocks/quotes", dependencies=[Depends(check_rate_limit)])
def get_batch_stock_quotes(symbols: str = Query(..., description="Comma-separated stock symbols")):
    """
    Fetches real-time market prices, day % change, and metadata for multiple stocks.
    Supports 200+ stocks concurrently with market-aware dynamic RAM caching & Keep-Alive pooling.
    """
    if not symbols:
        return {"quotes": {}}

    raw_symbols = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not raw_symbols:
        return {"quotes": {}}

    unique_symbols = [s for s in list(dict.fromkeys(raw_symbols)) if STOCK_SYMBOL_REGEX.match(s)]
    now = time.time()
    current_ttl = get_quote_cache_ttl()
    results: Dict[str, Dict[str, Any]] = {}
    missing_symbols: List[str] = []

    for sym in unique_symbols:
        cached = _QUOTE_CACHE.get(sym)
        if not cached:
            clean_s = sym.replace(".NS", "").replace(".BO", "").strip()
            cached = _QUOTE_CACHE.get(clean_s)

        if cached and (now - cached["timestamp"] < current_ttl):
            results[sym] = cached["data"]
            clean_k = cached["data"].get("clean_symbol")
            if clean_k and clean_k not in results:
                results[clean_k] = cached["data"]
            full_k = cached["data"].get("full_symbol")
            if full_k and full_k not in results:
                results[full_k] = cached["data"]
        else:
            missing_symbols.append(sym)

    if missing_symbols:
        future_to_sym = {_STOCK_QUOTE_EXECUTOR.submit(_fetch_single_stock_quote, sym): sym for sym in missing_symbols}
        for future in concurrent.futures.as_completed(future_to_sym):
                sym = future_to_sym[future]
                try:
                    q_data = future.result()
                    if q_data:
                        results[sym] = q_data
                        _cache_set_quote(sym, q_data, now)

                        clean_k = q_data.get("clean_symbol")
                        if clean_k:
                            if clean_k not in results:
                                results[clean_k] = q_data
                            _cache_set_quote(clean_k, q_data, now)

                        full_k = q_data.get("full_symbol")
                        if full_k:
                            if full_k not in results:
                                results[full_k] = q_data
                            _cache_set_quote(full_k, q_data, now)
                except Exception as e:
                    logger.warning(f"Error fetching quote for {sym}: {e}")

    # Enrich quotes with pre-computed institutional market cache analysis (signals, targets, stop-loss)
    for sym_key, q_dict in list(results.items()):
        if not isinstance(q_dict, dict):
            continue
        clean_s = q_dict.get("clean_symbol") or sym_key.replace(".NS", "").replace(".BO", "").strip().upper()
        pack = market_cache.get_stock(clean_s) or market_cache.get_stock(sym_key)
        if pack:
            analysis = pack.get("analysis", {})
            tactical = analysis.get("tactical_levels") or pack.get("tactical_levels", {})
            tech = pack.get("technicals", {})
            bias = analysis.get("action_bias") or pack.get("action_bias")
            score = pack.get("confluence_score") or analysis.get("confluence_score")
            if score is not None:
                q_dict["confluence_score"] = score
            if bias and bias not in ["HOLD_NEUTRAL", "DATA_UNAVAILABLE"]:
                t1 = tactical.get("target_1") or tactical.get("tactical_resistance_1")
                sl = tactical.get("protective_stop_loss")
                if t1 and sl and t1 not in ["-", "₹0", "0"] and sl not in ["-", "₹0", "0"]:
                    q_dict["signal"] = bias.replace("_", " ")
                    q_dict["action_bias"] = bias
                    q_dict["signal_type"] = "strong_buy" if "BUY" in bias else "sell"
                    q_dict["target"] = t1
                    q_dict["stop_loss"] = sl
                    tsl = tactical.get("trailing_stop_loss")
                    if tsl:
                        q_dict["trailing_sl"] = tsl
            if q_dict.get("change_pct") is None and tech.get("change_pct") is not None:
                q_dict["change_pct"] = tech.get("change_pct")

    return {"quotes": results}


@router.get("/api/stocks/{symbol}/analysis", dependencies=[Depends(check_rate_limit)])
async def get_single_stock_analysis(
    symbol: str = Path(..., description="Stock symbol (e.g. TATAMOTORS, RELIANCE)")
):
    """
    Returns instant institutional analysis (< 1ms from RAM cache if precomputed,
    or on-demand dynamic calculation) for any watchlist stock.
    """
    clean_sym = symbol.replace(".NS", "").replace(".BO", "").strip().upper()
    pack = market_cache.get_stock(clean_sym)
    if not pack:
        from app.agent_runner import evaluate_single_symbol_full
        pack = await evaluate_single_symbol_full(clean_sym)
    return {
        "symbol": clean_sym,
        "price": pack.get("current_price"),
        "confluence_score": pack.get("confluence_score"),
        "action_bias": pack.get("action_bias"),
        "tactical_levels": pack.get("tactical_levels"),
        "technicals": pack.get("technicals"),
        "flow_data": pack.get("flow_data"),
        "forensics": pack.get("forensics"),
        "analysis": pack.get("analysis")
    }


# Dynamic In-Memory Candle Cache (TTL: 180s for intraday, 14400s for daily/hourly)
_CANDLE_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}

def get_candle_cache_ttl(interval: str) -> float:
    """
    Intraday intervals (1m, 5m, 15m) are refreshed every 180 seconds (3 min).
    Higher timeframe intervals (1h, 1d) are held for 14,400 seconds (4 hours).
    """
    if interval in ["1h", "1d"]:
        return 14400.0
    return 180.0


def _parse_v8_chart_to_df(chart_data: Dict[str, Any]) -> pd.DataFrame:
    """
    Converts Yahoo v8 chart JSON response into a normalized pandas DataFrame
    indexed by Asia/Kolkata DatetimeIndex with OHLCV numeric columns.
    Filters out malformed or null rows.
    """
    try:
        results = chart_data.get("chart", {}).get("result")
        if not results:
            return pd.DataFrame()
        first_result = results[0]
        timestamps = first_result.get("timestamp")
        if not timestamps:
            return pd.DataFrame()
        quote_list = first_result.get("indicators", {}).get("quote", [])
        if not quote_list:
            return pd.DataFrame()
        quote = quote_list[0]
        opens = quote.get("open", [])
        highs = quote.get("high", [])
        lows = quote.get("low", [])
        closes = quote.get("close", [])
        volumes = quote.get("volume", [])

        rows = []
        vol_len = len(volumes) if volumes else 0
        for i, t in enumerate(timestamps):
            if t is None:
                continue
            o = opens[i] if i < len(opens) else None
            h = highs[i] if i < len(highs) else None
            l = lows[i] if i < len(lows) else None
            c = closes[i] if i < len(closes) else None
            if o is None or h is None or l is None or c is None:
                continue
            v = volumes[i] if i < vol_len and volumes[i] is not None else 0
            rows.append({
                "timestamp": t,
                "Open": float(o),
                "High": float(h),
                "Low": float(l),
                "Close": float(c),
                "Volume": int(v)
            })

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df.index = pd.to_datetime(df["timestamp"], unit="s", utc=True).dt.tz_convert("Asia/Kolkata")
        df.drop(columns=["timestamp"], inplace=True)
        return df
    except Exception as e:
        logger.warning(f"Error parsing Yahoo v8 chart data: {e}")
        return pd.DataFrame()


def _fetch_v8_candles_df(clean_sym: str, interval: str, period: str) -> Tuple[pd.DataFrame, Optional[str]]:
    """
    Fetches OHLCV candlestick data directly from Yahoo Finance v8 chart API using persistent Keep-Alive
    HTTP connection pooling (_QUOTE_HTTP_SESSION) with automatic host failover (query1 -> query2)
    and dual-exchange suffix resolution (.NS / .BO).
    Strictly avoids heavy, blocking yfinance dependencies.
    """
    clean = clean_sym.strip().upper()
    if clean.endswith(".NS") or clean.endswith(".BO"):
        candidates = [clean]
    elif clean.isdigit():
        candidates = [f"{clean}.BO", f"{clean}.NS"]
    else:
        candidates = [f"{clean}.NS", f"{clean}.BO"]

    for target_sym in candidates:
        for host in ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]:
            try:
                url = f"https://{host}/v8/finance/chart/{target_sym}?range={period}&interval={interval}"
                res = _QUOTE_HTTP_SESSION.get(url, timeout=3.5)
                if res.status_code == 404:
                    # Symbol not found on this exchange, avoid trying query2
                    break
                if res.status_code == 200:
                    df = _parse_v8_chart_to_df(res.json())
                    if not df.empty:
                        return df, target_sym
            except Exception as e:
                logger.debug(f"Direct v8 candle fetch error for {target_sym} on {host}: {e}")
                continue
    return pd.DataFrame(), None


@router.get("/api/stocks/candles", dependencies=[Depends(check_rate_limit)])
def get_stock_candles(
    symbol: str = Query(..., min_length=1, max_length=20),
    interval: str = Query("5m"),
    period: str = Query("5d")
):
    """
    Returns OHLCV Candlestick data for TradingView lightweight-charts,
    overlaid with Camarilla Equation Pivots (H4, H3, L3, L4), VWAP, and Chandelier Trailing Stop.
    Pure Direct Yahoo v8 Chart ingestion with sub-second latency and zero yfinance dependency.
    """
    clean_sym = symbol.strip().upper()
    if not STOCK_SYMBOL_REGEX.match(clean_sym):
        raise HTTPException(status_code=400, detail="Invalid stock symbol format.")

    if interval not in ["1m", "5m", "15m", "1h", "1d"]:
        interval = "5m"
    if period not in ["1d", "5d", "1mo", "3mo", "1y"]:
        period = "5d"

    cache_key = f"{clean_sym}:{interval}:{period}"
    now = time.time()
    ttl = get_candle_cache_ttl(interval)
    if cache_key in _CANDLE_CACHE:
        ts, cached_payload = _CANDLE_CACHE[cache_key]
        if (now - ts) < ttl:
            return cached_payload

    df_candles, resolved_sym = _fetch_v8_candles_df(clean_sym, interval, period)

    if df_candles.empty:
        return {
            "symbol": clean_sym,
            "interval": interval,
            "period": period,
            "candles": [],
            "camarilla": None,
            "ttm_squeeze": None,
            "vwap_bands": None
        }

    try:
        vwap_bands_info = calculate_vwap_bands(df_candles)
        vwap_series = vwap_bands_info.get("vwap_series")
        std_dev_series = vwap_bands_info.get("std_dev_series")
    except Exception:
        vwap_bands_info = {}
        vwap_series = None
        std_dev_series = None

    try:
        ttm_squeeze_info = calculate_ttm_squeeze(df_candles)
    except Exception:
        ttm_squeeze_info = None

    try:
        high_low = df_candles["High"] - df_candles["Low"]
        high_close = (df_candles["High"] - df_candles["Close"].shift()).abs()
        low_close = (df_candles["Low"] - df_candles["Close"].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr_14 = tr.rolling(window=14, min_periods=1).mean()
        rolling_high = df_candles["High"].rolling(window=22, min_periods=1).max()
        chandelier_sl_series = (rolling_high - (2.5 * atr_14)).round(2)
    except Exception:
        chandelier_sl_series = None

    # Camarilla Equation Pivots (H4, H3, L3, L4) from prior completed session (D-1)
    camarilla = None
    if interval == "1d":
        camarilla = calculate_camarilla_pivots(df_candles)
    else:
        # Intraday: query prior daily bars for resolved ticker via pooled session (~100-150ms)
        target_sym_daily = resolved_sym or clean_sym
        df_daily, _ = _fetch_v8_candles_df(target_sym_daily, interval="1d", period="10d")
        if not df_daily.empty:
            camarilla = calculate_camarilla_pivots(df_daily)
        elif len(df_candles.index.normalize().unique()) >= 2:
            # Fallback: synthesize daily session bars from intraday candles
            df_daily_synth = df_candles.groupby(df_candles.index.date).agg({
                "Open": "first",
                "High": "max",
                "Low": "min",
                "Close": "last",
                "Volume": "sum"
            })
            camarilla = calculate_camarilla_pivots(df_daily_synth)

    candles = []
    for idx, row in df_candles.iterrows():
        try:
            bar_time = int(idx.timestamp())
            raw_vwap = float(vwap_series.loc[idx]) if (vwap_series is not None and not vwap_series.empty and idx in vwap_series) else None
            c_vwap = raw_vwap if (raw_vwap is not None and not pd.isna(raw_vwap)) else None

            raw_sd = float(std_dev_series.loc[idx]) if (std_dev_series is not None and not std_dev_series.empty and idx in std_dev_series) else None
            c_sd = raw_sd if (raw_sd is not None and not pd.isna(raw_sd)) else None

            c_u1 = (c_vwap + c_sd) if (c_vwap is not None and c_sd is not None) else None
            c_l1 = max(0.01, c_vwap - c_sd) if (c_vwap is not None and c_sd is not None) else None

            raw_sl = float(chandelier_sl_series.loc[idx]) if (chandelier_sl_series is not None and not chandelier_sl_series.empty and idx in chandelier_sl_series) else None
            c_sl = raw_sl if (raw_sl is not None and not pd.isna(raw_sl)) else None

            r_open = float(row["Open"]) if not pd.isna(row["Open"]) else None
            r_high = float(row["High"]) if not pd.isna(row["High"]) else None
            r_low = float(row["Low"]) if not pd.isna(row["Low"]) else None
            r_close = float(row["Close"]) if not pd.isna(row["Close"]) else None

            candles.append({
                "time": bar_time,
                "open": round(r_open, 2) if r_open is not None else None,
                "high": round(r_high, 2) if r_high is not None else None,
                "low": round(r_low, 2) if r_low is not None else None,
                "close": round(r_close, 2) if r_close is not None else None,
                "volume": int(row.get("Volume", 0)) if not pd.isna(row.get("Volume", 0)) else 0,
                "vwap": round(c_vwap, 2) if c_vwap is not None else None,
                "vwap_upper_1s": round(c_u1, 2) if c_u1 is not None and not pd.isna(c_u1) else None,
                "vwap_lower_1s": round(c_l1, 2) if c_l1 is not None and not pd.isna(c_l1) else None,
                "chandelier_sl": round(c_sl, 2) if c_sl is not None else None
            })
        except Exception:
            continue

    payload = {
        "symbol": clean_sym,
        "interval": interval,
        "period": period,
        "candles": candles,
        "camarilla": camarilla,
        "ttm_squeeze": ttm_squeeze_info,
        "vwap_bands": {
            "vwap": vwap_bands_info.get("vwap"),
            "vwap_upper_1s": vwap_bands_info.get("vwap_upper_1s"),
            "vwap_lower_1s": vwap_bands_info.get("vwap_lower_1s"),
            "vwap_upper_2s": vwap_bands_info.get("vwap_upper_2s"),
            "vwap_lower_2s": vwap_bands_info.get("vwap_lower_2s")
        } if vwap_bands_info.get("vwap") is not None else None
    }
    if len(_CANDLE_CACHE) > 200:
        oldest_keys = sorted(_CANDLE_CACHE.keys(), key=lambda k: _CANDLE_CACHE[k][0])[:50]
        for k in oldest_keys:
            _CANDLE_CACHE.pop(k, None)
    _CANDLE_CACHE[cache_key] = (now, payload)
    return payload
