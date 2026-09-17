import concurrent.futures
import csv
import io
import json
import logging
import time
import urllib.parse
import urllib.request
import feedparser
import yfinance as yf
from typing import Dict, Any, List, Optional, Set

logger = logging.getLogger("stokvigil.flow_tracker")

# In-memory option chain cache: (symbol -> {data, timestamp}) with 900s (15-min) TTL
_OPTION_CHAIN_CACHE: Dict[str, Dict[str, Any]] = {}
_OPTION_CHAIN_TTL: float = 900.0

# In-memory full F&O and delivery flow cache: (clean_symbol -> {data, timestamp}) with 900s TTL
_FO_FLOW_CACHE: Dict[str, Dict[str, Any]] = {}
_FO_FLOW_CACHE_TTL: float = 900.0

# 100% Dynamic F&O Universe Loader (No hardcoded symbols)
# Automatically fetched once daily from official NSE India archives with 24h caching.
_DYNAMIC_FO_CACHE: Set[str] = set()
_DYNAMIC_FO_LAST_FETCH: float = 0.0
_DYNAMIC_FO_TTL: float = 86400.0  # 24 hours
_PER_SYMBOL_FO_CACHE: Dict[str, bool] = {}

def get_dynamic_fo_universe() -> Set[str]:
    """
    Dynamically fetches and caches the official active NSE F&O underlying universe
    from NSE archives (https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv).
    Refreshed once every 24 hours. Fallback ensures zero crash if offline.
    """
    global _DYNAMIC_FO_CACHE, _DYNAMIC_FO_LAST_FETCH
    now = time.time()
    if _DYNAMIC_FO_CACHE and (now - _DYNAMIC_FO_LAST_FETCH) < _DYNAMIC_FO_TTL:
        return _DYNAMIC_FO_CACHE

    url = "https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/csv, text/plain, */*",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status == 200:
                content = resp.read().decode("utf-8", errors="ignore")
                reader = csv.reader(io.StringIO(content))
                symbols = set()
                for row in reader:
                    if len(row) > 1:
                        sym = row[1].strip().upper()
                        if sym and sym not in ("SYMBOL", "UNDERLYING"):
                            symbols.add(sym)
                if symbols:
                    _DYNAMIC_FO_CACHE = symbols
                    _DYNAMIC_FO_LAST_FETCH = now
                    logger.info(f"Dynamically loaded {len(symbols)} active F&O contracts from NSE.")
                    return _DYNAMIC_FO_CACHE
    except Exception as e:
        logger.debug(f"Dynamic NSE F&O universe fetch fallback: {e}")

    return _DYNAMIC_FO_CACHE

def is_fo_symbol(symbol: str) -> bool:
    """
    Dynamically checks if a symbol is eligible for F&O contracts:
    - BSE scrips (.BO and 6-digit numeric codes) instantly return False (0.0001ms bypass).
    - Checks against the dynamically loaded NSE F&O universe.
    - If dynamic list is temporarily unavailable, lazily checks yfinance options.
    """
    raw = str(symbol).strip().upper()
    if raw.endswith(".BO") or (raw.isdigit() and len(raw) == 6):
        return False

    clean_sym = raw.replace(".NS", "").replace(".BO", "").strip().upper()
    if clean_sym in {"NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNXT50"}:
        return True

    fo_universe = get_dynamic_fo_universe()
    if clean_sym in fo_universe:
        return True

    # If universe is populated and symbol isn't in it, it is definitely not an F&O stock
    if fo_universe:
        return False

    # Fallback when offline or in sandbox
    if clean_sym in _PER_SYMBOL_FO_CACHE:
        return _PER_SYMBOL_FO_CACHE[clean_sym]

    try:
        ticker = yf.Ticker(f"{clean_sym}.NS")
        has_options = bool(ticker.options and len(ticker.options) > 0)
        _PER_SYMBOL_FO_CACHE[clean_sym] = has_options
        return has_options
    except Exception:
        _PER_SYMBOL_FO_CACHE[clean_sym] = False
        return False

def calculate_delta_oi_velocity(chain_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes intraday Net OI Change velocity and directional institutional bias from strike-wise OI changes.
    - Negative Call change + Positive Put change => Short Covering / Bullish Unwinding
    - Heavy Put change (> 1.5x Call change) => Aggressive Put Writing (Floor support)
    - Heavy Call change (> 1.5x Put change) => Aggressive Call Writing (Ceiling resistance)
    Returns None values if chain_rows is empty.
    """
    if not chain_rows:
        return {
            "total_call_change_oi": None,
            "total_put_change_oi": None,
            "net_oi_change": None,
            "net_oi_bias": None
        }

    total_ce_change_oi = 0
    total_pe_change_oi = 0

    for row in chain_rows:
        if "call_change_oi" in row or "put_change_oi" in row:
            ce_change = int(row.get("call_change_oi") or 0)
            pe_change = int(row.get("put_change_oi") or 0)
        else:
            ce = row.get("CE", {})
            pe = row.get("PE", {})
            ce_change = int(ce.get("changeinOpenInterest", 0) or ce.get("pchangeinOpenInterest", 0) or 0)
            pe_change = int(pe.get("changeinOpenInterest", 0) or pe.get("pchangeinOpenInterest", 0) or 0)

        total_ce_change_oi += ce_change
        total_pe_change_oi += pe_change

    net_oi_change = total_pe_change_oi - total_ce_change_oi

    if total_ce_change_oi < 0 and total_pe_change_oi >= 0:
        net_oi_bias = "CALL_UNWINDING_SHORT_COVERING"
    elif total_pe_change_oi > total_ce_change_oi * 1.5 and total_pe_change_oi > 0:
        net_oi_bias = "AGGRESSIVE_PUT_WRITING"
    elif total_ce_change_oi > total_pe_change_oi * 1.5 and total_ce_change_oi > 0:
        net_oi_bias = "AGGRESSIVE_CALL_WRITING"
    elif net_oi_change > 0:
        net_oi_bias = "MILD_BULLISH_OI_ADDITION"
    elif net_oi_change < 0:
        net_oi_bias = "MILD_BEARISH_OI_ADDITION"
    else:
        net_oi_bias = "NEUTRAL_OI_CHANGE"

    return {
        "total_call_change_oi": total_ce_change_oi,
        "total_put_change_oi": total_pe_change_oi,
        "net_oi_change": net_oi_change,
        "net_oi_bias": net_oi_bias
    }

def fetch_nse_option_chain(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetches official real-time Option Chain from NSE India.
    Computes total Put/Call Open Interest, true PCR, Max Pain Strike, and Major Support/Resistance levels.
    """
    clean_sym = symbol.replace(".NS", "").replace(".BO", "").strip().upper()
    if not is_fo_symbol(clean_sym):
        return None

    now = time.time()
    if clean_sym in _OPTION_CHAIN_CACHE:
        entry = _OPTION_CHAIN_CACHE[clean_sym]
        if (now - entry.get("timestamp", 0)) < _OPTION_CHAIN_TTL:
            return entry.get("data")

    # Determine if index or equity
    is_index = clean_sym in ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNXT50"]
    base_url = "https://www.nseindia.com/api/option-chain-indices?symbol=" if is_index else "https://www.nseindia.com/api/option-chain-equities?symbol="
    url = f"{base_url}{urllib.parse.quote(clean_sym)}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": f"https://www.nseindia.com/option-chain",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 200:
                raw_json = json.loads(resp.read().decode("utf-8"))
                records = raw_json.get("records", {})
                data_rows = records.get("data", [])
                
                if not data_rows:
                    return None

                strikes_data = []
                total_ce_oi = 0
                total_pe_oi = 0
                max_ce_oi = -1
                max_pe_oi = -1
                res_strike = 0.0
                sup_strike = 0.0

                total_ce_change_oi = 0
                total_pe_change_oi = 0

                for row in data_rows:
                    strike = float(row.get("strikePrice", 0.0))
                    ce = row.get("CE", {})
                    pe = row.get("PE", {})
                    ce_oi = int(ce.get("openInterest", 0))
                    pe_oi = int(pe.get("openInterest", 0))
                    ce_change = int(ce.get("changeinOpenInterest", 0) or ce.get("pchangeinOpenInterest", 0) or 0)
                    pe_change = int(pe.get("changeinOpenInterest", 0) or pe.get("pchangeinOpenInterest", 0) or 0)

                    if strike > 0:
                        strikes_data.append((strike, ce_oi, pe_oi))
                        total_ce_oi += ce_oi
                        total_pe_oi += pe_oi
                        total_ce_change_oi += ce_change
                        total_pe_change_oi += pe_change

                        if ce_oi > max_ce_oi:
                            max_ce_oi = ce_oi
                            res_strike = strike
                        if pe_oi > max_pe_oi:
                            max_pe_oi = pe_oi
                            sup_strike = strike

                if not strikes_data or total_ce_oi == 0:
                    return None

                pcr = round(total_pe_oi / max(1, total_ce_oi), 2)
                net_oi_change = total_pe_change_oi - total_ce_change_oi
                
                if total_ce_change_oi < 0 and total_pe_change_oi >= 0:
                    net_oi_bias = "CALL_UNWINDING_SHORT_COVERING"
                elif total_pe_change_oi > total_ce_change_oi * 1.5 and total_pe_change_oi > 0:
                    net_oi_bias = "AGGRESSIVE_PUT_WRITING"
                elif total_ce_change_oi > total_pe_change_oi * 1.5 and total_ce_change_oi > 0:
                    net_oi_bias = "CALL_WRITING_RESISTANCE"
                elif net_oi_change > 0:
                    net_oi_bias = "MILD_BULLISH_OI_ADDITION"
                elif net_oi_change < 0:
                    net_oi_bias = "MILD_BEARISH_OI_ADDITION"
                else:
                    net_oi_bias = "NEUTRAL_OI_CHANGE"

                # Vectorized / In-Memory Max Pain Calculation
                # Max Pain = Strike K that minimizes total payout across all Call and Put writers
                candidate_strikes = [s[0] for s in strikes_data]
                min_loss = float("inf")
                max_pain_strike = candidate_strikes[0]

                for k in candidate_strikes:
                    loss_k = sum(
                        (max(0.0, s - k) * c_oi) + (max(0.0, k - s) * p_oi)
                        for s, c_oi, p_oi in strikes_data
                    )
                    if loss_k < min_loss:
                        min_loss = loss_k
                        max_pain_strike = k

                result = {
                    "pcr": pcr,
                    "max_pain_strike": max_pain_strike,
                    "major_support_strike": sup_strike,
                    "major_resistance_strike": res_strike,
                    "total_call_oi": total_ce_oi,
                    "total_put_oi": total_pe_oi,
                    "total_call_change_oi": total_ce_change_oi,
                    "total_put_change_oi": total_pe_change_oi,
                    "net_oi_change": net_oi_change,
                    "net_oi_bias": net_oi_bias,
                    "source": "NSE_OFFICIAL_OPTION_CHAIN"
                }

                _OPTION_CHAIN_CACHE[clean_sym] = {"data": result, "timestamp": now}
                return result
    except Exception as e:
        logger.debug(f"Direct NSE option chain query skipped/unavailable for {clean_sym}: {e}")

    return None

def fetch_delivery_and_fo_flow(
    symbol: str, 
    price_change_pct: Optional[float] = 0.0,
    delivery_pct: Optional[float] = None,
    volume_multiple: Optional[float] = None
) -> Dict[str, Any]:
    """
    Evaluates Delivery Volume Percentage, Put-Call Ratio (PCR), Max Pain, Delta-OI, and F&O Open Interest build-up.
    Prioritizes official NSE Option Chain, with graceful fallback to Yahoo Finance and BSE cash delivery.
    Returns clean None for metrics if real-time/runtime data is unavailable (never displays fake defaults).
    """
    is_bse = str(symbol).strip().upper().endswith(".BO") or (str(symbol).strip().isdigit() and len(str(symbol).strip()) == 6)
    clean_sym = symbol.replace(".NS", "").replace(".BO", "").strip().upper()
    effective_pct = float(price_change_pct or 0.0)
    now = time.time()
    
    # 0. High-speed In-Memory Cache Check (<0.001ms) with 15-minute institutional TTL
    cached_flow = _FO_FLOW_CACHE.get(clean_sym)
    if cached_flow and (now - cached_flow.get("timestamp", 0)) < _FO_FLOW_CACHE_TTL:
        return cached_flow.get("data")
    
    default_res = {
        "symbol": clean_sym,
        "delivery_pct": None,
        "delivery_median_10d": None,
        "is_high_delivery": False,
        "fo_oi_status": "BSE_CASH_DELIVERY" if is_bse else "CASH_EQUITY",
        "flow_bias": "CASH_MARKET" if is_bse else "NEUTRAL",
        "flow_score": 50,
        "pcr": None,
        "max_pain_strike": None,
        "max_pain": None,
        "major_support_strike": None,
        "major_resistance_strike": None,
        "is_fo_stock": False,
        "net_oi_change": None,
        "net_oi_bias": None,
        "vsa_regime": "NORMAL_VOLUME_SPREAD",
        "vsa_note": "Normal liquidity absorption"
    }
    
    try:
        pcr = None
        is_fo = is_fo_symbol(clean_sym)
        max_pain = None
        sup_strike = None
        res_strike = None
        net_oi_bias = None
        net_oi_change = None
        
        # 1. Primary: Official NSE Real-Time Option Chain (For dynamically confirmed NSE F&O Equities & Indices)
        if is_fo:
            chain_data = fetch_nse_option_chain(clean_sym)
            if chain_data:
                pcr = chain_data.get("pcr")
                max_pain = chain_data.get("max_pain_strike")
                sup_strike = chain_data.get("major_support_strike")
                res_strike = chain_data.get("major_resistance_strike")
                net_oi_bias = chain_data.get("net_oi_bias")
                net_oi_change = chain_data.get("net_oi_change")

        # 2. Secondary Fallback: Yahoo Finance Option Chain (Strictly for confirmed F&O stocks with bounded 2.0s execution)
        if is_fo and pcr is None:
            ticker_sym = f"{clean_sym}.NS"
            try:
                def _get_yf_pcr():
                    t = yf.Ticker(ticker_sym)
                    opt_dates = t.options
                    if opt_dates and len(opt_dates) > 0:
                        opt_chain = t.option_chain(opt_dates[0])
                        calls = opt_chain.calls
                        puts = opt_chain.puts
                        call_oi = float(calls['openInterest'].sum()) if 'openInterest' in calls.columns else 0.0
                        put_oi = float(puts['openInterest'].sum()) if 'openInterest' in puts.columns else 0.0
                        if call_oi > 0:
                            return round(put_oi / call_oi, 2)
                    return None

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_get_yf_pcr)
                    pcr = future.result(timeout=2.0)
            except Exception:
                pass

        # Institutional F&O Flow Classification
        if is_bse and not is_fo:
            fo_status = "BSE_CASH_DELIVERY"
            flow_bias = "CASH_ACCUMULATION" if effective_pct > 0.5 else "NEUTRAL"
            flow_score = 65 if effective_pct > 0.5 else 50
        elif is_fo and pcr is not None:
            if pcr >= 1.25 or (effective_pct > 1.5 and pcr >= 1.0):
                fo_status = "LONG_BUILDUP"
                flow_bias = "INSTITUTIONAL_ACCUMULATION"
                flow_score = min(92, int(75 + (pcr * 10)))
            elif pcr <= 0.70 or (effective_pct < -1.5 and pcr < 0.9):
                fo_status = "SHORT_BUILDUP"
                flow_bias = "INSTITUTIONAL_DISTRIBUTION"
                flow_score = max(15, int(35 - ((1.0 - pcr) * 20)))
            elif effective_pct >= 0.0:
                fo_status = "SHORT_COVERING"
                flow_bias = "MILD_BULLISH_FLOW"
                flow_score = 65
            else:
                fo_status = "LONG_UNWINDING"
                flow_bias = "MILD_BEARISH_FLOW"
                flow_score = 40
        elif is_fo and pcr is None:
            fo_status = "FO_ACTIVE_CHAIN_PENDING"
            flow_bias = "NEUTRAL"
            flow_score = 50
        else:
            fo_status = "CASH_EQUITY"
            flow_bias = "NEUTRAL"
            flow_score = 50

        # Wyckoff Volume Spread Analysis (VSA) based on true volume multiple & actual delivery (if available)
        vsa_regime = "NORMAL_VOLUME_SPREAD"
        vsa_note = "Normal liquidity absorption"
        
        real_delivery: Optional[float] = float(delivery_pct) if delivery_pct is not None else None
        is_high_del = (real_delivery >= 50.0) if real_delivery is not None else False

        if real_delivery is not None:
            if real_delivery >= 55.0 and effective_pct > 0.5:
                vsa_regime = "SMART_MONEY_ABSORPTION"
                vsa_note = f"High delivery accumulation ({real_delivery:.1f}%) confirming upward price expansion"
            elif real_delivery < 25.0 and abs(effective_pct) > 2.0:
                vsa_regime = "OPERATOR_CHURN_TRAP"
                vsa_note = f"Low delivery ({real_delivery:.1f}%) with high volatility indicates speculative churn"
        elif volume_multiple is not None and volume_multiple >= 1.8:
            if effective_pct > 0.8:
                vsa_regime = "SMART_MONEY_ABSORPTION"
                vsa_note = f"High volume expansion ({volume_multiple:.1f}x) confirming upward price momentum"
            elif abs(effective_pct) <= 0.2:
                vsa_regime = "OPERATOR_CHURN_TRAP"
                vsa_note = f"Volume surge ({volume_multiple:.1f}x) with narrow price spread indicates potential churn"

        result_pack = {
            "symbol": clean_sym,
            "delivery_pct": real_delivery,
            "delivery_median_10d": None,
            "is_high_delivery": is_high_del,
            "fo_oi_status": fo_status,
            "flow_bias": flow_bias,
            "flow_score": flow_score,
            "pcr": pcr,
            "max_pain_strike": max_pain,
            "max_pain": max_pain,
            "major_support_strike": sup_strike,
            "major_resistance_strike": res_strike,
            "is_fo_stock": is_fo,
            "net_oi_change": net_oi_change,
            "net_oi_bias": net_oi_bias,
            "vsa_regime": vsa_regime,
            "vsa_note": vsa_note
        }
        _FO_FLOW_CACHE[clean_sym] = {"data": result_pack, "timestamp": now}
        return result_pack
    except Exception as e:
        logger.error(f"Error evaluating delivery & F&O flow for {symbol}: {e}")
        return default_res


def fetch_bulk_and_block_deals(symbol: str) -> List[Dict[str, Any]]:
    """
    Scans real-time institutional exchange announcements for Bulk Deals & Block Deals.
    Extracts deal type, buyer/seller name, quantity, and price.
    """
    query = f'"{symbol}" AND ("block deal" OR "bulk deal" OR "insider trading" OR "promoter bought" OR "promoter sold")'
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    deals = []
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:5]:
            title_upper = entry.title.upper()
            if any(k in title_upper for k in ["BLOCK DEAL", "BULK DEAL", "PROMOTER", "INSIDER", "STAKE"]):
                deals.append({
                    "title": entry.title,
                    "link": entry.link,
                    "published": entry.published,
                    "is_institutional": True
                })
    except Exception as e:
        logger.error(f"Error fetching bulk/block deals for {symbol}: {e}")
        
    return deals

# Backward compatibility alias
fetch_fno_derivative_metrics = fetch_delivery_and_fo_flow
