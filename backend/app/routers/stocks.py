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
from fastapi import APIRouter, HTTPException, Depends, Query
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
import yfinance as yf

from app.core.rate_limiter import check_rate_limit
from app.core.dependencies import is_indian_market_open
from app.market_cache import market_cache
from app.agent_runner import compute_tactical_levels
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
                bias = cached_stock.get("action_bias")
                signal = None
                signal_type = None
                if bias:
                    if bias == "HOLD_NEUTRAL":
                        signal = "HOLD"
                        signal_type = "hold"
                    elif "BUY" in bias:
                        signal = bias.replace("_", " ")
                        signal_type = "strong_buy"
                    elif "SELL" in bias or "EXIT" in bias:
                        signal = bias.replace("_", " ")
                        signal_type = "sell"
                    else:
                        signal = bias.replace("_", " ")
                        signal_type = "hold"

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
                    "signal": signal,
                    "signal_type": signal_type,
                    "disclaimer": "Mathematical volatility benchmarks (1.5x / 2.5x ATR). Not an advisory target or price promise."
                }

    # Step 2: Fetch via Yahoo Finance Chart API with pooled Keep-Alive session & dual-host fallbacks
    for suffix, exch in candidate_suffixes:
        for host in ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]:
            try:
                url = f"https://{host}/v8/finance/chart/{clean_sym}{suffix}?range=1d&interval=1d"
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
                            true_range = max(h_val - l_val, abs(h_val - c_prev), abs(l_val - c_prev)) if (float(p) > 0) else 0.0

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
                                if bias:
                                    if bias == "HOLD_NEUTRAL":
                                        signal = "HOLD"
                                        signal_type = "hold"
                                    elif "BUY" in bias:
                                        signal = bias.replace("_", " ")
                                        signal_type = "strong_buy"
                                    elif "SELL" in bias or "EXIT" in bias:
                                        signal = bias.replace("_", " ")
                                        signal_type = "sell"
                                    else:
                                        signal = bias.replace("_", " ")
                                        signal_type = "hold"

                            if (not target_val or not sl_val) and true_range > 0 and float(p) > 0 and h3 and l4:
                                tactical = compute_tactical_levels(
                                    current_price=float(p),
                                    atr_val=true_range,
                                    h3=h3,
                                    h4=h4,
                                    l3=l3,
                                    l4=l4,
                                    action_bias="HOLD_NEUTRAL"
                                )
                                if tactical:
                                    target_val = tactical.get("target_1")
                                    sl_val = tactical.get("protective_stop_loss")
                                if not signal:
                                    signal = "HOLD"
                                    signal_type = "hold"

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
            df = t.history(period="1d", interval="1d")
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
                true_range = max(h_val - l_val, abs(h_val - c_prev), abs(l_val - c_prev)) if (float(p) > 0) else 0.0

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
                    if bias:
                        if bias == "HOLD_NEUTRAL":
                            signal = "HOLD"
                            signal_type = "hold"
                        elif "BUY" in bias:
                            signal = bias.replace("_", " ")
                            signal_type = "strong_buy"
                        elif "SELL" in bias or "EXIT" in bias:
                            signal = bias.replace("_", " ")
                            signal_type = "sell"
                        else:
                            signal = bias.replace("_", " ")
                            signal_type = "hold"

                if (not target_val or not sl_val) and true_range > 0 and float(p) > 0 and h3 and l4:
                    tactical = compute_tactical_levels(
                        current_price=float(p),
                        atr_val=true_range,
                        h3=h3,
                        h4=h4,
                        l3=l3,
                        l4=l4,
                        action_bias="HOLD_NEUTRAL"
                    )
                    if tactical:
                        target_val = tactical.get("target_1")
                        sl_val = tactical.get("protective_stop_loss")
                    if not signal:
                        signal = "HOLD"
                        signal_type = "hold"

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
        max_workers = min(15, max(1, len(missing_symbols)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_to_sym = {pool.submit(_fetch_single_stock_quote, sym): sym for sym in missing_symbols}
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

    return {"quotes": results}


# In-Memory Candle Cache (TTL 60 seconds)
_CANDLE_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}

@router.get("/api/stocks/candles", dependencies=[Depends(check_rate_limit)])
def get_stock_candles(
    symbol: str = Query(..., min_length=1, max_length=20),
    interval: str = Query("5m"),
    period: str = Query("5d")
):
    """
    Returns OHLCV Candlestick data for TradingView lightweight-charts,
    overlaid with Camarilla Equation Pivots (H4, H3, L3, L4), VWAP, and Chandelier Trailing Stop.
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
    if cache_key in _CANDLE_CACHE:
        ts, cached_payload = _CANDLE_CACHE[cache_key]
        if (now - ts) < 60.0:
            return cached_payload

    df_candles = pd.DataFrame()
    candidates = [clean_sym] if (clean_sym.endswith(".NS") or clean_sym.endswith(".BO")) else [f"{clean_sym}.NS", f"{clean_sym}.BO"]
    for sym_to_try in candidates:
        try:
            t = yf.Ticker(sym_to_try)
            df_try = t.history(period=period, interval=interval)
            if not df_try.empty:
                df_candles = df_try
                break
        except Exception:
            continue

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
        vwap_series = df_candles["Close"]
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
        chandelier_sl_series = (df_candles["Close"] * 0.96).round(2)

    camarilla = None
    for sym_to_try in candidates:
        try:
            t_daily = yf.Ticker(sym_to_try)
            df_daily = t_daily.history(period="10d", interval="1d")
            if not df_daily.empty:
                camarilla = calculate_camarilla_pivots(df_daily)
                break
        except Exception as e:
            logger.debug(f"Daily Camarilla fetch error for {sym_to_try}: {e}")

    candles = []
    for idx, row in df_candles.iterrows():
        try:
            bar_time = int(idx.timestamp())
            c_vwap = float(vwap_series.loc[idx]) if (vwap_series is not None and idx in vwap_series) else None
            c_sd = float(std_dev_series.loc[idx]) if (std_dev_series is not None and idx in std_dev_series) else None
            c_u1 = (c_vwap + c_sd) if (c_vwap is not None and c_sd is not None) else None
            c_l1 = max(0.01, c_vwap - c_sd) if (c_vwap is not None and c_sd is not None) else None
            c_sl = float(chandelier_sl_series.loc[idx]) if idx in chandelier_sl_series else None
            candles.append({
                "time": bar_time,
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row.get("Volume", 0)),
                "vwap": round(c_vwap, 2) if c_vwap is not None and not pd.isna(c_vwap) else None,
                "vwap_upper_1s": round(c_u1, 2) if c_u1 is not None and not pd.isna(c_u1) else None,
                "vwap_lower_1s": round(c_l1, 2) if c_l1 is not None and not pd.isna(c_l1) else None,
                "chandelier_sl": round(c_sl, 2) if c_sl is not None and not pd.isna(c_sl) else None
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
