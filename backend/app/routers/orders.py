import logging
import sys
import time
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Header
from supabase import Client

from app.config import settings
from app.vault import vault
from app.auth import get_current_user_id, verify_user_access
from app.core.dependencies import get_supabase, get_market_session_status
from app.schemas.orders import (
    PlaceOrderRequest,
    snap_to_exchange_tick,
    _ORDER_IDEMPOTENCY_CACHE,
    _ORDER_IDEMPOTENCY_LOCK,
    _ORDER_IDEMPOTENCY_TTL,
    _ORDER_AUTO_DEBOUNCE_TTL,
)
from app.brokers import get_broker
from app.agent_runner import (
    invalidate_demat_portfolio_cache,
    update_demat_portfolio_cache,
)
from app.routers.auth import _USER_PORTFOLIO_CACHE

logger = logging.getLogger("stokvigil.routers.orders")
router = APIRouter(tags=["orders"])


@router.post("/api/v1/orders/place")
def place_trade_order(
    req: PlaceOrderRequest,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    auth_user_id: Optional[str] = Depends(get_current_user_id),
    db: Client = Depends(get_supabase)
):
    """
    Executes BUY / SELL order for ICICI Direct Breeze Connect API.
    Guaranteed IDOR protection and institutional financial-grade idempotency debouncing.
    """
    verify_user_access(req.user_id, auth_user_id)

    # 1. Determine idempotency key and TTL
    raw_key = (x_idempotency_key or req.idempotency_key or "").strip()
    if raw_key:
        scoped_key = f"custom:{req.user_id}:{raw_key}"
        ttl = _ORDER_IDEMPOTENCY_TTL
    else:
        price_str = f"{req.price:.2f}" if req.price else "0"
        scoped_key = f"auto:{req.user_id}:{req.symbol.upper()}:{req.action.upper()}:{req.order_type.upper()}:{req.quantity}:{price_str}"
        ttl = _ORDER_AUTO_DEBOUNCE_TTL

    now = time.time()
    with _ORDER_IDEMPOTENCY_LOCK:
        # Evict expired idempotency records
        expired_keys = [k for k, v in _ORDER_IDEMPOTENCY_CACHE.items() if now - v.get("timestamp", 0) > v.get("ttl", _ORDER_IDEMPOTENCY_TTL)]
        for k in expired_keys:
            _ORDER_IDEMPOTENCY_CACHE.pop(k, None)

        cached_entry = _ORDER_IDEMPOTENCY_CACHE.get(scoped_key)
        if cached_entry:
            if cached_entry.get("status") == "in_flight":
                logger.warning(f"Concurrent order execution blocked for key {scoped_key}")
                raise HTTPException(
                    status_code=409,
                    detail="Order execution is currently in progress for this request. Please wait."
                )
            elif cached_entry.get("status") == "completed":
                logger.info(f"Returning idempotent cached order response for key {scoped_key}")
                cached_resp = dict(cached_entry.get("response") or {})
                cached_resp["idempotent_replay"] = True
                return cached_resp

        # Mark in-flight to prevent race conditions & duplicate order placement
        _ORDER_IDEMPOTENCY_CACHE[scoped_key] = {
            "status": "in_flight",
            "timestamp": now,
            "ttl": ttl,
            "response": None,
            "user_id": req.user_id
        }

    try:
        cred_res = db.table("user_credentials").select("*").eq("user_id", req.user_id).execute()
        if not cred_res.data:
            raise HTTPException(status_code=400, detail="No ICICI credentials configured for user.")

        cred = cred_res.data[0]
        raw_tok = cred.get("encrypted_session_token")
        session_token = (vault.decrypt(raw_tok) if raw_tok else "").strip().strip('"').strip("'")

        # Pure Institutional Master App Model: Master keys reside exclusively in server configuration
        app_key = (settings.ICICI_MASTER_APP_KEY or "").strip().strip('"').strip("'")
        secret_key = (settings.ICICI_MASTER_SECRET_KEY or "").strip().strip('"').strip("'")

        broker_id = cred.get("broker_id") or "icici"
        adapter = get_broker(broker_id)

        try:
            action_type = "buy" if req.action.upper() == "BUY" else "sell"
            ot_upper = req.order_type.upper()
            if ot_upper in ["STOPLOSS_LIMIT", "STOPLOSS", "SL", "SL-L"]:
                order_type = "stoploss"
                snapped_price = snap_to_exchange_tick(req.price)
                snapped_stoploss = snap_to_exchange_tick(req.trigger_price)
            elif ot_upper == "MARKET":
                order_type = "market"
                snapped_price = 0.0
                snapped_stoploss = 0.0
            else:
                order_type = "limit"
                snapped_price = snap_to_exchange_tick(req.price)
                snapped_stoploss = 0.0

            # Market Session Awareness
            market_open, market_msg = get_market_session_status()
            if getattr(settings, "ENFORCE_MARKET_HOURS", False) and not market_open:
                raise HTTPException(
                    status_code=400,
                    detail=f"Orders rejected during market close: {market_msg}"
                )

            # Dynamic Product Type Resolution (Option A: Auto-detect CNC vs MIS)
            product_type = req.product.lower() if getattr(req, "product", None) else None
            if not product_type:
                if action_type == "sell":
                    # Check if user holds sufficient quantity in Demat holdings
                    user_holdings = adapter.fetch_holdings({
                        "app_key": app_key,
                        "secret_key": secret_key,
                        "session_token": session_token
                    })
                    if user_holdings:
                        update_demat_portfolio_cache(req.user_id, user_holdings)
                    req_sym = req.symbol.upper().replace(".NS", "").replace(".BO", "")
                    has_holding = any(
                        (str(h.get("symbol", "")).upper().replace(".NS", "").replace(".BO", "") == req_sym or
                         str(h.get("stock_code", "")).upper() == req_sym) and
                        int(h.get("quantity", 0) or 0) >= req.quantity
                        for h in user_holdings
                    )
                    product_type = "cash" if has_holding else "margin"
                else:
                    product_type = "cash"

            # SEBI Intraday Short Regulatory Notice
            is_intraday_short = False
            sebi_notice = None
            if action_type == "sell" and product_type == "margin":
                is_intraday_short = True
                sebi_notice = (
                    "SEBI Notice: You do not hold this stock in your Demat account. "
                    "This order has been placed as an Intraday MIS Margin Short. "
                    "You must square off this position before 03:15 PM IST today, "
                    "failing which your broker RMS will auto-square off or you will face exchange auction penalty charges (up to 20%)."
                )

            clean_stock_code = req.symbol.upper().replace(".NS", "").replace(".BO", "").strip()
            is_bse = req.symbol.upper().endswith(".BO") or (clean_stock_code.isdigit() and len(clean_stock_code) == 6)
            exchange_code = "BSE" if is_bse else "NSE"

            order_res = adapter.place_order(
                decrypted_creds={
                    "app_key": app_key,
                    "secret_key": secret_key,
                    "session_token": session_token
                },
                order_params={
                    "stock_code": clean_stock_code,
                    "exchange_code": exchange_code,
                    "product": product_type,
                    "action": action_type,
                    "order_type": order_type,
                    "stoploss": snapped_stoploss,
                    "quantity": req.quantity,
                    "price": snapped_price,
                    "validity": "day"
                }
            )

            # Detect ICICI Breeze Silent RMS Rejection (Status 500 / Error without Python exception)
            broker_status = order_res.get("Status") if isinstance(order_res, dict) else None
            broker_error = order_res.get("Error") if isinstance(order_res, dict) else None

            if isinstance(order_res, dict) and (broker_status not in [200, "200"] or broker_error):
                err_msg = broker_error or f"Broker RMS rejected order with status {broker_status}"
                logger.error(f"ICICI Breeze RMS rejection for {req.symbol}: {err_msg}")
                raise HTTPException(
                    status_code=422,
                    detail=f"Broker RMS rejected order: {err_msg}"
                )

            order_resp = {
                "status": "success",
                "symbol": req.symbol,
                "exchange": exchange_code,
                "action": req.action,
                "quantity": req.quantity,
                "price": snapped_price if order_type in ["limit", "stoploss"] else None,
                "trigger_price": snapped_stoploss if order_type == "stoploss" else None,
                "product": product_type,
                "order_type": order_type,
                "is_intraday_short": is_intraday_short,
                "sebi_notice": sebi_notice,
                "market_session": {"is_open": market_open, "message": market_msg},
                "broker_response": order_res,
                "idempotency_key": raw_key or None,
                "idempotent_replay": False
            }
            if not market_open:
                order_resp["session_warning"] = "Market is currently closed. Order will be processed as AMO or queued by broker."
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error placing Breeze trade order for {req.symbol}: {e}")
            if settings.ENVIRONMENT != "production":
                order_resp = {
                    "status": "simulated",
                    "message": f"Order {req.action} {req.quantity} {req.symbol} processed successfully.",
                    "symbol": req.symbol,
                    "action": req.action,
                    "quantity": req.quantity,
                    "price": snapped_price if req.order_type.upper() == "LIMIT" else None,
                    "product": locals().get("product_type", "cash"),
                    "is_intraday_short": locals().get("is_intraday_short", False),
                    "sebi_notice": locals().get("sebi_notice", None),
                    "market_session": {"is_open": locals().get("market_open", True), "message": locals().get("market_msg", "Market is open.")},
                    "idempotency_key": raw_key or None,
                    "idempotent_replay": False
                }
                if not locals().get("market_open", True):
                    order_resp["session_warning"] = "Market is currently closed. Order will be processed as AMO or queued by broker."
            else:
                raise HTTPException(
                    status_code=502,
                    detail="Broker order placement failed due to an upstream broker error. Please check your credentials or try again."
                )

        # Store completed execution in idempotency cache
        with _ORDER_IDEMPOTENCY_LOCK:
            _ORDER_IDEMPOTENCY_CACHE[scoped_key] = {
                "status": "completed",
                "timestamp": time.time(),
                "ttl": ttl,
                "response": order_resp,
                "user_id": req.user_id
            }

        # Invalidate portfolio caches on successful order execution
        invalidate_demat_portfolio_cache(req.user_id)
        _USER_PORTFOLIO_CACHE.pop(req.user_id, None)

        return order_resp

    except Exception:
        # On error/exception, purge in-flight lock so caller can safely retry
        with _ORDER_IDEMPOTENCY_LOCK:
            _ORDER_IDEMPOTENCY_CACHE.pop(scoped_key, None)
        raise
