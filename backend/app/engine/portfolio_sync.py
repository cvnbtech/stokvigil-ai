import concurrent.futures
import json
import logging
import time
import urllib.parse
import urllib.request
from typing import List, Dict, Any, Optional

from app.engine.security_master import resolve_security, is_valid_isin, resolve_symbol_to_isin

logger = logging.getLogger("stokvigil.engine.portfolio_sync")

# User Demat Portfolio Cache: user_id -> {holdings, timestamp} (TTL: 14400 seconds / 4 hours)
_DEMAT_PORTFOLIO_CACHE: Dict[str, Dict[str, Any]] = {}
_DEMAT_PORTFOLIO_CACHE_TTL: float = 14400.0  # 4 hours


def normalize_watchlist_symbol(symbol: str, exchange: Optional[str] = None) -> str:
    """
    Standardizes a ticker symbol for database storage in user_watchlists table:
    - NSE equities: Suffix .NS is stripped -> bare symbol (e.g. 'RELIANCE', 'TCS').
    - BSE equities: Suffix .BO is preserved (e.g. 'RELIANCE.BO', '500325.BO'),
      or 6-digit numeric BSE scrip code (e.g. '500325').
      If exchange is BSE and no .BO suffix, appends .BO (unless 6-digit).
    """
    clean = str(symbol or "").strip().upper()
    if not clean:
        return ""
    if clean.endswith(".NS"):
        clean = clean[:-3]
    if exchange and str(exchange).upper() == "BSE":
        if not clean.endswith(".BO") and not (clean.isdigit() and len(clean) == 6):
            clean = f"{clean}.BO"
    return clean


def resolve_isin_to_nse_symbol(isin: str, fallback_code: str = "") -> str:
    """
    Authoritatively resolves any Indian stock ISIN (e.g. INE155A01022), 6-digit BSE scrip code (500325),
    or broker code (e.g. TELCO) to its official exchange ticker using the in-memory Security Master.
    Sub-millisecond O(1) in RAM with zero network scraping.
    """
    isin_clean = str(isin or "").strip().upper()
    fallback = str(fallback_code or "").strip().upper()

    if isin_clean.endswith(".BO") or isin_clean.endswith(".NS"):
        return isin_clean
    if isin_clean.isdigit() and len(isin_clean) == 6:
        return f"{isin_clean}.BO"
    if fallback.isdigit() and len(fallback) == 6:
        return f"{fallback}.BO"
    if fallback.endswith(".BO") or fallback.endswith(".NS"):
        return fallback

    if is_valid_isin(isin_clean):
        sec = resolve_security(isin_clean)
        if sec.get("symbol"):
            return sec["symbol"]

    if fallback:
        sec = resolve_security(fallback)
        if sec.get("symbol"):
            return sec["symbol"]

    return fallback or isin_clean


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
            raw_exch = str(item.get('exchange_code') or item.get('exchange') or '').upper()

            # Universal Security Master resolution
            sec_meta = resolve_security(isin_code or raw_code, exchange=raw_exch)
            resolved_isin = sec_meta.get("isin") or (isin_code.strip().upper() if is_valid_isin(isin_code) else None)
            clean_symbol = sec_meta.get("symbol") or normalize_watchlist_symbol(raw_code, exchange=raw_exch)
            if not resolved_isin:
                resolved_isin = resolve_symbol_to_isin(clean_symbol) or resolve_symbol_to_isin(raw_code)
            company_name = sec_meta.get("company_name") or str(item.get('stock_name') or item.get('company_name') or '').strip()
            is_bse = sec_meta.get("exchange") == "BSE" or raw_exch == "BSE" or clean_symbol.endswith(".BO")
            bare_symbol = clean_symbol.replace(".BO", "").replace(".NS", "").strip().upper()

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

            if clean_symbol and qty > 0:
                return {
                    "isin": resolved_isin,
                    "symbol": clean_symbol,
                    "clean_symbol": bare_symbol,
                    "name": company_name or bare_symbol,
                    "stock_name": company_name or bare_symbol,
                    "company_name": company_name or bare_symbol,
                    "exchange": "BSE" if is_bse else "NSE",
                    "quantity": qty,
                    "average_price": avg_p,
                    "current_market_price": cmp,
                }
            return None

        result = []
        seen_keys = set()
        max_workers = min(10, max(1, len(raw_holdings)))
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            parsed_items = list(pool.map(_parse_holding, raw_holdings))

        for parsed in parsed_items:
            if not parsed:
                continue
            isin = parsed.get("isin")
            if isin:
                if isin not in seen_keys:
                    seen_keys.add(isin)
                    result.append(parsed)
            elif parsed["symbol"] not in seen_keys:
                seen_keys.add(parsed["symbol"])
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
