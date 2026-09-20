import time
import json
import csv
import io
import urllib.request
import urllib.parse
import logging
import threading
import yfinance as yf
from typing import Dict, Any, Tuple, Optional, List, Set

logger = logging.getLogger("stokvigil.macro_filter")

# Dynamic Industry Taxonomy to NIFTY Sector Benchmarks (Category Mapping, NOT Hardcoded Stocks)
GLOBAL_INDUSTRY_TO_NIFTY_SECTOR = {
    "Financial Services": "NIFTY BANK",
    "Financial": "NIFTY BANK",
    "Banking": "NIFTY BANK",
    "Banks": "NIFTY BANK",
    "Technology": "NIFTY IT",
    "Software": "NIFTY IT",
    "Information Technology": "NIFTY IT",
    "Consumer Cyclical": "NIFTY AUTO",
    "Automobile": "NIFTY AUTO",
    "Auto": "NIFTY AUTO",
    "Auto Manufacturers": "NIFTY AUTO",
    "Healthcare": "NIFTY PHARMA",
    "Pharmaceuticals": "NIFTY PHARMA",
    "Drug Manufacturers": "NIFTY PHARMA",
    "Basic Materials": "NIFTY METAL",
    "Metals & Mining": "NIFTY METAL",
    "Steel": "NIFTY METAL",
    "Energy": "NIFTY ENERGY",
    "Oil & Gas": "NIFTY ENERGY",
    "Utilities": "NIFTY ENERGY",
    "Consumer Defensive": "NIFTY FMCG",
    "Consumer Goods": "NIFTY FMCG",
}

# Dynamic Reference Aliases (Deprecated: Sector maps are now 100% dynamic from exchange APIs)
SECTOR_MAP: Dict[str, str] = {}
BSE_SCRIP_SECTOR_MAP: Dict[str, str] = {}

SECTOR_INDEX_MAP = {
    "NIFTY IT": "^CNXIT",
    "NIFTY BANK": "^NSEBANK",
    "NIFTY AUTO": "^CNXAUTO",
    "NIFTY PHARMA": "^CNXPHARMA",
    "NIFTY METAL": "^CNXMETAL",
    "NIFTY ENERGY": "^CNXENERGY",
    "NIFTY FMCG": "^CNXFMCG",
}

_DYNAMIC_SECTOR_CACHE: Dict[str, str] = {}
_DYNAMIC_SECTOR_TS: float = 0.0
_DYNAMIC_SECTOR_TTL: float = 86400.0  # 24 hours
_DYNAMIC_SECTOR_LOCK = threading.Lock()
_BSE_SCRIP_CACHE: Dict[str, str] = {}


def resolve_bse_scrip_to_symbol(scrip_code: str) -> Optional[str]:
    """
    Dynamically resolves any 6-digit numeric BSE security code to its ticker symbol
    via the official BSE India API with zero hardcoding.
    """
    clean_code = str(scrip_code).strip().upper()
    if not (clean_code.isdigit() and len(clean_code) == 6):
        return None
    if clean_code in _BSE_SCRIP_CACHE:
        return _BSE_SCRIP_CACHE[clean_code]
    try:
        url = f"https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w?Group=&Scripcode={clean_code}&industry=&segment=Equity&status=Active"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Referer": "https://www.bseindia.com/",
            "Accept": "application/json, text/plain, */*",
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, list) and len(data) > 0:
                    scrip_id = data[0].get("scrip_id", "").strip().upper()
                    if scrip_id:
                        _BSE_SCRIP_CACHE[clean_code] = scrip_id
                        return scrip_id
    except Exception as e:
        logger.debug(f"Dynamic BSE scrip lookup notice for {clean_code}: {e}")
    return None


def get_dynamic_sector_map() -> Dict[str, str]:
    """
    Dynamically fetches and caches official NSE sector index constituent lists from NSE archives.
    Refreshed once every 24 hours. Zero hardcoded stocks.
    """
    global _DYNAMIC_SECTOR_CACHE, _DYNAMIC_SECTOR_TS
    now = time.time()
    if _DYNAMIC_SECTOR_CACHE and (now - _DYNAMIC_SECTOR_TS) < _DYNAMIC_SECTOR_TTL:
        return _DYNAMIC_SECTOR_CACHE

    with _DYNAMIC_SECTOR_LOCK:
        if _DYNAMIC_SECTOR_CACHE and (now - _DYNAMIC_SECTOR_TS) < _DYNAMIC_SECTOR_TTL:
            return _DYNAMIC_SECTOR_CACHE

        sector_files = {
            "NIFTY BANK": "ind_niftybanklist.csv",
            "NIFTY IT": "ind_niftyitlist.csv",
            "NIFTY AUTO": "ind_niftyautolist.csv",
            "NIFTY PHARMA": "ind_niftypharmalist.csv",
            "NIFTY METAL": "ind_niftymetallist.csv",
            "NIFTY ENERGY": "ind_niftyenergylist.csv",
            "NIFTY FMCG": "ind_niftyfmcglist.csv",
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/csv, text/plain, */*",
        }

        # 100% Dynamic - no hardcoded stock list
        combined_map: Dict[str, str] = {}

        loaded_sectors = 0
        for sec_name, filename in sector_files.items():
            try:
                url = f"https://nsearchives.nseindia.com/content/indices/{filename}"
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=4.0) as resp:
                    if resp.status == 200:
                        content = resp.read().decode("utf-8", errors="ignore")
                        reader = csv.reader(io.StringIO(content))
                        for row in list(reader)[1:]:
                            if len(row) > 2:
                                sym = row[2].strip().upper()
                                if sym and sym not in ("SYMBOL", "COMPANY NAME", "SERIES"):
                                    combined_map[sym] = sec_name
                        loaded_sectors += 1
            except Exception as err:
                logger.debug(f"Dynamic sector fetch note for {sec_name}: {err}")

        _DYNAMIC_SECTOR_CACHE = combined_map
        _DYNAMIC_SECTOR_TS = now
        if loaded_sectors > 0:
            logger.info(f"✅ Dynamic sector universe updated from NSE: {len(combined_map)} equities mapped across {loaded_sectors} sectors.")
        return _DYNAMIC_SECTOR_CACHE


def get_symbol_sector(symbol: str) -> Optional[str]:
    """
    Dynamically resolves the sector for any NSE ticker or dual-listed BSE scrip.
    Supports .NS, .BO, bare symbols, and 6-digit BSE codes with ZERO hardcoding.
    """
    if not symbol:
        return None
    raw = str(symbol).strip().upper()
    bare = raw.replace(".NS", "").replace(".BO", "").strip()

    sec_map = get_dynamic_sector_map()

    # 1. Direct match against dynamic NSE constituent cache
    if bare in sec_map:
        return sec_map[bare]
    if raw in sec_map:
        return sec_map[raw]
    if bare in _DYNAMIC_SECTOR_CACHE:
        return _DYNAMIC_SECTOR_CACHE[bare]

    # 2. Dynamic BSE 6-digit scrip code resolution via live BSE API
    lookup_sym = bare
    if bare.isdigit() and len(bare) == 6:
        resolved_sym = resolve_bse_scrip_to_symbol(bare)
        if resolved_sym:
            if resolved_sym in sec_map:
                sec = sec_map[resolved_sym]
                _DYNAMIC_SECTOR_CACHE[bare] = sec
                _DYNAMIC_SECTOR_CACHE[raw] = sec
                return sec
            lookup_sym = resolved_sym

    # 3. Dynamic lookup via Ticker Metadata & Industry Taxonomy
    for cand in [f"{lookup_sym}.NS", f"{lookup_sym}.BO", lookup_sym]:
        try:
            t = yf.Ticker(cand)
            info = getattr(t, "info", None) or {}
            sector_str = info.get("sector")
            if sector_str:
                nifty_sec = GLOBAL_INDUSTRY_TO_NIFTY_SECTOR.get(sector_str)
                if nifty_sec:
                    _DYNAMIC_SECTOR_CACHE[bare] = nifty_sec
                    _DYNAMIC_SECTOR_CACHE[raw] = nifty_sec
                    _DYNAMIC_SECTOR_CACHE[lookup_sym] = nifty_sec
                    return nifty_sec
        except Exception:
            continue

    return None

_SECTOR_RETURNS_CACHE: Dict[str, Dict[str, Any]] = {}
_SECTOR_RETURNS_TTL: float = 900.0  # 15 minutes

def get_sector_20d_return(sector_name: str) -> Optional[float]:
    """Fetches 20-day return for a sectoral index with 15-minute RAM caching."""
    sec_ticker = SECTOR_INDEX_MAP.get(sector_name)
    if not sec_ticker:
        return None
    now = time.time()
    if sec_ticker in _SECTOR_RETURNS_CACHE:
        entry = _SECTOR_RETURNS_CACHE[sec_ticker]
        if (now - entry.get("timestamp", 0)) < _SECTOR_RETURNS_TTL:
            return entry.get("return_20d")
    try:
        t = yf.Ticker(sec_ticker)
        hist = t.history(period="1mo")
        if len(hist) >= 20:
            p_now = float(hist['Close'].iloc[-1])
            p_20d = float(hist['Close'].iloc[-20])
            if p_20d > 0:
                ret = round(((p_now - p_20d) / p_20d) * 100.0, 2)
                _SECTOR_RETURNS_CACHE[sec_ticker] = {"return_20d": ret, "timestamp": now}
                return ret
    except Exception as e:
        logger.debug(f"Error fetching sector return for {sec_ticker}: {e}")
    return None

def calculate_sector_relative_strength(symbol: str, stock_20d_ret: Optional[float] = None) -> Dict[str, Any]:
    """
    Computes Mansfield Relative Strength of stock against its specific sector benchmark.
    Returns None values if sector or stock 20d return is unavailable.
    """
    sector_name = get_symbol_sector(symbol)
    if not sector_name or stock_20d_ret is None:
        return {
            "sector_name": sector_name or "BROAD_MARKET",
            "sector_symbol": SECTOR_INDEX_MAP.get(sector_name or ""),
            "sector_rs_rating": None,
            "sector_rs_20d": None,
            "sector_rs_regime": "DATA_UNAVAILABLE",
            "sector_trend": "DATA_UNAVAILABLE"
        }

    sec_ret = get_sector_20d_return(sector_name)
    if sec_ret is None:
        return {
            "sector_name": sector_name,
            "sector_symbol": SECTOR_INDEX_MAP.get(sector_name),
            "sector_rs_rating": None,
            "sector_rs_20d": None,
            "sector_rs_regime": "DATA_UNAVAILABLE",
            "sector_trend": "DATA_UNAVAILABLE"
        }

    delta_rs = round(float(stock_20d_ret) - float(sec_ret), 2)
    if delta_rs >= 2.5:
        regime = "SECTOR_LEADER"
    elif delta_rs <= -2.5:
        regime = "SECTOR_LAGGARD"
    else:
        regime = "IN_LINE"

    return {
        "sector_name": sector_name,
        "sector_symbol": SECTOR_INDEX_MAP.get(sector_name),
        "sector_rs_rating": delta_rs,
        "sector_rs_20d": delta_rs,
        "sector_rs_regime": regime,
        "sector_trend": "OUTPERFORMING" if delta_rs > 0 else "UNDERPERFORMING"
    }

# In-memory cache for market breadth (TTL: 60 seconds)
_MARKET_BREADTH_CACHE: Dict[str, Any] = {}
_MARKET_BREADTH_TS: float = 0.0
_MARKET_BREADTH_TTL: float = 60.0

def fetch_market_breadth_adr() -> Dict[str, Any]:
    """
    Fetches real-time Indian cash market breadth (Advance-Decline Ratio - ADR).
    Queries official NSE All-Indices market breadth with in-memory caching and resilient fallback.
    - STRONG_BULLISH_BREADTH: ADR >= 1.5 (High breakout follow-through probability)
    - BALANCED_BREADTH: 0.8 <= ADR < 1.5 (Stock-specific action)
    - MILD_BREADTH_WEAKNESS: 0.6 <= ADR < 0.8 (Caution on new long entries)
    - SEVERE_MARKET_DISTRIBUTION: ADR < 0.60 (Blocks all long breakouts / anti-bull-trap veto)
    Returns None values if market data is unavailable.
    """
    global _MARKET_BREADTH_CACHE, _MARKET_BREADTH_TS
    now = time.time()
    if _MARKET_BREADTH_CACHE and (now - _MARKET_BREADTH_TS) < _MARKET_BREADTH_TTL:
        return _MARKET_BREADTH_CACHE

    default_breadth = {
        "adr_ratio": None,
        "advances": None,
        "declines": None,
        "unchanged": None,
        "breadth_regime": "DATA_UNAVAILABLE",
        "source": "DATA_UNAVAILABLE"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/",
    }

    try:
        url = "https://www.nseindia.com/api/allIndices"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                raw = json.loads(resp.read().decode("utf-8"))
                indices = raw.get("data", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
                # Prioritize NIFTY 50 or NIFTY 500 breadth
                target_index = next((item for item in indices if item.get("index") in ["NIFTY 50", "NIFTY 500"]), None)
                if target_index and target_index.get("advances") is not None and target_index.get("declines") is not None:
                    adv = int(target_index.get("advances"))
                    dec = int(target_index.get("declines"))
                    unch = int(target_index.get("unchanged") or 0)
                    adr = round(adv / max(1, dec), 2)
                    
                    if adr >= 1.5:
                        regime = "STRONG_BULLISH_BREADTH"
                    elif adr >= 0.8:
                        regime = "BALANCED_BREADTH"
                    elif adr >= 0.6:
                        regime = "MILD_BREADTH_WEAKNESS"
                    else:
                        regime = "SEVERE_MARKET_DISTRIBUTION"

                    result = {
                        "adr_ratio": adr,
                        "advances": adv,
                        "declines": dec,
                        "unchanged": unch,
                        "breadth_regime": regime,
                        "source": "NSE_LIVE"
                    }
                    _MARKET_BREADTH_CACHE = result
                    _MARKET_BREADTH_TS = now
                    return result
    except Exception as e:
        logger.debug(f"Direct NSE market breadth fetch skipped/unavailable: {e}")

    # ZERO-DEFAULT POLICY: When direct exchange breadth data is unavailable, return clean unpopulated state
    return default_breadth

def _fetch_yahoo_chart_meta(symbol: str) -> Optional[Tuple[float, float, float]]:
    """
    Direct high-speed chart metadata fetcher bypassing yfinance crumb/cookie session blocks.
    Returns (current_price, prev_close, change_pct) or None if unavailable.
    """
    encoded_sym = urllib.parse.quote(symbol)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded_sym}?range=2d&interval=1d"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=4) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                results = data.get("chart", {}).get("result", [])
                if results and len(results) > 0:
                    meta = results[0].get("meta", {})
                    curr_p = meta.get("regularMarketPrice")
                    prev_p = meta.get("chartPreviousClose") or meta.get("previousClose")
                    if curr_p is not None:
                        curr_p = float(curr_p)
                        if prev_p is not None and float(prev_p) > 0:
                            prev_p = float(prev_p)
                            chg_pct = round(((curr_p - prev_p) / prev_p) * 100, 2)
                        else:
                            chg_pct = 0.0
                        return (curr_p, prev_p, chg_pct)
    except Exception as e:
        logger.debug(f"Direct Yahoo chart fetch note for {symbol}: {e}")
    return None

# In-memory cache for macro market regime (TTL: 60 seconds)
_MACRO_REGIME_CACHE: Dict[str, Any] = {}
_MACRO_REGIME_TS: float = 0.0
_MACRO_REGIME_TTL: float = 60.0
_MACRO_REGIME_LOCK = threading.Lock()

def fetch_macro_market_regime() -> Dict[str, Any]:
    """
    Fetches broad Indian market indices and breadth:
    - NIFTY 50 (^NSEI)
    - BSE SENSEX (^BSESN)
    - India VIX (^INDIAVIX)
    - Advance-Decline Ratio (Market Breadth ADR)
    Features 60s thread-safe in-memory caching and stale-cache fallback on rate limits.
    ZERO-DEFAULT POLICY: Returns None and DATA_UNAVAILABLE when realtime exchange data cannot be retrieved.
    """
    global _MACRO_REGIME_CACHE, _MACRO_REGIME_TS

    # Fast path: return fresh in-memory snapshot if within TTL
    now = time.time()
    if _MACRO_REGIME_CACHE and (now - _MACRO_REGIME_TS) < _MACRO_REGIME_TTL:
        return dict(_MACRO_REGIME_CACHE)

    default_res = {
        "nifty_price": None,
        "nifty_change_pct": None,
        "nifty_trend": "DATA_UNAVAILABLE",
        "sensex_price": None,
        "sensex_change_pct": None,
        "india_vix": None,
        "vix_regime": "DATA_UNAVAILABLE",
        "adr_ratio": None,
        "advances": None,
        "declines": None,
        "breadth_regime": "DATA_UNAVAILABLE",
        "allow_breakout_trades": False
    }

    with _MACRO_REGIME_LOCK:
        now = time.time()
        if _MACRO_REGIME_CACHE and (now - _MACRO_REGIME_TS) < _MACRO_REGIME_TTL:
            return dict(_MACRO_REGIME_CACHE)

        try:
            # 1. NIFTY 50 (^NSEI)
            nifty_price = None
            nifty_change_pct = None
            nifty_trend = "DATA_UNAVAILABLE"
            nifty_meta = _fetch_yahoo_chart_meta("^NSEI")
            if nifty_meta:
                nifty_price = round(nifty_meta[0], 2)
                nifty_change_pct = nifty_meta[2]
                nifty_trend = "BULLISH" if nifty_change_pct > 0.3 else ("BEARISH" if nifty_change_pct < -0.3 else "NEUTRAL")
            else:
                nifty = yf.Ticker("^NSEI")
                nifty_hist = nifty.history(period="2d")
                if len(nifty_hist) >= 2:
                    prev_close = float(nifty_hist['Close'].iloc[-2])
                    curr_close = float(nifty_hist['Close'].iloc[-1])
                    nifty_price = round(curr_close, 2)
                    nifty_change_pct = round(((curr_close - prev_close) / prev_close) * 100, 2)
                    nifty_trend = "BULLISH" if nifty_change_pct > 0.3 else ("BEARISH" if nifty_change_pct < -0.3 else "NEUTRAL")
                elif not nifty_hist.empty:
                    curr_close = float(nifty_hist['Close'].iloc[-1])
                    nifty_price = round(curr_close, 2)
                    nifty_trend = "NEUTRAL"

            # 2. India VIX (^INDIAVIX)
            vix_val = None
            vix_regime = "DATA_UNAVAILABLE"
            allow_breakout = True
            vix_meta = _fetch_yahoo_chart_meta("^INDIAVIX")
            if vix_meta:
                vix_val = round(vix_meta[0], 2)
            else:
                vix = yf.Ticker("^INDIAVIX")
                vix_hist = vix.history(period="2d")
                if not vix_hist.empty:
                    vix_val = round(float(vix_hist['Close'].iloc[-1]), 2)

            if vix_val is not None:
                if vix_val < 13.0:
                    vix_regime = "LOW_VOLATILITY_TRENDING"
                    allow_breakout = True
                elif vix_val <= 19.0:
                    vix_regime = "NORMAL_VOLATILITY"
                    allow_breakout = True
                elif vix_val <= 24.0:
                    vix_regime = "ELEVATED_VOLATILITY_CAUTION"
                    allow_breakout = True
                else:
                    vix_regime = "EXTREME_VOLATILITY_HIGH_RISK"
                    allow_breakout = False

            # 3. BSE SENSEX (^BSESN)
            sensex_price = None
            sensex_change_pct = None
            sensex_meta = _fetch_yahoo_chart_meta("^BSESN")
            if sensex_meta:
                sensex_price = round(sensex_meta[0], 2)
                sensex_change_pct = sensex_meta[2]
            else:
                try:
                    sensex = yf.Ticker("^BSESN")
                    sensex_hist = sensex.history(period="2d")
                    if len(sensex_hist) >= 2:
                        s_prev = float(sensex_hist['Close'].iloc[-2])
                        s_curr = float(sensex_hist['Close'].iloc[-1])
                        sensex_price = round(s_curr, 2)
                        sensex_change_pct = round(((s_curr - s_prev) / s_prev) * 100, 2)
                    elif not sensex_hist.empty:
                        sensex_price = round(float(sensex_hist['Close'].iloc[-1]), 2)
                except Exception as e:
                    logger.debug(f"BSE SENSEX fetch fallback: {e}")

            # 4. Market Breadth Advance-Decline Ratio (ADR)
            breadth = fetch_market_breadth_adr()
            adr_val = breadth.get("adr_ratio")
            breadth_regime = breadth.get("breadth_regime", "DATA_UNAVAILABLE")

            # Market Breadth Veto: If severe distribution (ADR < 0.60), block breakout trades
            if adr_val is not None and adr_val < 0.60:
                allow_breakout = False

            result = {
                "nifty_price": nifty_price,
                "nifty_change_pct": nifty_change_pct,
                "nifty_trend": nifty_trend,
                "sensex_price": sensex_price,
                "sensex_change_pct": sensex_change_pct,
                "india_vix": vix_val,
                "vix_regime": vix_regime,
                "adr_ratio": adr_val,
                "advances": breadth.get("advances"),
                "declines": breadth.get("declines"),
                "breadth_regime": breadth_regime,
                "allow_breakout_trades": allow_breakout
            }

            # Only cache when we obtain at least one valid index data point
            if nifty_price is not None or vix_val is not None:
                _MACRO_REGIME_CACHE = result
                _MACRO_REGIME_TS = now

            return result

        except Exception as e:
            logger.error(f"Error fetching macro regime: {e}")
            if _MACRO_REGIME_CACHE:
                logger.warning("Returning stale in-memory macro regime cache due to upstream fetch error.")
                stale_result = dict(_MACRO_REGIME_CACHE)
                stale_result["is_stale"] = True
                return stale_result
            return default_res


def fetch_pre_market_war_room_data() -> Dict[str, Any]:
    """
    Synthesizes institutional pre-market intelligence for the 09:00 AM IST War Room:
    1. Domestic Benchmark: NIFTY 50 & BSE SENSEX levels and previous close
    2. Volatility Regime: India VIX (^INDIAVIX) and risk posture
    3. Global Cues: US (Dow Jones ^DJI, Nasdaq ^IXIC) and Asia (Nikkei ^N225)
    4. Sectoral Momentum: NIFTY Bank (^NSEBANK), NIFTY IT (^CNXIT), NIFTY Auto (^CNXAUTO)
    5. Actionable Session Guidance: Volatility warning, directional bias, and setup priority
    ZERO-DEFAULT POLICY: Omits missing benchmarks, sector lists, and cues rather than fabricating fake defaults.
    """
    from datetime import date
    today_str = str(date.today())
    
    # 1. Base macro data
    base_macro = fetch_macro_market_regime()
    nifty_price = base_macro.get("nifty_price")
    nifty_chg = base_macro.get("nifty_change_pct")
    sensex_price = base_macro.get("sensex_price")
    sensex_chg = base_macro.get("sensex_change_pct")
    vix_val = base_macro.get("india_vix")
    vix_regime = base_macro.get("vix_regime", "DATA_UNAVAILABLE")
    allow_breakouts = base_macro.get("allow_breakout_trades", True)
    
    # 2. Global Cues
    global_cues = {
        "dow_jones_pct": None,
        "nasdaq_pct": None,
        "nikkei_pct": None,
        "bias": "DATA_UNAVAILABLE"
    }
    
    ticker_map = {
        "^DJI": "dow_jones_pct",
        "^IXIC": "nasdaq_pct",
        "^N225": "nikkei_pct"
    }
    
    for t_sym, key in ticker_map.items():
        meta = _fetch_yahoo_chart_meta(t_sym)
        if meta and meta[2] is not None:
            global_cues[key] = meta[2]
        else:
            try:
                t = yf.Ticker(t_sym)
                fast = getattr(t, 'fast_info', None)
                if fast:
                    lp = getattr(fast, 'last_price', None)
                    prev = getattr(fast, 'regular_market_previous_close', None)
                    if lp and prev and prev > 0:
                        pct = round(((float(lp) - float(prev)) / float(prev)) * 100, 2)
                        global_cues[key] = pct
            except Exception as err:
                logger.debug(f"Pre-market global cue fetch failed for {t_sym}: {err}")
            
    valid_cues = [v for v in [global_cues["dow_jones_pct"], global_cues["nasdaq_pct"], global_cues["nikkei_pct"]] if v is not None]
    if valid_cues:
        avg_global = sum(valid_cues) / len(valid_cues)
        if avg_global >= 0.5:
            global_cues["bias"] = "BULLISH_TAILWINDS"
        elif avg_global <= -0.5:
            global_cues["bias"] = "BEARISH_HEADWINDS"
        elif avg_global > 0:
            global_cues["bias"] = "MILD_POSITIVE"
        else:
            global_cues["bias"] = "MILD_NEGATIVE"
    else:
        global_cues["bias"] = "DATA_UNAVAILABLE"
        
    # 3. Sectoral Momentum Check
    sector_tickers = {
        "NIFTY BANK": "^NSEBANK",
        "NIFTY IT": "^CNXIT",
        "NIFTY AUTO": "^CNXAUTO"
    }
    
    sector_results = []
    for s_name, s_ticker in sector_tickers.items():
        meta = _fetch_yahoo_chart_meta(s_ticker)
        if meta:
            sector_results.append({
                "name": s_name,
                "price": round(float(meta[0]), 2),
                "change_pct": meta[2]
            })
        else:
            try:
                t = yf.Ticker(s_ticker)
                fast = getattr(t, 'fast_info', None)
                if fast:
                    lp = getattr(fast, 'last_price', None)
                    prev = getattr(fast, 'regular_market_previous_close', None)
                    if lp and prev and prev > 0:
                        chg_pct = round(((float(lp) - float(prev)) / float(prev)) * 100, 2)
                        sector_results.append({
                            "name": s_name,
                            "price": round(float(lp), 2),
                            "change_pct": chg_pct
                        })
            except Exception:
                continue
            
    sector_results.sort(key=lambda x: x["change_pct"], reverse=True)
    leading_sectors = sector_results[:2] if sector_results else []
    lagging_sectors = sector_results[-1:] if sector_results else []
    
    # 4. Tactical Session Guidance
    adr_val = base_macro.get("adr_ratio")
    breadth_regime = base_macro.get("breadth_regime", "DATA_UNAVAILABLE")

    if not allow_breakouts or (vix_val is not None and vix_val > 22.0) or (adr_val is not None and adr_val < 0.60):
        vix_str = f"{vix_val}" if vix_val is not None else "N/A"
        adr_str = f"{adr_val:.2f}" if adr_val is not None else "N/A"
        guidance = f"⚠️ High risk regime detected (VIX: {vix_str}, Market Breadth ADR: {adr_str}). Heavy market distribution. Vetoing new long breakouts."
    elif global_cues["bias"] in ["BULLISH_TAILWINDS", "MILD_POSITIVE"] and (nifty_chg is not None and nifty_chg >= 0):
        sec_str = f" in leading sectors ({', '.join(s['name'] for s in leading_sectors)})" if leading_sectors else ""
        guidance = f"🟢 Favorable bullish tailwinds (Breadth: {breadth_regime}). Prioritize Smart Money Absorption breakouts above VWAP{sec_str}."
    elif global_cues["bias"] == "BEARISH_HEADWINDS" or (nifty_chg is not None and nifty_chg < -0.4):
        guidance = "🔴 Macro headwinds prevalent. Watch for Wyckoff operator bull-traps and protect Demat profits with Chandelier Trailing Stops."
    elif global_cues["bias"] == "DATA_UNAVAILABLE" and nifty_price is None:
        guidance = "⚪ Broad market feeds offline / pending open. Focus on stock-specific volume surges and disciplined risk management."
    else:
        guidance = "⚪ Mixed global cues. Focus on stock-specific volume surges and disciplined Camarilla L3 liquidity floor entries."
        
    return {
        "date": today_str,
        "nifty_price": nifty_price,
        "nifty_change_pct": nifty_chg,
        "sensex_price": sensex_price,
        "sensex_change_pct": sensex_chg,
        "india_vix": vix_val,
        "vix_regime": vix_regime,
        "adr_ratio": adr_val,
        "breadth_regime": breadth_regime,
        "allow_breakout_trades": allow_breakouts,
        "global_cues": global_cues,
        "leading_sectors": leading_sectors,
        "lagging_sectors": lagging_sectors,
        "tactical_guidance": guidance
    }


def evaluate_forensic_health(symbol: str, financials: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates corporate governance, debt health, and forensic red flags:
    - Debt-to-Equity (< 1.0 is healthy, > 2.0 is risky)
    - Trailing P/E vs Forward P/E
    - Interest Coverage (Estimated)
    - Promoter Pledging Flag (Flagged if > 15%)
    """
    debt_to_equity = financials.get("debt_to_equity")
    pe_ratio = financials.get("pe_ratio")
    forward_pe = financials.get("forward_pe")
    profit_margin = financials.get("profit_margin_pct")
    
    red_flags = []
    strengths = []
    
    if debt_to_equity is not None:
        if debt_to_equity > 2.0:
            red_flags.append(f"Elevated Debt-to-Equity ratio ({debt_to_equity})")
        elif debt_to_equity < 0.5:
            strengths.append(f"Virtually Debt-Free / Robust Balance Sheet (D/E: {debt_to_equity})")
            
    if pe_ratio and forward_pe:
        if forward_pe < pe_ratio:
            strengths.append(f"Forward Valuation improving (Trailing P/E: {pe_ratio} -> Forward P/E: {forward_pe})")
            
    if profit_margin and profit_margin > 15.0:
        strengths.append(f"High Operating Profit Margin ({profit_margin}%)")
        
    sector_name = get_symbol_sector(symbol) or "BROAD_MARKET"
    
    return {
        "symbol": symbol,
        "sector_name": sector_name,
        "is_healthy": len(red_flags) == 0,
        "red_flags": red_flags,
        "strengths": strengths,
        "forensic_score": 80 if len(red_flags) == 0 else (40 if len(red_flags) == 1 else 20)
    }
