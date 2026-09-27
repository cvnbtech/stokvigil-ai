import asyncio
import hmac
import logging
import sys
from datetime import date
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Header
from supabase import Client

from app.config import settings
from app.auth import mask_id
from app.core.dependencies import get_supabase, verify_cron_secret
from app.schemas.cron import TelegramWebhookPayload
from app.agent_runner import (
    evaluate_user_portfolio_and_watchlists,
    sync_market_cache_for_all_active_symbols,
    reset_ai_scan_counter,
    update_demat_portfolio_cache,
)
from app.macro_filter import (
    fetch_pre_market_war_room_data,
    fetch_macro_market_regime,
    fetch_market_breadth_adr,
    get_sector_20d_return,
    SECTOR_INDEX_MAP,
)
from app.notifications import (
    send_telegram_notification,
    send_fcm_notification,
    format_pre_market_war_room_telegram,
    format_post_market_summary_telegram,
)
from app.fii_dii_tracker import fetch_daily_fii_dii_flows
from app.vault import vault
from app.brokers import get_broker
from app.db_pool import fetch_all
from app.routers.market import get_accuracy_ledger
from app.routers.auth import _async_sync_demat_to_watchlists

logger = logging.getLogger("stokvigil.cron")

router = APIRouter(tags=["Cron & Webhook Automation"])

_scan_in_progress = False
_DAILY_SCAN_CYCLES_COUNT: int = 0
_DAILY_SCAN_CYCLES_DATE: str = ""


async def execute_multi_user_market_scan(db: Client) -> Dict[str, Any]:
    """
    Executes full multi-user market intelligence scan.
    Returns structured execution telemetry including scanned symbols, users, and dispatched alerts.
    """
    global _scan_in_progress, _DAILY_SCAN_CYCLES_COUNT, _DAILY_SCAN_CYCLES_DATE
    if _scan_in_progress:
        logger.info("⚡ Multi-user market scan is already running. Skipping duplicate task.")
        return {
            "status": "skipped",
            "message": "Market scan already in progress.",
            "timestamp": str(date.today())
        }

    _scan_in_progress = True
    today_str = str(date.today())
    if _DAILY_SCAN_CYCLES_DATE != today_str:
        _DAILY_SCAN_CYCLES_DATE = today_str
        _DAILY_SCAN_CYCLES_COUNT = 0
    _DAILY_SCAN_CYCLES_COUNT += 1
    
    reset_ai_scan_counter()

    try:
        logger.info("🚀 Multi-user market intelligence scan started...")
        synced_symbols_count = await sync_market_cache_for_all_active_symbols(db)
        logger.info(f"⚡ In-Memory Market Cache refreshed: {synced_symbols_count} unique symbols pre-computed.")

        macro_snapshot = await asyncio.to_thread(fetch_macro_market_regime)

        pooled_profiles = await fetch_all(
            "SELECT id, email, fcm_device_token, fcm_enabled, telegram_chat_id, telegram_enabled, alert_sensitivity, execution_mode, demat_auto_sync FROM profiles"
        )
        if pooled_profiles is not None:
            profiles_data = pooled_profiles
        else:
            profiles_res = db.table("profiles").select(
                "id, email, fcm_device_token, fcm_enabled, telegram_chat_id, telegram_enabled, alert_sensitivity, execution_mode, demat_auto_sync"
            ).execute()
            profiles_data = profiles_res.data or []

        pooled_watchlists = await fetch_all(
            "SELECT user_id, symbol, is_auto_synced FROM user_watchlists WHERE symbol IS NOT NULL"
        )
        if pooled_watchlists is not None:
            watchlists_data = pooled_watchlists
        else:
            try:
                watchlists_res = db.table("user_watchlists").select("user_id, symbol, is_auto_synced").not_.is_("symbol", "null").limit(50000).execute()
                watchlists_data = watchlists_res.data or []
            except Exception:
                watchlists_res = db.table("user_watchlists").select("user_id, symbol, is_auto_synced").limit(50000).execute()
                watchlists_data = watchlists_res.data or []

        pooled_creds = await fetch_all(
            "SELECT * FROM user_credentials WHERE token_date = $1",
            today_str
        )
        if pooled_creds is not None:
            creds_data = pooled_creds
        else:
            creds_res = db.table("user_credentials").select("*").eq("token_date", today_str).execute()
            creds_data = creds_res.data or []

        for c in creds_data:
            if "broker_id" not in c or not c.get("broker_id"):
                c["broker_id"] = "icici"

        user_contexts: Dict[str, Dict[str, Any]] = {}
        for p in profiles_data:
            uid = str(p.get("id"))
            user_contexts[uid] = {
                "profile": p,
                "symbols": set(),
                "cred": None
            }

        for w in watchlists_data:
            uid = str(w.get("user_id"))
            sym = w.get("symbol")
            if sym:
                clean_s = sym.strip().upper()
                if uid in user_contexts:
                    user_contexts[uid]["symbols"].add(clean_s)
                else:
                    user_contexts[uid] = {
                        "profile": {"id": uid},
                        "symbols": {clean_s},
                        "cred": None
                    }

        for c in creds_data:
            uid = str(c.get("user_id"))
            if uid in user_contexts:
                user_contexts[uid]["cred"] = c
            else:
                user_contexts[uid] = {
                    "profile": {"id": uid},
                    "symbols": set(),
                    "cred": c
                }

        users = profiles_data
        scanned_users = 0
        all_generated_alerts = []
        user_sem = asyncio.Semaphore(10)

        async def _evaluate_user_worker(u):
            nonlocal scanned_users
            uid = str(u.get('id'))
            preloaded_ctx = user_contexts.get(uid)
            async with user_sem:
                try:
                    alerts = await evaluate_user_portfolio_and_watchlists(
                        uid, db, macro_data=macro_snapshot, preloaded_user_ctx=preloaded_ctx
                    )
                    scanned_users += 1
                    return alerts or []
                except Exception as user_err:
                    logger.error(f"Error scanning user {mask_id(uid)}: {user_err}")
                    return []

        if users:
            user_results = await asyncio.gather(*(_evaluate_user_worker(u) for u in users), return_exceptions=False)
            for res in user_results:
                if isinstance(res, list):
                    all_generated_alerts.extend(res)

        logger.info(f"✅ Background market scan finished: {synced_symbols_count} symbols, {scanned_users} users scanned, {len(all_generated_alerts)} alerts dispatched.")
        return {
            "status": "completed",
            "message": f"Market intelligence scan completed: {synced_symbols_count} symbols, {scanned_users} users scanned, {len(all_generated_alerts)} alerts dispatched.",
            "synced_symbols_count": synced_symbols_count,
            "scanned_users": scanned_users,
            "alerts_dispatched": len(all_generated_alerts),
            "timestamp": today_str
        }
    except Exception as e:
        logger.error(f"❌ Error in background market scan: {e}", exc_info=True)
        return {
            "status": "error",
            "error": "Market intelligence scan failed." if settings.ENVIRONMENT == "production" else str(e),
            "timestamp": today_str
        }
    finally:
        _scan_in_progress = False


@router.post("/api/cron/multi-user-scan")
async def run_multi_user_scan(
    x_cron_secret: Optional[str] = Header(None, alias="X-Cron-Secret"),
    db: Client = Depends(get_supabase)
):
    """
    5-Minute Cron Endpoint triggered during Indian market hours.
    Shielded by exact X-Cron-Secret header token.
    Executes scan synchronously during the HTTP request to guarantee 100% CPU allocation
    under Cloud Run Free Tier, preventing container freezing while streaming real-time logs.
    """
    verify_cron_secret(x_cron_secret)
    return await execute_multi_user_market_scan(db)


@router.post("/api/cron/morning-token-reminder")
async def run_morning_token_reminder(
    x_cron_secret: Optional[str] = Header(None, alias="X-Cron-Secret"),
    db: Client = Depends(get_supabase)
):
    """
    Automated 08:50 AM IST Morning Push Notification.
    Prompts users whose ICICI session token is expired to authenticate 25 minutes before market open.
    """
    verify_cron_secret(x_cron_secret)

    today_str = str(date.today())
    creds_res = db.table("user_credentials").select("*").execute()
    credentials_list = creds_res.data or []
    for cred in credentials_list:
        if "broker_id" not in cred or not cred.get("broker_id"):
            cred["broker_id"] = "icici"

    reminded_users = 0
    synced_users = 0

    app_key = (getattr(settings, "ICICI_MASTER_APP_KEY", "") or "").strip().strip('"').strip("'")
    secret_key = (getattr(settings, "ICICI_MASTER_SECRET_KEY", "") or "").strip().strip('"').strip("'")

    for cred in credentials_list:
        uid = cred.get("user_id")
        token_date = cred.get("token_date")
        if str(token_date) != today_str:
            p_res = db.table("profiles").select("*").eq("id", uid).execute()
            if p_res.data:
                profile = p_res.data[0]
                fcm_tok = profile.get("fcm_device_token")
                fcm_on = profile.get("fcm_enabled", False)
                tg_id = profile.get("telegram_chat_id")
                tg_on = profile.get("telegram_enabled", False)

                title = "🔔 ICICI Direct Demat Session Expired"
                body = "Market opens in 25 mins! Tap here to authenticate your session for today's surveillance."

                if fcm_tok and fcm_on:
                    await send_fcm_notification(fcm_tok, title, body, {
                        "type": "TOKEN_REFRESH",
                        "route": "/credentials"
                    })

                if tg_id and tg_on:
                    tg_msg = (
                        "🔔 <b>StokVigil AI: Morning Demat Surveillance Alert</b>\n\n"
                        "Your ICICI Direct session token has expired for today. Market opens in 25 minutes (09:15 AM IST).\n\n"
                        "👉 <i>Open the StokVigil app or portal, navigate to ICICI Credentials, and log in to activate today's surveillance.</i>"
                    )
                    await send_telegram_notification(tg_id, tg_msg)
                
                reminded_users += 1
        else:
            try:
                raw_tok = cred.get("encrypted_session_token")
                session_token = (vault.decrypt(raw_tok) if raw_tok else "").strip().strip('"').strip("'")
                broker_id = cred.get("broker_id") or "icici"
                adapter = get_broker(broker_id)
                m_holdings = await asyncio.to_thread(
                    adapter.fetch_holdings,
                    {"app_key": app_key, "secret_key": secret_key, "session_token": session_token}
                )
                if m_holdings:
                    update_demat_portfolio_cache(uid, m_holdings)
                    holding_syms = [h.get('symbol') for h in m_holdings if h.get('symbol')]
                    if holding_syms:
                        _async_sync_demat_to_watchlists(db, uid, holding_syms)
                    synced_users += 1
            except Exception as sync_err:
                logger.debug(f"Morning pre-sync note for user {mask_id(uid)}: {sync_err}")

    return {
        "status": "completed",
        "reminded_users_count": reminded_users,
        "synced_users_count": synced_users,
        "date": today_str
    }


@router.post("/api/cron/pre-market-briefing")
async def run_pre_market_briefing(
    x_cron_secret: Optional[str] = Header(None, alias="X-Cron-Secret"),
    db: Client = Depends(get_supabase)
):
    """
    Automated 09:00 AM IST Pre-Market War Room Briefing.
    Dispatches global cues, India VIX regime, and sectoral tailwinds 15 minutes before cash market open.
    Shielded by X-Cron-Secret header token.
    """
    verify_cron_secret(x_cron_secret)

    # Automated 30-day database retention maintenance
    try:
        from app.maintenance import prune_historical_alerts
        asyncio.create_task(prune_historical_alerts(db, retention_days=30))
    except Exception as m_err:
        logger.warning(f"Maintenance prune note: {m_err}")

    # Automated FII/DII institutional flow sync
    try:
        asyncio.create_task(asyncio.to_thread(fetch_daily_fii_dii_flows, db))
    except Exception as fii_err:
        logger.warning(f"FII/DII sync note: {fii_err}")

    today_str = str(date.today())
    war_room_data = await asyncio.to_thread(fetch_pre_market_war_room_data)
    telegram_html = format_pre_market_war_room_telegram(war_room_data)
    
    profiles_res = db.table("profiles").select("id, telegram_chat_id, telegram_enabled, fcm_device_token, fcm_enabled").execute()
    users = profiles_res.data or []
    briefed_count = 0
    fcm_title = "🌅 StokVigil AI: Pre-Market War Room Briefing"
    n_chg = war_room_data.get('nifty_change_pct')
    vix_val = war_room_data.get('india_vix')
    bias_val = (war_room_data.get('global_cues') or {}).get('bias')

    body_parts = []
    if n_chg is not None:
        body_parts.append(f"NIFTY: {n_chg:+.2f}%")
    if vix_val is not None:
        body_parts.append(f"VIX: {vix_val}")
    if bias_val and bias_val != "DATA_UNAVAILABLE":
        body_parts.append(f"Global Bias: {str(bias_val).replace('_', ' ')}")
    fcm_body = " | ".join(body_parts) if body_parts else "Pre-Market intelligence briefing is ready."
    
    sem = asyncio.Semaphore(20)

    async def _notify_single_user(u: Dict[str, Any]) -> bool:
        tg_id = u.get("telegram_chat_id")
        tg_on = u.get("telegram_enabled", False)
        fcm_tok = u.get("fcm_device_token")
        fcm_on = u.get("fcm_enabled", False)
        sent = False
        async with sem:
            if tg_id and tg_on:
                try:
                    await send_telegram_notification(tg_id, telegram_html)
                    sent = True
                except Exception as tg_err:
                    logger.warning(f"Telegram pre-market dispatch failed for chat {mask_id(tg_id)}: {tg_err}")
            if fcm_tok and fcm_on:
                try:
                    await send_fcm_notification(fcm_tok, fcm_title, fcm_body, {
                        "type": "PRE_MARKET_BRIEFING",
                        "route": "/dashboard"
                    })
                    sent = True
                except Exception as fcm_err:
                    logger.warning(f"FCM pre-market dispatch failed for user: {fcm_err}")
        return sent

    if users:
        dispatch_results = await asyncio.gather(*[_notify_single_user(u) for u in users], return_exceptions=True)
        briefed_count = sum(1 for r in dispatch_results if r is True)
            
    logger.info(f"✅ 09:00 AM Pre-Market War Room Briefing sent to {briefed_count} users.")
    return {
        "status": "completed",
        "briefed_users_count": briefed_count,
        "war_room_data": war_room_data,
        "date": today_str
    }


@router.post("/api/cron/post-market-summary")
async def run_post_market_summary(
    x_cron_secret: Optional[str] = Header(None, alias="X-Cron-Secret"),
    db: Client = Depends(get_supabase)
):
    """
    Automated 03:45 PM IST Post-Market Executive Closing Bell Scorecard.
    Aggregates closing benchmarks, cash market breadth (ADR), FII/DII institutional net flows,
    sector rotation leaders/laggards, and algorithmic Target 1 hit rates.
    Dispatches to registered Telegram and FCM users.
    Shielded by X-Cron-Secret header token.
    """
    verify_cron_secret(x_cron_secret)

    today_str = str(date.today())
    macro_data = await asyncio.to_thread(fetch_macro_market_regime)
    breadth_data = await asyncio.to_thread(fetch_market_breadth_adr)
    fii_dii_data = await asyncio.to_thread(fetch_daily_fii_dii_flows, db)

    top_sectors = []
    laggard_sectors = []
    try:
        sec_results = []
        for sec_name, sec_ticker in SECTOR_INDEX_MAP.items():
            ret = get_sector_20d_return(sec_name)
            if ret is not None:
                sec_results.append({"name": sec_name, "change_pct": ret})
        sec_results.sort(key=lambda x: x["change_pct"], reverse=True)
        if sec_results:
            top_sectors = sec_results[:2]
            laggard_sectors = sec_results[-2:]
    except Exception as sec_err:
        logger.warning(f"Sector aggregation note for post-market summary: {sec_err}")

    today_start = f"{today_str}T00:00:00"
    today_alerts = []
    try:
        res = db.table("stok_alerts").select(
            "id, symbol, alert_title, catalyst_type, metrics_snapshot, created_at"
        ).gte("created_at", today_start).execute()
        today_alerts = res.data or []
    except Exception as alert_err:
        logger.warning(f"Error querying today alerts for post-market summary: {alert_err}")

    target_1_hit_rate = None
    try:
        ledger_res = await get_accuracy_ledger(db=db)
        if ledger_res and isinstance(ledger_res, dict):
            target_1_hit_rate = ledger_res.get("target_1_hit_rate_pct")
    except Exception:
        pass

    notable_movers = []
    for a in today_alerts[:4]:
        sym = a.get("symbol", "")
        metrics = a.get("metrics_snapshot") or {}
        chg = metrics.get("change_pct") or metrics.get("day_change_pct")
        bias = a.get("catalyst_type", "BREAKOUT")
        notable_movers.append({
            "symbol": sym,
            "change_pct": chg,
            "bias": bias
        })

    summary_payload = {
        "date": today_str,
        "nifty_price": macro_data.get("nifty_price"),
        "nifty_change_pct": macro_data.get("nifty_change_pct"),
        "sensex_price": macro_data.get("sensex_price"),
        "sensex_change_pct": macro_data.get("sensex_change_pct"),
        "india_vix": macro_data.get("india_vix"),
        "vix_regime": macro_data.get("vix_regime"),
        "adr_ratio": breadth_data.get("adr_ratio"),
        "advances": breadth_data.get("advances"),
        "declines": breadth_data.get("declines"),
        "breadth_regime": breadth_data.get("breadth_regime"),
        "fii_net_cr": fii_dii_data.get("fii_net_cr"),
        "dii_net_cr": fii_dii_data.get("dii_net_cr"),
        "fii_dii_sentiment": fii_dii_data.get("sentiment"),
        "total_scans_today": _DAILY_SCAN_CYCLES_COUNT if _DAILY_SCAN_CYCLES_DATE == today_str else len(today_alerts),
        "alerts_fired_today": len(today_alerts),
        "target_1_hit_rate_pct": target_1_hit_rate,
        "top_sectors": top_sectors,
        "laggard_sectors": laggard_sectors,
        "notable_movers": notable_movers
    }

    telegram_html = format_post_market_summary_telegram(summary_payload)

    profiles_res = db.table("profiles").select(
        "id, telegram_chat_id, telegram_enabled, fcm_device_token, fcm_enabled"
    ).execute()
    users = profiles_res.data or []
    briefed_count = 0

    fcm_title = "🔔 StokVigil AI: Post-Market Closing Bell Digest"
    n_chg = summary_payload.get("nifty_change_pct")
    fii_n = summary_payload.get("fii_net_cr")
    fcm_parts = []
    if n_chg is not None:
        fcm_parts.append(f"NIFTY: {n_chg:+.2f}%")
    if fii_n is not None:
        fcm_parts.append(f"FII Net: ₹{fii_n:,.0f} Cr")
    fcm_parts.append(f"Alerts: {len(today_alerts)}")
    fcm_body = " | ".join(fcm_parts)

    sem = asyncio.Semaphore(20)

    async def _notify_single_user(u: Dict[str, Any]) -> bool:
        tg_id = u.get("telegram_chat_id")
        tg_on = u.get("telegram_enabled", False)
        fcm_tok = u.get("fcm_device_token")
        fcm_on = u.get("fcm_enabled", False)
        sent = False
        async with sem:
            if tg_id and tg_on:
                try:
                    await send_telegram_notification(tg_id, telegram_html)
                    sent = True
                except Exception as tg_err:
                    logger.warning(f"Telegram post-market dispatch failed for chat {mask_id(tg_id)}: {tg_err}")
            if fcm_tok and fcm_on:
                try:
                    await send_fcm_notification(fcm_tok, fcm_title, fcm_body, {
                        "type": "POST_MARKET_SUMMARY",
                        "route": "/dashboard"
                    })
                    sent = True
                except Exception as fcm_err:
                    logger.warning(f"FCM post-market dispatch failed for user: {fcm_err}")
        return sent

    if users:
        dispatch_results = await asyncio.gather(*[_notify_single_user(u) for u in users], return_exceptions=True)
        briefed_count = sum(1 for r in dispatch_results if r is True)

    logger.info(f"✅ 03:45 PM Post-Market Closing Bell Summary sent to {briefed_count} users.")
    return {
        "status": "completed",
        "briefed_users_count": briefed_count,
        "summary": summary_payload,
        "date": today_str
    }


@router.post("/api/telegram/webhook")
async def telegram_webhook(
    payload: TelegramWebhookPayload,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None, alias="X-Telegram-Bot-Api-Secret-Token"),
    db: Client = Depends(get_supabase)
):
    """
    Telegram Bot Webhook endpoint handling `/start <USER_ID>` deep link pairing.
    Protected by X-Telegram-Bot-Api-Secret-Token header validation.
    """
    expected = (getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "") or "").strip().strip('"').strip("'")
    if expected:
        incoming = (x_telegram_bot_api_secret_token or "").strip().strip('"').strip("'")
        if not incoming or not hmac.compare_digest(incoming, expected):
            logger.warning("Blocked Telegram webhook: Secret token header mismatch or missing.")
            raise HTTPException(status_code=403, detail="Unauthorized webhook source: Invalid secret token.")
    elif getattr(settings, "ENVIRONMENT", "") == "production":
        logger.critical("TELEGRAM_WEBHOOK_SECRET is unconfigured in production mode. Rejecting all webhook calls.")
        raise HTTPException(status_code=503, detail="Telegram webhook service is temporarily unconfigured.")

    msg = payload.message or {}
    if not msg:
        return {"status": "ignored"}
        
    chat_id = str(msg.get("chat", {}).get("id", "")).strip()
    text = msg.get("text", "").strip()
    logger.info(f"📩 Incoming Telegram Webhook from Chat ID: {mask_id(chat_id)}")

    if not chat_id:
        return {"status": "ignored"}

    user_param = None
    email_detected = False

    if text.startswith("/start") or text.startswith("/link"):
        parts = text.split(" ")
        if len(parts) > 1:
            candidate = parts[1].strip()
            if "@" in candidate:
                email_detected = True
            else:
                user_param = candidate
    elif len(text) >= 10:
        if "@" in text:
            email_detected = True
        else:
            user_param = text.strip()

    if email_detected:
        logger.warning(f"Rejected Telegram linking attempt using email address from Chat ID: {mask_id(chat_id)}")
        warn_msg = (
            "⚠️ <b>Email Linking Disabled for Account Security</b>\n\n"
            "To protect your surveillance feed from unauthorized access, linking via email is not permitted.\n\n"
            "👉 <b>How to Link Securely:</b>\n"
            "1. Open the StokVigil App or Web Portal $\\to$ <b>Settings</b>.\n"
            f"2. Save your Telegram Chat ID (<code>{chat_id}</code>) directly in the Notification Settings.\n"
            "3. Or copy your <b>User ID</b> from the app settings and send: <code>/start YOUR_USER_ID</code>."
        )
        await send_telegram_notification(chat_id, warn_msg)
        return {"status": "rejected", "reason": "email_not_permitted"}

    if user_param:
        logger.info(f"🔗 Linking Telegram Chat ID: {mask_id(chat_id)} to user identifier: {mask_id(user_param)}")
        try:
            res = db.table("profiles").update({
                "telegram_chat_id": chat_id,
                "telegram_enabled": True,
                "updated_at": "now()"
            }).eq("id", user_param).execute()

            if not res.data or len(res.data) == 0:
                upsert_payload = {
                    "id": user_param,
                    "telegram_chat_id": chat_id,
                    "telegram_enabled": True,
                    "updated_at": "now()"
                }
                db.table("profiles").upsert(upsert_payload).execute()

            logger.info(f"✅ Successfully linked Telegram Chat ID {mask_id(chat_id)} to user {mask_id(user_param)}")
            welcome_msg = (
                "✅ <b>StokVigil AI Successfully Linked!</b>\n\n"
                f"Your Telegram Chat ID (<code>{chat_id}</code>) has been connected to your StokVigil AI account.\n\n"
                "You will now receive real-time institutional alerts, 200 EMA breakout signals, and Demat notifications directly here."
            )
            await send_telegram_notification(chat_id, welcome_msg)
            return {"status": "linked", "user_param": mask_id(user_param), "chat_id": mask_id(chat_id)}
        except Exception as e:
            logger.error(f"Error linking telegram user in Supabase: {e}")
            await send_telegram_notification(chat_id, "⚠️ Connection error. Please save your Chat ID in the app settings.")
            return {"status": "error", "detail": "Connection error"}
    else:
        help_msg = (
            f"👋 <b>Welcome to StokVigil AI Bot!</b>\n\n"
            f"Your Telegram Chat ID is: <code>{chat_id}</code>\n\n"
            "👉 <b>How to link:</b>\n"
            "1. Open the StokVigil App or Web Portal $\to$ Settings.\n"
            f"2. Paste <code>{chat_id}</code> into the <b>Telegram Chat ID</b> field and tap Save.\n"
            "3. Or tap 'Connect @StokVigilAi_bot' directly from the app."
        )
        await send_telegram_notification(chat_id, help_msg)
        return {"status": "help_sent", "chat_id": mask_id(chat_id)}
