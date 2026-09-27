import asyncio
import hmac
import logging
import re
import sys
import time
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Header, Query
from supabase import Client

from app.config import settings
from app.auth import get_current_user_id, get_optional_user_id, mask_id
from app.core.dependencies import get_supabase
from app.core.rate_limiter import check_rate_limit
from app.schemas.market import BacktestRequest
from app.backtester import run_vectorized_strategy_backtest
from app.fii_dii_tracker import fetch_daily_fii_dii_flows
from app.accuracy_verifier import batch_verify_alerts
from app.market_cache import market_cache
from app.db_pool import fetch_all

logger = logging.getLogger("stokvigil.market")

STOCK_SYMBOL_REGEX = re.compile(r'^[A-Z0-9_\-&.]{1,25}$')

router = APIRouter(tags=["Market Intelligence"])

# In-memory accuracy ledger cache (5m TTL)
_ACCURACY_LEDGER_CACHE: Dict[str, Any] = {}
_ACCURACY_LEDGER_TS: float = 0.0


def _is_admin_or_secret(
    x_admin_secret: Optional[str],
    x_cron_secret: Optional[str],
    auth_user_id: Optional[str],
    db: Client
) -> bool:
    """
    Determines whether the caller holds administrative privileges to view
    confidential surveillance symbol watchlists.
    Accepts:
    1. X-Admin-Secret matching ADMIN_SECRET_KEY or active_cron_secret
    2. X-Cron-Secret matching active_cron_secret
    3. Authenticated Bearer JWT whose profile has role='admin' or is_admin=True
    4. Unit test mock tokens when ENVIRONMENT == 'test'
    """
    # 1. Admin Secret Header
    incoming_admin = (x_admin_secret or "").strip().strip('"').strip("'")
    if incoming_admin:
        configured_admin = (settings.ADMIN_SECRET_KEY or "").strip().strip('"').strip("'")
        if configured_admin and hmac.compare_digest(incoming_admin, configured_admin):
            return True
        cron_secret = settings.active_cron_secret
        if cron_secret and hmac.compare_digest(incoming_admin, cron_secret):
            return True
        if settings.ENVIRONMENT == "test" and incoming_admin == "test-admin-secret":
            return True

    # 2. Cron Secret Header
    incoming_cron = (x_cron_secret or "").strip().strip('"').strip("'")
    if incoming_cron:
        cron_secret = settings.active_cron_secret
        if cron_secret and hmac.compare_digest(incoming_cron, cron_secret):
            return True

    # 3. Authenticated Bearer JWT Admin Role
    if auth_user_id:
        if settings.ENVIRONMENT == "test" and auth_user_id == "admin-user-007":
            return True
        try:
            p_res = db.table("profiles").select("role, is_admin").eq("id", auth_user_id).execute()
            if p_res.data:
                prof = p_res.data[0]
                if prof.get("role") == "admin" or prof.get("is_admin") is True:
                    return True
        except Exception as e:
            logger.debug(f"Admin verification query error for user {mask_id(auth_user_id)}: {e}")

    return False


@router.get("/api/market/backtest", dependencies=[Depends(check_rate_limit)])
async def get_strategy_backtest(
    symbol: str = Query(..., min_length=1, max_length=25),
    period: str = Query("1y"),
    interval: str = Query("1d"),
    strategy: str = Query("camarilla_breakout"),
    capital: float = Query(200000.0),
    risk_budget: float = Query(2000.0),
    auth_user_id: str = Depends(get_current_user_id)
):
    """
    In-Memory Vectorized Strategy Backtester.
    Runs historical replay simulation over NSE & BSE equities using 1% risk position sizing.
    Supports Camarilla Breakout and Confluence Trend algorithms.
    Requires authentication to protect compute resources from unauthenticated DoS.
    """
    clean_sym = symbol.strip().upper()
    if not STOCK_SYMBOL_REGEX.match(clean_sym):
        raise HTTPException(status_code=400, detail="Invalid stock symbol format. Only alphanumeric characters, '.', and '-' allowed.")
    
    runner = run_vectorized_strategy_backtest
    result = await asyncio.to_thread(
        runner,
        symbol=clean_sym,
        period=period,
        interval=interval,
        strategy=strategy,
        initial_capital=capital,
        risk_budget=risk_budget
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message", "Backtest data unavailable"))
    return result


@router.post("/api/market/backtest", dependencies=[Depends(check_rate_limit)])
async def post_strategy_backtest(
    req: BacktestRequest,
    auth_user_id: str = Depends(get_current_user_id)
):
    """
    In-Memory Vectorized Strategy Backtester (POST interface).
    Supports custom backtest payload configurations.
    Requires authentication to protect compute resources from unauthenticated DoS.
    """
    clean_sym = req.symbol.strip().upper()
    if not STOCK_SYMBOL_REGEX.match(clean_sym):
        raise HTTPException(status_code=400, detail="Invalid stock symbol format. Only alphanumeric characters, '.', and '-' allowed.")
    
    runner = run_vectorized_strategy_backtest
    result = await asyncio.to_thread(
        runner,
        symbol=clean_sym,
        period=req.period or "1y",
        interval=req.interval or "1d",
        strategy=req.strategy or "camarilla_breakout",
        initial_capital=req.capital or 200000.0,
        risk_budget=req.risk_budget or 2000.0
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message", "Backtest data unavailable"))
    return result


@router.get("/api/market/fii-dii-flows", dependencies=[Depends(check_rate_limit)])
def get_fii_dii_flows(db: Client = Depends(get_supabase)):
    """
    Returns official NSE FII & DII Cash Market daily turnover, net flows in ₹ Crores,
    and institutional sentiment classification with historical multi-day trend.
    """
    try:
        return fetch_daily_fii_dii_flows(db=db)
    except Exception as e:
        logger.error(f"Error retrieving FII/DII flows: {e}")
        return fetch_daily_fii_dii_flows(db=None)


@router.get("/api/market/accuracy-ledger", dependencies=[Depends(check_rate_limit)])
async def get_accuracy_ledger(db: Client = Depends(get_supabase)):
    """
    Public Institutional Audited Accuracy Ledger.
    Computes audited track record and performance metrics for StokVigil AI signals:
    - Target 1 Hit Rate %
    - Average Risk-to-Reward Ratio
    - Cumulative Win/Loss Distribution
    - Real-Time Verifiable Signal Ledger
    Zero PII or private demat information is exposed.
    """
    global _ACCURACY_LEDGER_CACHE, _ACCURACY_LEDGER_TS
    now = time.time()
    if _ACCURACY_LEDGER_CACHE and (now - _ACCURACY_LEDGER_TS) < 300:
        return _ACCURACY_LEDGER_CACHE

    raw_alerts = None
    pooled_rows = await fetch_all(
        "SELECT id, symbol, alert_title, catalyst_type, impact_score, metrics_snapshot, created_at "
        "FROM stok_alerts ORDER BY created_at DESC LIMIT 50"
    )
    if pooled_rows is not None:
        raw_alerts = pooled_rows
    else:
        try:
            res = db.table("stok_alerts").select(
                "id, symbol, alert_title, catalyst_type, impact_score, metrics_snapshot, created_at"
            ).order("created_at", desc=True).limit(50).execute()
            raw_alerts = res.data or []
        except Exception as e:
            logger.warning(f"Error querying stok_alerts for accuracy ledger: {e}")
            raw_alerts = []

    response_data = batch_verify_alerts(raw_alerts or [])

    _ACCURACY_LEDGER_CACHE = response_data
    _ACCURACY_LEDGER_TS = now
    return response_data


@router.get("/api/market/cache-stats")
def get_market_cache_stats(
    x_admin_secret: Optional[str] = Header(None, alias="X-Admin-Secret"),
    x_cron_secret: Optional[str] = Header(None, alias="X-Cron-Secret"),
    auth_user_id: Optional[str] = Depends(get_optional_user_id),
    db: Client = Depends(get_supabase)
):
    """
    Returns telemetry stats for the in-memory market cache.
    Public callers receive aggregate cache metrics while monitored stock symbols
    are strictly redacted to prevent algorithmic reconnaissance.
    Authenticated administrators receive the full symbol telemetry.
    """
    is_admin = _is_admin_or_secret(x_admin_secret, x_cron_secret, auth_user_id, db)
    return {
        "status": "active",
        "cache_stats": market_cache.get_stats(),
        "cached_symbols": market_cache.get_all_cached_symbols() if is_admin else "[REDACTED - Administrator Authentication Required]",
        "admin_access": is_admin
    }
