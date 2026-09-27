import concurrent.futures
import json
import logging
import time
import urllib.parse
import urllib.request
from typing import List, Dict, Any, Optional

logger = logging.getLogger("stokvigil.engine.portfolio_sync")

# Universal Dynamic ISIN RAM Cache (<0.001ms)
_ISIN_CACHE: Dict[str, str] = {}

# User Demat Portfolio Cache: user_id -> {holdings, timestamp} (TTL: 14400 seconds / 4 hours)
_DEMAT_PORTFOLIO_CACHE: Dict[str, Dict[str, Any]] = {}
_DEMAT_PORTFOLIO_CACHE_TTL: float = 14400.0  # 4 hours


def resolve_isin_to_nse_symbol(isin: str, fallback_code: str = "") -> str:
    """
    Dynamically resolves any Indian stock ISIN (e.g. INE750C01026) or 6-digit BSE scrip code (e.g. 500325)
    to its official exchange ticker using real-time exchange security search. 100% dynamic for all 2,000+ stocks.
    """
    isin_clean = str(isin).strip().upper()
    fallback = str(fallback_code).strip().upper()

    if isin_clean.endswith(".BO") or isin_clean.endswith(".NS"):
        return isin_clean

    if isin_clean.isdigit() and len(isin_clean) == 6:
        return f"{isin_clean}.BO"
    if fallback.isdigit() and len(fallback) == 6:
        return f"{fallback}.BO"
    if fallback.endswith(".BO") or fallback.endswith(".NS"):
        return fallback
    
    if not isin_clean or not isin_clean.startswith("INE"):
        return fallback or isin_clean

    # 1. Check in-memory RAM cache (<0.001ms)
    if isin_clean in _ISIN_CACHE:
        return _ISIN_CACHE[isin_clean]

    # 2. Dynamic Exchange Search via Yahoo Finance Search API
    try:
        search_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        }
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(isin_clean)}&quotesCount=5"
        req = urllib.request.Request(url, headers=search_headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            quotes = data.get("quotes", [])
            for quote in quotes:
                sym = quote.get("symbol", "")
                if sym.endswith(".NS"):
                    clean_sym = sym.replace(".NS", "").strip().upper()
                    if clean_sym:
                        _ISIN_CACHE[isin_clean] = clean_sym
                        return clean_sym

            for quote in quotes:
                sym = quote.get("symbol", "")
                if sym.endswith(".BO"):
                    clean_sym = sym.replace(".BO", "").strip().upper()
                    if clean_sym and not clean_sym.startswith("0P"):
                        bse_sym = f"{clean_sym}.BO"
                        _ISIN_CACHE[isin_clean] = bse_sym
                        return bse_sym
                elif quote.get("quoteType") == "EQUITY":
                    clean_sym = sym.replace(".BO", "").replace(".NS", "").strip().upper()
                    if clean_sym and not clean_sym.startswith("0P"):
                        _ISIN_CACHE[isin_clean] = clean_sym
                        return clean_sym
    except Exception as e:
        logger.warning(f"Dynamic ISIN resolution failed for {isin_clean}: {e}")

    return fallback


def fetch_user_portfolio(app_key: str, secret_key: str, session_token: str) -> List[Dict[str, Any]]:
    """
    Fetches real-time portfolio holdings directly from user's CDSL/NSDL Demat account using breeze-connect SDK.
    Dynamically resolves ISINs to official NSE symbols in parallel for 100+ stock scalability.
    """
    if not app_key or not secret_key or not session_token:
        logger.warning("Incomplete Breeze credentials provided.")
        return []
        
    try:
        from breeze_connect import BreezeConnect

        clean_app = str(app_key or "").strip().strip('"').strip("'")
        clean_sec = str(secret_key or "").strip().strip('"').strip("'")
        clean_tok = str(session_token or "").strip().strip('"').strip("'")

        if "apisession=" in clean_tok:
            clean_tok = clean_tok.split("apisession=")[1].split("&")[0]

        clean_tok = urllib.parse.unquote(clean_tok).strip().strip('"').strip("'")

        app_preview = f"{clean_app[:3]}...{clean_app[-3:]}" if len(clean_app) >= 6 else "***"
        sec_preview = f"{clean_sec[:3]}...{clean_sec[-3:]}" if len(clean_sec) >= 6 else "***"
        tok_preview = f"{clean_tok[:3]}...{clean_tok[-3:]}" if len(clean_tok) >= 6 else "***"
        logger.info(f"Breeze Auth Check - AppKey: {app_preview} (len: {len(clean_app)}), SecretKey: {sec_preview} (len: {len(clean_sec)}), SessionToken: {tok_preview} (len: {len(clean_tok)})")

        breeze = BreezeConnect(api_key=clean_app)
        breeze.generate_session(api_secret=clean_sec, session_token=clean_tok)
        
        session_active = bool(getattr(breeze, 'session_key', None))
        logger.info(f"Breeze session_key established: {session_active}")
        
        demat_res = breeze.get_demat_holdings()
        status_code = demat_res.get('status') or demat_res.get('Status') if isinstance(demat_res, dict) else "Unknown"
        logger.info(f"Breeze get_demat_holdings status: {status_code}")

        raw_holdings = []
        if isinstance(demat_res, dict):
            if status_code in [200, "200"]:
                raw_holdings = demat_res.get('Success') or demat_res.get('success') or []
            else:
                logger.warning(f"Breeze get_demat_holdings returned error: {demat_res.get('Error') or demat_res}")
                return []

        def _fetch_tradebook_for_exchange(exch: str) -> Dict[str, float]:
            res_dict = {}
            try:
                p_res = breeze.get_portfolio_holdings(
                    exchange_code=exch,
                    from_date="",
                    to_date="",
                    stock_code="",
                    portfolio_type=""
                )
                if isinstance(p_res, dict):
                    status = p_res.get('status') or p_res.get('Status')
                    if status in [200, "200"]:
                        p_list = p_res.get('Success') or p_res.get('success') or []
                        if isinstance(p_list, list):
                            for item in p_list:
                                if isinstance(item, dict):
                                    code = str(item.get('stock_code') or item.get('symbol') or '').upper().strip()
                                    try:
                                        avg_p = float(item.get('average_price') or item.get('cost_price') or item.get('avg_cost') or item.get('purchase_price') or 0)
                                    except (ValueError, TypeError):
                                        avg_p = 0.0
                                    if code and avg_p > 0:
                                        res_dict[code] = avg_p
            except Exception as tradebook_err:
                logger.warning(f"Note on fetching ICICI {exch} tradebook avg prices: {tradebook_err}")
            return res_dict

        tradebook_avg_prices: Dict[str, float] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as tb_pool:
            fut_nse = tb_pool.submit(_fetch_tradebook_for_exchange, "NSE")
            fut_bse = tb_pool.submit(_fetch_tradebook_for_exchange, "BSE")
            tradebook_avg_prices.update(fut_nse.result())
            tradebook_avg_prices.update(fut_bse.result())

        def _parse_holding(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            if not isinstance(item, dict):
                return None
            raw_code = item.get('stock_code') or item.get('symbol') or item.get('stock_name') or ''
            isin_code = item.get('stock_ISIN') or item.get('isin') or ''
            clean_symbol = resolve_isin_to_nse_symbol(isin_code, fallback_code=raw_code)
            
            try:
                qty = float(item.get('quantity') or item.get('demat_total_bulk_quantity') or item.get('demat_avail_quantity') or 0)
            except (ValueError, TypeError):
                qty = 0.0

            raw_code_upper = str(raw_code).upper().strip()
            tb_price = tradebook_avg_prices.get(raw_code_upper, 0.0) or tradebook_avg_prices.get(clean_symbol, 0.0)
            
            try:
                avg_p = float(item.get('average_price') or item.get('avg_price') or item.get('cost_price') or item.get('purchase_price') or tb_price)
            except (ValueError, TypeError):
                avg_p = tb_price
                
            try:
                cmp = float(item.get('current_market_price') or item.get('last_price') or 0.0)
            except (ValueError, TypeError):
                cmp = 0.0

            stock_name = str(item.get('stock_name') or item.get('company_name') or item.get('stock_description') or '').strip()
            bare_symbol = clean_symbol.replace(".BO", "").replace(".NS", "").strip().upper()
            is_bse = clean_symbol.endswith(".BO") or str(item.get('exchange_code', '')).upper() == "BSE" or (bare_symbol.isdigit() and len(bare_symbol) == 6)

            if clean_symbol and qty > 0:
                return {
                    "symbol": clean_symbol,
                    "clean_symbol": bare_symbol,
                    "name": stock_name or bare_symbol,
                    "stock_name": stock_name or bare_symbol,
                    "exchange": "BSE" if is_bse else "NSE",
                    "quantity": qty,
                    "average_price": avg_p,
                    "current_market_price": cmp,
                }
            return None

        result = []
        seen_symbols = set()
        max_workers = min(10, max(1, len(raw_holdings)))
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            parsed_items = list(pool.map(_parse_holding, raw_holdings))

        for parsed in parsed_items:
            if parsed and parsed["symbol"] not in seen_symbols:
                seen_symbols.add(parsed["symbol"])
                result.append(parsed)

        logger.info(f"Successfully retrieved {len(result)} ICICI Demat holdings: {[r['symbol'] for r in result]}")
        return result
    except Exception as e:
        logger.error(f"Error fetching ICICI Breeze portfolio: {e}")
        return []


def invalidate_demat_portfolio_cache(user_id: str) -> None:
    """Invalidates cached Demat holdings for a user (e.g. after order placement)."""
    _DEMAT_PORTFOLIO_CACHE.pop(user_id, None)


def update_demat_portfolio_cache(user_id: str, holdings: List[Dict[str, Any]]) -> None:
    """Updates cached Demat holdings for a user in RAM."""
    _DEMAT_PORTFOLIO_CACHE[user_id] = {"timestamp": time.time(), "holdings": holdings}
