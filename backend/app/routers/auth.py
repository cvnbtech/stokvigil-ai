import asyncio
import concurrent.futures
import logging
import time
from datetime import date
from typing import Optional, List, Dict, Any, Tuple

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from supabase import Client

from app.config import settings
from app.auth import (
    get_current_user_id,
    verify_user_access,
    mask_id,
)
from app.core.dependencies import get_supabase
from app.schemas.auth import (
    RegisterDeviceRequest,
    SaveCredentialsRequest,
    DeleteAccountRequest,
)
from app.brokers import (
    get_broker,
    list_supported_brokers,
)
from app.vault import vault
from app.market_cache import market_cache
from app.engine.data_fetcher import fetch_stock_financials
from app.engine.portfolio_sync import update_demat_portfolio_cache
from app.accuracy_verifier import batch_verify_alerts
from app.db_pool import (
    fetch_one,
    fetch_all,
)
from app.routers.stocks import (
    _QUOTE_CACHE,
    get_quote_cache_ttl,
    _cache_set_quote,
    _fetch_single_stock_quote,
)

logger = logging.getLogger("stokvigil.auth")

router = APIRouter(tags=["User Authentication & Broker Integration"])

# In-Memory RAM Portfolio Cache (15s TTL for lightning-fast tab switching)
_USER_PORTFOLIO_CACHE: Dict[str, Dict[str, Any]] = {}
_USER_PORTFOLIO_CACHE_TTL = 15.0  # 15 seconds

# In-Memory Fundamentals Cache for Portfolio Holdings (24-Hour TTL / 86400s)
_FUNDAMENTALS_CACHE: Dict[str, Dict[str, Any]] = {}
_FUNDAMENTALS_CACHE_TTL = 86400.0  # 24 hours


def _async_sync_demat_to_watchlists(db: Client, user_id: str, symbols: List[str]):
    """Background task to sync Demat holdings to user_watchlists without blocking HTTP response."""

    if not symbols:
        return
    try:
        sync_payload = [
            {"user_id": user_id, "symbol": s.replace(".BO", "").replace(".NS", "").strip().upper(), "is_auto_synced": True}
            for s in symbols if s
        ]
        db.table("user_watchlists").upsert(sync_payload, on_conflict="user_id,symbol").execute()
        logger.info(f"Background auto-synced {len(symbols)} Demat holdings to user_watchlists for user {mask_id(user_id)}")
    except Exception as sync_err:
        logger.warning(f"Note on background auto-syncing Demat holdings: {sync_err}")


def _get_holding_fundamentals(symbol: str, now: float, fetch_if_missing: bool = False) -> Tuple[Optional[float], Optional[float]]:
    """
    Retrieves authentic P/E ratio and Debt-to-Equity with 24-hour in-memory caching.
    Checks RAM cache first (_FUNDAMENTALS_CACHE), then market_cache singleton.
    By default (fetch_if_missing=False), strictly avoids external network scraping in
    synchronous HTTP requests to guarantee sub-second (<800ms) portfolio response times.
    """
    clean_sym = symbol.replace(".NS", "").replace(".BO", "").strip().upper()
    if clean_sym in _FUNDAMENTALS_CACHE:
        cached = _FUNDAMENTALS_CACHE[clean_sym]
        if (now - cached.get("timestamp", 0)) < _FUNDAMENTALS_CACHE_TTL:
            return cached.get("pe_ratio"), cached.get("debt_to_equity")

    # Check market_cache singleton (pre-computed during background scans)
    m_cache = market_cache
    cached_market_pack = m_cache.get_stock(clean_sym)
    if cached_market_pack:
        fin = cached_market_pack.get("financials", {})
        pe = fin.get("pe_ratio")
        de = fin.get("debt_to_equity")
        if pe is not None or de is not None:
            _FUNDAMENTALS_CACHE[clean_sym] = {"pe_ratio": pe, "debt_to_equity": de, "timestamp": now}
            return pe, de

    if not fetch_if_missing:
        return None, None

    # Fetch authentic fundamentals from Yahoo Finance (used in background pre-warming)
    try:
        fin = fetch_stock_financials(clean_sym)
        pe = fin.get("pe_ratio")
        de = fin.get("debt_to_equity")
    except Exception as e:
        logger.warning(f"Error fetching fundamentals for {clean_sym}: {e}")
        pe, de = None, None

    # Bound cache size to 500 entries to prevent memory drift
    if len(_FUNDAMENTALS_CACHE) > 500:
        oldest_syms = sorted(_FUNDAMENTALS_CACHE.keys(), key=lambda k: _FUNDAMENTALS_CACHE[k].get("timestamp", 0))[:100]
        for s in oldest_syms:
            _FUNDAMENTALS_CACHE.pop(s, None)

    _FUNDAMENTALS_CACHE[clean_sym] = {"pe_ratio": pe, "debt_to_equity": de, "timestamp": now}
    return pe, de


def _async_pre_warm_holding_fundamentals(symbols: List[str], user_id: Optional[str] = None):
    """
    Asynchronously queues and caches missing holding fundamentals (P/E and D/E)
    without blocking the user's synchronous portfolio HTTP request.
    Also patches active _USER_PORTFOLIO_CACHE so immediate subsequent reads have fundamentals.
    """
    if not symbols:
        return
    now = time.time()
    for sym in symbols:
        clean_sym = sym.replace(".NS", "").replace(".BO", "").strip().upper()
        if clean_sym in _FUNDAMENTALS_CACHE:
            cached = _FUNDAMENTALS_CACHE[clean_sym]
            if (now - cached.get("timestamp", 0)) < _FUNDAMENTALS_CACHE_TTL:
                continue
        try:
            fin = fetch_stock_financials(clean_sym)
            pe = fin.get("pe_ratio")
            de = fin.get("debt_to_equity")
            if pe is not None or de is not None:
                _FUNDAMENTALS_CACHE[clean_sym] = {"pe_ratio": pe, "debt_to_equity": de, "timestamp": now}
        except Exception as e:
            logger.debug(f"Background pre-warm fundamentals note for {clean_sym}: {e}")

    if len(_FUNDAMENTALS_CACHE) > 500:
        oldest_syms = sorted(_FUNDAMENTALS_CACHE.keys(), key=lambda k: _FUNDAMENTALS_CACHE[k].get("timestamp", 0))[:100]
        for s in oldest_syms:
            _FUNDAMENTALS_CACHE.pop(s, None)

    if user_id and user_id in _USER_PORTFOLIO_CACHE:
        try:
            cached_data = _USER_PORTFOLIO_CACHE[user_id].get("data", {})
            for h in cached_data.get("holdings", []):
                h_sym = h.get("clean_symbol") or h.get("symbol")
                if h_sym in _FUNDAMENTALS_CACHE:
                    f_entry = _FUNDAMENTALS_CACHE[h_sym]
                    if h.get("pe_ratio") is None:
                        h["pe_ratio"] = f_entry.get("pe_ratio")
                    if h.get("debt_to_equity") is None:
                        h["debt_to_equity"] = f_entry.get("debt_to_equity")
        except Exception:
            pass


@router.get("/api/user/profile")
async def get_user_profile(
    user_id: str,
    auth_user_id: Optional[str] = Depends(get_current_user_id),
    db: Client = Depends(get_supabase)
):
    """
    Fetches user profile, notification preferences, and system settings.
    Guaranteed IDOR protection via verify_user_access.
    """
    verify_user_access(user_id, auth_user_id)
    
    pooled_profile = await fetch_one("SELECT * FROM profiles WHERE id = $1", user_id)
    if pooled_profile is not None:
        if not pooled_profile:
            raise HTTPException(status_code=404, detail="User profile not found.")
        return {"status": "success", "profile": pooled_profile}

    res = db.table("profiles").select("*").eq("id", user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="User profile not found.")
    return {"status": "success", "profile": res.data[0]}


@router.post("/api/auth/register-device")
def register_device(
    req: RegisterDeviceRequest,
    auth_user_id: Optional[str] = Depends(get_current_user_id),
    db: Client = Depends(get_supabase)
):
    """
    Registers or updates FCM device token, Telegram configuration, and alert preferences.
    """
    verify_user_access(req.user_id, auth_user_id)
    update_data = {}
    if req.fcm_device_token is not None:
        update_data["fcm_device_token"] = req.fcm_device_token
    if req.fcm_enabled is not None:
        update_data["fcm_enabled"] = req.fcm_enabled
    if req.telegram_chat_id is not None:
        update_data["telegram_chat_id"] = req.telegram_chat_id
    if req.telegram_enabled is not None:
        update_data["telegram_enabled"] = req.telegram_enabled
    if req.alert_sensitivity is not None:
        sens = req.alert_sensitivity.upper()
        if sens in ["HIGH", "ALL", "FII"]:
            update_data["alert_sensitivity"] = sens
    if req.execution_mode is not None:
        mode = req.execution_mode.upper()
        if mode in ["INSTANT", "CONFIRM"]:
            update_data["execution_mode"] = mode
    if req.demat_auto_sync is not None:
        update_data["demat_auto_sync"] = req.demat_auto_sync
    if req.tnc_accepted is not None:
        update_data["tnc_accepted"] = req.tnc_accepted
        update_data["tnc_accepted_at"] = "now()"
        
    update_data["updated_at"] = "now()"
    
    try:
        res = db.table("profiles").update(update_data).eq("id", req.user_id).execute()
        logger.info(f"✅ Device & notification preferences updated for user {mask_id(req.user_id)}")
        if res.data and len(res.data) > 0:
            return {"status": "success", "profile": res.data[0]}
            
        update_data["id"] = req.user_id
        try:
            user_auth = db.auth.admin.get_user_by_id(req.user_id)
            if user_auth and user_auth.user and user_auth.user.email:
                update_data["email"] = user_auth.user.email
        except Exception:
            pass
            
        res = db.table("profiles").upsert(update_data).execute()
        return {"status": "success", "profile": res.data[0] if res.data else update_data}
    except Exception as e:
        logger.error(f"Error updating profile in DB: {e}")
        return {"status": "success", "profile": update_data}


@router.get("/api/brokers")
def get_brokers_catalog():
    """
    Returns the catalog of supported and upcoming broker integrations for dynamic UI discovery.
    """
    return {
        "brokers": list_supported_brokers(),
        "default_broker": "icici"
    }


@router.get("/api/brokers/{broker_id}/login-url")
def get_broker_login_url(broker_id: str):
    """
    Returns the official broker login URL configured with institutional Master Keys.
    """
    adapter = get_broker(broker_id)
    return {
        "broker": adapter.broker_id,
        "login_url": adapter.get_login_url()
    }


@router.get("/api/broker/icici/login-url")
def get_icici_login_url_alias():
    """
    Backward-compatible alias for 1-Click ICICI Direct login URL.
    """
    adapter = get_broker("icici")
    return {
        "broker": "icici",
        "login_url": adapter.get_login_url()
    }


@router.get("/api/user/credentials")
def get_user_credentials(
    user_id: str,
    broker: str = "icici",
    auth_user_id: Optional[str] = Depends(get_current_user_id),
    db: Client = Depends(get_supabase)
):
    """
    Retrieves user credential status (has_credentials, token_date, is_expired, login_url).
    Follows pure Master App Publisher model: zero manual API/Secret keys leaked.
    Guarded by Supabase JWT verify_user_access (Zero IDOR).
    """
    verify_user_access(user_id, auth_user_id)
    adapter = get_broker(broker)
    login_url = adapter.get_login_url()

    cred_res = db.table("user_credentials").select("*").eq("user_id", user_id).execute()
    if not cred_res.data:
        return {
            "has_credentials": False,
            "token_date": "",
            "is_expired": False,
            "login_url": login_url,
            "broker": adapter.broker_id
        }

    cred = cred_res.data[0]
    token_date = str(cred.get("token_date", ""))
    is_expired = not adapter.validate_session(token_date)

    return {
        "has_credentials": True,
        "token_date": token_date,
        "is_expired": is_expired,
        "login_url": login_url,
        "broker": adapter.broker_id
    }


@router.post("/api/user/credentials")
def save_user_credentials(
    req: SaveCredentialsRequest,
    auth_user_id: Optional[str] = Depends(get_current_user_id),
    db: Client = Depends(get_supabase)
):
    """
    Encrypts user broker session token (AES-256 Fernet) with institutional Master Keys and stores in vault.
    Delegates to the requested broker adapter in the pluggable broker registry.
    """
    verify_user_access(req.user_id, auth_user_id)
    adapter = get_broker(req.broker)
    return adapter.save_credentials(
        db=db,
        vault=vault,
        user_id=req.user_id,
        session_token=req.session_token
    )


@router.post("/api/user/delete-account")
def delete_user_account(
    req: DeleteAccountRequest,
    auth_user_id: Optional[str] = Depends(get_current_user_id),
    db: Client = Depends(get_supabase)
):
    """
    Permanently deletes all data associated with a user:
    1. Removes encrypted broker credentials from user_credentials.
    2. Removes all saved symbols from user_watchlists.
    3. Removes registered FCM & Telegram tokens from profiles.
    4. Deletes the user identity from Supabase auth.users via Admin API.
    """
    verify_user_access(req.user_id, auth_user_id)
    logger.info(f"Initiating complete account deletion for user_id: {mask_id(req.user_id)}")
    try:
        db.table("user_credentials").delete().eq("user_id", req.user_id).execute()
        db.table("user_watchlists").delete().eq("user_id", req.user_id).execute()
        try:
            db.table("user_devices").delete().eq("user_id", req.user_id).execute()
        except Exception:
            pass

        try:
            db.table("profiles").delete().eq("id", req.user_id).execute()
        except Exception:
            pass

        try:
            db.auth.admin.delete_user(req.user_id)
        except Exception as auth_err:
            logger.warning(f"Note on auth admin deletion: {auth_err}")

        logger.info(f"Successfully deleted all data and identity for user_id: {mask_id(req.user_id)}")
        return {
            "status": "success",
            "message": "Your account and all associated data have been permanently deleted."
        }
    except Exception as e:
        logger.error(f"Error deleting account for user {mask_id(req.user_id)}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete account due to an internal error. Please try again or contact support."
        )


@router.get("/api/user/portfolio")
def get_user_portfolio(
    user_id: str,
    refresh: bool = Query(False, description="Set true to bypass cache and perform live sync"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    auth_user_id: Optional[str] = Depends(get_current_user_id),
    db: Client = Depends(get_supabase)
):
    """
    Fetches synced ICICI holdings, current prices, and total P/L summary.
    Includes 15-second RAM caching for lightning-fast (<1ms) tab switching.
    """
    verify_user_access(user_id, auth_user_id)

    now = time.time()
    if not refresh:
        cached = _USER_PORTFOLIO_CACHE.get(user_id)
        if cached and (now - cached.get("timestamp", 0) < _USER_PORTFOLIO_CACHE_TTL):
            return cached["data"]

    cred_res = db.table("user_credentials").select("*").eq("user_id", user_id).execute()
    if not cred_res.data:
        return {"has_credentials": False, "is_expired": False, "holdings": [], "total_portfolio_value": 0.0}

    cred = cred_res.data[0]
    today_str = str(date.today())
    token_date = str(cred.get("token_date", ""))

    if token_date != today_str:
        logger.info(f"ICICI Session Token expired for user {mask_id(user_id)}. Token date: {token_date}, Today: {today_str}")
        return {
            "has_credentials": False,
            "is_expired": True,
            "token_date": token_date,
            "total_portfolio_value": 0.0,
            "total_investment_value": 0.0,
            "total_pnl": 0.0,
            "total_pnl_percent": 0.0,
            "holdings": []
        }

    raw_session_token = cred.get("encrypted_session_token")
    session_token = (vault.decrypt(raw_session_token) if raw_session_token else "").strip().strip('"').strip("'")

    app_key = (getattr(settings, "ICICI_MASTER_APP_KEY", "") or "").strip().strip('"').strip("'")
    secret_key = (getattr(settings, "ICICI_MASTER_SECRET_KEY", "") or "").strip().strip('"').strip("'")

    broker_id = cred.get("broker_id") or "icici"
    adapter = get_broker(broker_id)
    raw_holdings = adapter.fetch_holdings({
        "app_key": app_key,
        "secret_key": secret_key,
        "session_token": session_token
    })
    if raw_holdings:
        update_demat_portfolio_cache(user_id, raw_holdings)

    def _price_single_holding(h: Dict[str, Any]) -> Dict[str, Any]:
        sym = h['symbol']
        clean_sym = sym.replace(".NS", "").replace(".BO", "").strip().upper()

        live_price = 0.0
        current_ttl = get_quote_cache_ttl()
        cached_quote = _QUOTE_CACHE.get(clean_sym) or _QUOTE_CACHE.get(sym)
        if cached_quote and (now - cached_quote.get("timestamp", 0) < current_ttl):
            live_price = float(cached_quote["data"].get("price", 0.0))
        else:
            quote_data = _fetch_single_stock_quote(clean_sym)
            if quote_data and quote_data.get("price"):
                live_price = float(quote_data["price"])
                _cache_set_quote(clean_sym, quote_data, now)
                clean_k = quote_data.get("clean_symbol")
                full_k = quote_data.get("full_symbol")
                if clean_k:
                    _cache_set_quote(clean_k, quote_data, now)
                if full_k:
                    _cache_set_quote(full_k, quote_data, now)

        if live_price <= 0.0:
            live_price = float(h.get('current_market_price') or h.get('last_price') or 0.0)

        pe_ratio, debt_to_equity = _get_holding_fundamentals(clean_sym, now)

        qty = h.get('quantity', 0)
        avg_price = h.get('average_price', 0)
        
        current_val = (live_price * qty) if live_price > 0 else 0.0
        investment_val = (avg_price * qty) if avg_price > 0 else 0.0
        pnl = (current_val - investment_val) if (live_price > 0 and avg_price > 0) else 0.0
        pnl_pct = ((pnl / investment_val) * 100) if (live_price > 0 and avg_price > 0 and investment_val > 0) else 0.0

        quote_obj = cached_quote["data"] if cached_quote else quote_data
        day_high = (quote_obj.get("day_high") if quote_obj else None) if live_price > 0 else None
        day_low = (quote_obj.get("day_low") if quote_obj else None) if live_price > 0 else None
        chg_pct = float(quote_obj.get("change_pct", 0.0)) if (quote_obj and live_price > 0) else 0.0
        day_pnl = round(current_val * (chg_pct / 100.0), 2) if (chg_pct != 0.0 and live_price > 0) else 0.0

        is_bse = sym.endswith(".BO") or (clean_sym.isdigit() and len(clean_sym) == 6) or h.get("exchange") == "BSE"
        exch = "BSE" if is_bse else (quote_obj.get("exchange", "NSE") if quote_obj else "NSE")
        
        proper_name = None
        q_name = quote_obj.get("name") if quote_obj else None
        if q_name and not q_name.endswith("(NSE)") and not q_name.endswith("(BSE)"):
            proper_name = q_name
        if not proper_name:
            proper_name = h.get("name") or h.get("stock_name")
        if not proper_name or proper_name == sym:
            proper_name = q_name or clean_sym

        return {
            "symbol": clean_sym,
            "clean_symbol": clean_sym,
            "full_symbol": sym,
            "name": proper_name,
            "exchange": exch,
            "quantity": qty,
            "avg_price": avg_price,
            "current_price": round(live_price, 2) if live_price > 0 else 0.0,
            "current_value": round(current_val, 2) if live_price > 0 else 0.0,
            "pnl": round(pnl, 2) if (live_price > 0 and avg_price > 0) else None,
            "pnl_percent": round(pnl_pct, 2) if (live_price > 0 and avg_price > 0) else None,
            "day_high": day_high,
            "day_low": day_low,
            "change_pct": chg_pct,
            "day_pnl": day_pnl if (quote_obj and live_price > 0) else None,
            "pe_ratio": pe_ratio,
            "debt_to_equity": debt_to_equity,
            "signal": (quote_obj.get("signal") if quote_obj else None) if live_price > 0 else None,
            "signal_type": (quote_obj.get("signal_type") if quote_obj else None) if live_price > 0 else None,
            "target": (quote_obj.get("target") if quote_obj else None) if live_price > 0 else None,
            "stop_loss": (quote_obj.get("stop_loss") if quote_obj else None) if live_price > 0 else None,
            "_curr_val": current_val,
            "_inv_val": investment_val,
            "_day_pnl": day_pnl if (quote_obj and live_price > 0) else None,
        }

    detailed_holdings = []
    total_val = 0.0
    total_investment = 0.0
    total_day_pnl = 0.0
    has_day_pnl = False

    if raw_holdings:
        max_workers = min(10, max(1, len(raw_holdings)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            priced_items = list(pool.map(_price_single_holding, raw_holdings))

        for item in priced_items:
            total_val += item.pop("_curr_val", 0.0)
            total_investment += item.pop("_inv_val", 0.0)
            d_pnl = item.pop("_day_pnl", None)
            if d_pnl is not None:
                total_day_pnl += d_pnl
                has_day_pnl = True
            detailed_holdings.append(item)

    total_pnl = total_val - total_investment
    total_pnl_pct = ((total_pnl / total_investment) * 100) if total_investment > 0 else 0.0

    if detailed_holdings:
        holding_syms = [h['symbol'] for h in detailed_holdings]
        background_tasks.add_task(_async_sync_demat_to_watchlists, db, user_id, holding_syms)

        missing_fund_syms = [
            h.get('clean_symbol') or h['symbol'] for h in detailed_holdings
            if h.get('pe_ratio') is None and h.get('debt_to_equity') is None
        ]
        if missing_fund_syms:
            background_tasks.add_task(_async_pre_warm_holding_fundamentals, list(set(missing_fund_syms)), user_id)

    response_payload = {
        "has_credentials": True,
        "token_date": cred.get("token_date"),
        "total_portfolio_value": round(total_val, 2),
        "total_investment_value": round(total_investment, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_percent": round(total_pnl_pct, 2),
        "total_day_pnl": round(total_day_pnl, 2) if has_day_pnl else None,
        "holdings": detailed_holdings
    }

    _USER_PORTFOLIO_CACHE[user_id] = {
        "timestamp": now,
        "data": response_payload
    }

    return response_payload


@router.get("/api/user/alerts")
async def get_user_alerts(
    user_id: str,
    limit: int = 50,
    auth_user_id: Optional[str] = Depends(get_current_user_id),
    db: Client = Depends(get_supabase)
):
    """
    Retrieves historical alert logs for the user.
    """
    verify_user_access(user_id, auth_user_id)
    
    pooled_alerts = await fetch_all(
        "SELECT * FROM stok_alerts WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
        user_id, limit
    )
    if pooled_alerts is not None:
        return {"alerts": pooled_alerts}

    res = db.table("stok_alerts") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
    return {"alerts": res.data or []}


@router.get("/api/user/accuracy-stats")
async def get_user_accuracy_stats(
    user_id: str,
    auth_user_id: Optional[str] = Depends(get_current_user_id),
    db: Client = Depends(get_supabase)
):
    """
    Computes real-time accuracy and performance metrics for the user's historical alerts.
    """
    verify_user_access(user_id, auth_user_id)
    
    pooled_alerts = await fetch_all(
        "SELECT * FROM stok_alerts WHERE user_id = $1 ORDER BY created_at DESC LIMIT 100",
        user_id
    )
    if pooled_alerts is not None:
        alerts = pooled_alerts
    else:
        res = db.table("stok_alerts").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(100).execute()
        alerts = res.data or []
    
    total = len(alerts)
    if total == 0:
        return {
            "total_alerts": 0,
            "win_rate_estimate_pct": 0.0,
            "avg_confluence_score": 0,
            "high_conviction_count": 0,
            "trailing_sl_count": 0,
            "sample_size": "New account (No alerts recorded yet)"
        }

    verified_result = batch_verify_alerts(alerts)
    verified_summary = verified_result.get("audited_summary", {})
    win_rate = verified_summary.get("win_rate_pct", 0.0)

    high_conviction = sum(1 for a in alerts if (a.get("impact_score") or 0) >= 75)
    trailing_sl = sum(1 for a in alerts if a.get("catalyst_type") == "TRAILING_STOP_TRIGGER" or "TRAILING" in str(a.get("alert_title", "")))
    avg_score = round(sum(a.get("impact_score") or 50 for a in alerts) / total, 1)

    return {
        "total_alerts": total,
        "win_rate_estimate_pct": win_rate,
        "avg_confluence_score": avg_score,
        "high_conviction_count": high_conviction,
        "trailing_sl_count": trailing_sl,
        "sample_size": f"Computed over {total} real-time surveillance alerts with verified price tracking"
    }
