import asyncio
import time
import html as html_lib
import json
import logging
import os
import httpx
from typing import Optional, Dict, Any, List
from app.config import settings
from app.auth import mask_id, mask_telegram_token

logger = logging.getLogger("stokvigil.notifications")
logging.getLogger("httpx").setLevel(logging.WARNING)

# Lazy Firebase Init
firebase_app = None

def init_firebase():
    global firebase_app
    if firebase_app:
        return firebase_app
    
    if not settings.FIREBASE_CREDENTIALS_JSON:
        logger.warning("FIREBASE_CREDENTIALS_JSON not configured. FCM alerts will operate in dry-run mode.")
        return None
        
    try:
        import firebase_admin
        from firebase_admin import credentials
        cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
        cred = credentials.Certificate(cred_dict)
        firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully.")
        return firebase_app
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
        return None

async def send_fcm_notification(fcm_token: str, title: str, body: str, data_payload: Optional[dict] = None) -> bool:
    """
    Sends High-Priority Lock-Screen FCM Push Alert to Android/iOS devices.
    """
    if not fcm_token:
        logger.warning("No FCM token provided, skipping FCM push.")
        return False
        
    app = init_firebase()
    if not app:
        logger.info(f"[DRY RUN - FCM Push to {fcm_token[:10]}...] Title: {title} | Body: {body}")
        return True
        
    try:
        from firebase_admin import messaging
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data_payload or {},
            token=fcm_token,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    sound='default',
                    channel_id='stokvigil_high_priority_alerts',
                    icon='ic_notification_stokvigil',
                ),
            ),
        )
        response = messaging.send(message)
        logger.info(f"FCM Notification sent successfully. Message ID: {response}")
        return True
    except Exception as e:
        logger.error(f"Error sending FCM notification: {e}")
        return False

_telegram_http_client: Optional[httpx.AsyncClient] = None

def get_telegram_client() -> httpx.AsyncClient:
    """
    Returns a shared, persistent httpx.AsyncClient with HTTP/2 and connection pooling.
    Eliminates per-alert TCP/TLS negotiation overhead with api.telegram.org.
    """
    global _telegram_http_client
    if _telegram_http_client is None or _telegram_http_client.is_closed:
        _telegram_http_client = httpx.AsyncClient(
            http2=True,
            timeout=10.0,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50)
        )
    return _telegram_http_client

async def close_telegram_client() -> None:
    """Gracefully closes persistent telegram HTTP client connections."""
    global _telegram_http_client
    if _telegram_http_client is not None and not _telegram_http_client.is_closed:
        await _telegram_http_client.aclose()
        _telegram_http_client = None

_TELEGRAM_LOCK = asyncio.Lock()
_TELEGRAM_LAST_SEND_TIME: float = 0.0
_TELEGRAM_MIN_INTERVAL: float = 0.04  # 40ms = max 25 msgs/sec (safe under Telegram global 30 msgs/sec limit)

async def _throttle_telegram() -> None:
    """Enforces a leaky-bucket minimum spacing between Telegram HTTP requests."""
    global _TELEGRAM_LAST_SEND_TIME
    async with _TELEGRAM_LOCK:
        now = time.time()
        elapsed = now - _TELEGRAM_LAST_SEND_TIME
        if elapsed < _TELEGRAM_MIN_INTERVAL:
            await asyncio.sleep(_TELEGRAM_MIN_INTERVAL - elapsed)
        _TELEGRAM_LAST_SEND_TIME = time.time()

# Background Leaky-Bucket Queue Consumer (25 msgs/sec maximum)
_TELEGRAM_QUEUE: asyncio.Queue = asyncio.Queue()
_TELEGRAM_WORKER_TASK: Optional[asyncio.Task] = None

async def enqueue_telegram_notification(chat_id: str, formatted_html_text: str, reply_markup: Optional[dict] = None) -> None:
    """Enqueues an alert for background delivery respecting Telegram rate limits."""
    await _TELEGRAM_QUEUE.put((chat_id, formatted_html_text, reply_markup))

async def telegram_worker() -> None:
    """Consumes alerts from queue, respecting Telegram's 30 msgs/sec limit."""
    while True:
        try:
            chat_id, text, markup = await _TELEGRAM_QUEUE.get()
            try:
                await send_telegram_notification(chat_id, text, markup)
            except Exception as e:
                logger.error(f"Error in telegram_worker sending alert to {mask_id(chat_id)}: {e}")
            finally:
                _TELEGRAM_QUEUE.task_done()
            await asyncio.sleep(0.04)  # 25 requests per second maximum
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Unexpected error in telegram_worker: {e}")
            await asyncio.sleep(0.04)

def start_telegram_worker() -> Optional[asyncio.Task]:
    """Starts the background telegram worker task if an event loop is active."""
    global _TELEGRAM_WORKER_TASK
    if _TELEGRAM_WORKER_TASK is None or _TELEGRAM_WORKER_TASK.done():
        try:
            loop = asyncio.get_running_loop()
            _TELEGRAM_WORKER_TASK = loop.create_task(telegram_worker())
            logger.info("⚡ Background Telegram queue worker started (rate limit: 25 msgs/sec).")
        except RuntimeError:
            pass
    return _TELEGRAM_WORKER_TASK

async def stop_telegram_worker() -> None:
    """Gracefully drains and stops the background telegram worker."""
    global _TELEGRAM_WORKER_TASK
    if _TELEGRAM_WORKER_TASK and not _TELEGRAM_WORKER_TASK.done():
        _TELEGRAM_WORKER_TASK.cancel()
        try:
            await _TELEGRAM_WORKER_TASK
        except asyncio.CancelledError:
            pass
        _TELEGRAM_WORKER_TASK = None

async def send_telegram_notification(chat_id: str, formatted_html_text: str, reply_markup: Optional[dict] = None) -> bool:
    """
    Sends styled HTML Telegram market intelligence alert straight to Telegram chat.
    Uses Telegram Bot HTTP API with optional inline keyboard buttons.
    Protected by Leaky-Bucket Rate Limiter (max 25 msgs/sec) and automatic HTTP 429 retry backoff.
    """
    if not chat_id:
        logger.warning("No Telegram Chat ID provided, skipping Telegram alert.")
        return False
        
    bot_token = settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        logger.info(f"[DRY RUN - Telegram Alert to Chat {mask_id(chat_id)}] Message:\n{formatted_html_text}")
        return True
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": formatted_html_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
    try:
        await _throttle_telegram()
        client = get_telegram_client()
        res = await client.post(url, json=payload)

        # Handle Telegram HTTP 429 Too Many Requests (Rate limit backoff)
        if res.status_code == 429:
            retry_after = 1.0
            try:
                err_data = res.json()
                retry_after = float(err_data.get("parameters", {}).get("retry_after", 1.0))
            except Exception:
                pass
            logger.warning(f"Telegram 429 rate limit hit for Chat ID: {mask_id(chat_id)}. Backing off for {retry_after}s...")
            await asyncio.sleep(retry_after)
            await _throttle_telegram()
            res = await client.post(url, json=payload)

        if res.status_code == 200:
            logger.info(f"Telegram alert sent to Chat ID: {mask_id(chat_id)}")
            return True
        else:
            logger.error(f"Telegram Bot API error [{res.status_code}]: {mask_telegram_token(res.text)}")
            return False
    except Exception as e:
        logger.error(f"Exception sending Telegram notification: {mask_telegram_token(str(e))}")
        return False

def format_telegram_alert(
    symbol: str,
    alert_title: str,
    action_bias: str,
    confluence_score: int,
    catalyst_type: str,
    confluence_drivers: List[str],
    tactical_levels: Optional[Dict[str, Any]] = None,
    demat_position: Optional[Dict[str, Any]] = None,
    metrics_snapshot: Optional[Dict[str, Any]] = None,
    holding_guidance: Optional[str] = None
) -> str:
    """
    Formats institutional-grade market alert as rich HTML for Telegram.
    Includes Action Badges, Demat context, Technical Drivers, and Risk-Reward Levels.
    """
    bias_upper = (action_bias or "HOLD_NEUTRAL").upper()
    if "TARGET_1" in bias_upper or "TRAIL_ALERT" in bias_upper:
        header_badge = "🎯 <b>STOKVIGIL PROTOCOL: TACTICAL LEVEL 1 REACHED & TRAIL TO COST</b> 🎯"
    elif "BUY" in bias_upper or "ACCUMULATE" in bias_upper:
        header_badge = "🟢 <b>STOKVIGIL SIGNAL: ACCUMULATE / BUY WATCH</b> 🟢"
    elif "SELL" in bias_upper:
        header_badge = "🔴 <b>STOKVIGIL SIGNAL: PROFIT BOOK / SELL WATCH</b> 🔴"
    elif "TRAILING" in bias_upper:
        header_badge = "🟡 <b>STOKVIGIL ALERT: TRAILING STOP-LOSS TRIGGER</b> 🟡"
    else:
        header_badge = "⚪ <b>STOKVIGIL UPDATE: MARKET WATCHTOWER</b> ⚪"

    raw_sym = str(symbol).strip().upper()
    clean_sym = raw_sym.replace(".NS", "").replace(".BO", "").strip()
    is_bse = raw_sym.endswith(".BO") or (clean_sym.isdigit() and len(clean_sym) == 6)
    exch_label = "BSE" if is_bse else "NSE"

    safe_catalyst = html_lib.escape(catalyst_type.replace('_', ' '), quote=False)
    safe_title = html_lib.escape(alert_title, quote=False)

    html = f"{header_badge}\n"
    html += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    html += f"📈 <b>Ticker:</b> #{clean_sym} ({exch_label})\n"
    html += f"🎯 <b>Confluence Score:</b> <b>{confluence_score}/100</b>\n"
    html += f"⚡ <b>Catalyst:</b> {safe_catalyst}\n\n"
    html += f"📌 <b>{safe_title}</b>\n\n"

    # Demat Position Context (if held by user in ICICI Direct)
    if demat_position and demat_position.get("is_in_portfolio"):
        qty = demat_position.get("quantity", 0)
        avg_p = demat_position.get("average_buy_price", 0.0)
        pnl_pct = demat_position.get("unrealized_pnl_pct", 0.0)
        pnl_badge = "🟢" if pnl_pct >= 0 else "🔴"
        html += "💼 <b>Your ICICI Direct Demat Snapshot:</b>\n"
        html += f"• Position: {qty} Qty @ Avg ₹{avg_p:,.2f}\n"
        html += f"• Current P&L: {pnl_badge} {pnl_pct:+.2f}%\n"
        if holding_guidance:
            safe_guidance = html_lib.escape(str(holding_guidance), quote=False)
            html += f"• <i>Guidance: {safe_guidance}</i>\n"
        html += "\n"

    # Factual Confluence Drivers
    if confluence_drivers:
        html += "🔍 <b>Multi-Factor Drivers:</b>\n"
        for driver in confluence_drivers[:4]:
            safe_driver = html_lib.escape(str(driver), quote=False)
            html += f"• {safe_driver}\n"
        html += "\n"

    # Tactical Levels (Entry, Target, Stop-Loss, R:R)
    # ZERO-DEFAULT RULE: Never display fake 0.00, None, or placeholder levels if not received
    if tactical_levels and isinstance(tactical_levels, dict):
        entry = tactical_levels.get("entry_range")
        t1 = tactical_levels.get("target_1")
        t2 = tactical_levels.get("target_2")
        sl = tactical_levels.get("protective_stop_loss")
        rr = tactical_levels.get("risk_reward_ratio")
        
        # Validate that tactical levels are actual valid prices/ranges, not 0.00 / N/A / None
        is_valid_entry = entry and str(entry).strip() not in ("N/A", "None", "-", "") and "₹0.00" not in str(entry)
        if is_valid_entry:
            rr_str = f" (R:R: {rr})" if rr and str(rr).strip() not in ("N/A", "None", "") else ""
            if "SELL" in bias_upper:
                html += "📐 <b>Tactical Defense & Downside Levels:</b>\n"
                html += f"• <b>Sell / Short Zone:</b> {entry}\n"
                if t1 and str(t1).strip() not in ("N/A", "None", "-", "") and "₹0.00" not in str(t1):
                    html += f"• <b>Tactical Support 1 (1.5x ATR):</b> {t1}\n"
                if t2 and str(t2).strip() not in ("N/A", "None", "-", "") and "₹0.00" not in str(t2):
                    html += f"• <b>Expansion Support 2 (2.5x ATR):</b> {t2}\n"
                if sl and str(sl).strip() not in ("N/A", "None", "-", "") and "₹0.00" not in str(sl):
                    html += f"• <b>Protective Buy-Stop:</b> {sl}{rr_str}\n"
            elif "TRAILING" in bias_upper:
                html += "🛡️ <b>Capital Defense & Exit Levels:</b>\n"
                html += f"• <b>Defense Range:</b> {entry}\n"
                if t1 and str(t1).strip() not in ("N/A", "None", "-", "") and "₹0.00" not in str(t1):
                    html += f"• <b>Tactical Benchmark 1:</b> {t1}\n"
                if t2 and str(t2).strip() not in ("N/A", "None", "-", "") and "₹0.00" not in str(t2):
                    html += f"• <b>Expansion Benchmark 2:</b> {t2}\n"
                if sl and str(sl).strip() not in ("N/A", "None", "-", "") and "₹0.00" not in str(sl):
                    html += f"• <b>Trailing SL (Exit):</b> {sl}{rr_str}\n"
            else:
                html += "📐 <b>Tactical Risk-Reward Levels:</b>\n"
                html += f"• <b>Entry Range:</b> {entry}\n"
                if t1 and str(t1).strip() not in ("N/A", "None", "-", "") and "₹0.00" not in str(t1):
                    html += f"• <b>Tactical Resistance 1 (1.5x ATR):</b> {t1}\n"
                if t2 and str(t2).strip() not in ("N/A", "None", "-", "") and "₹0.00" not in str(t2):
                    html += f"• <b>Expansion Resistance 2 (2.5x ATR):</b> {t2}\n"
                if sl and str(sl).strip() not in ("N/A", "None", "-", "") and "₹0.00" not in str(sl):
                    html += f"• <b>Stop-Loss:</b> {sl}{rr_str}\n"
            rec_qty = tactical_levels.get("recommended_quantity")
            cap_risk = tactical_levels.get("capital_at_risk")
            if rec_qty and int(rec_qty) > 0 and cap_risk is not None:
                html += f"• <b>Position Sizing (1% Risk Rule):</b> {int(rec_qty)} shares (Max Risk: ₹{float(cap_risk):,.2f})\n"
            html += "• <i>Note: Mathematical volatility benchmarks. Not an advisory price target.</i>\n\n"

    # Technical Metrics Snapshot (ZERO-DEFAULT RULE: Only render actual received metrics)
    if metrics_snapshot and isinstance(metrics_snapshot, dict):
        snapshot_lines = []
        p = metrics_snapshot.get("current_price") or metrics_snapshot.get("price")
        if p is not None and str(p).strip() not in ("None", "N/A", "0", "0.0", "0.00", ""):
            snapshot_lines.append(f"• LTP: ₹{p}")

        day_chg = metrics_snapshot.get("change_pct")
        if day_chg is not None and str(day_chg).strip() not in ("None", "N/A", ""):
            try:
                chg_f = float(day_chg)
                chg_sign = "+" if chg_f > 0 else ""
                snapshot_lines.append(f"• Day Change: <b>{chg_sign}{chg_f:.2f}%</b>")
            except (ValueError, TypeError):
                snapshot_lines.append(f"• Day Change: <b>{day_chg}%</b>")

        orb_st = metrics_snapshot.get("orb_status")
        if orb_st and str(orb_st).strip() not in ("None", "N/A", "NONE", "DATA_INSUFFICIENT", ""):
            safe_orb = html_lib.escape(str(orb_st).replace('_', ' '), quote=False)
            snapshot_lines.append(f"• 15m ORB: <b>{safe_orb}</b>")
            
        rsi_15m = metrics_snapshot.get("rsi_15m")
        rsi_5m = metrics_snapshot.get("rsi_5m")
        if rsi_15m is not None and str(rsi_15m).strip() not in ("None", "N/A", ""):
            rsi_str = f"• 15m RSI: {rsi_15m}"
            if rsi_5m is not None and str(rsi_5m).strip() not in ("None", "N/A", ""):
                rsi_str += f" | 5m RSI: {rsi_5m}"
            snapshot_lines.append(rsi_str)
            
        vwap = metrics_snapshot.get("vwap")
        if vwap is not None and isinstance(vwap, (int, float)) and vwap > 0:
            snapshot_lines.append(f"• VWAP: ₹{vwap:,.2f}")
            
        delivery_pct = metrics_snapshot.get("delivery_pct")
        if delivery_pct is not None and str(delivery_pct).strip() not in ("None", "N/A", ""):
            snapshot_lines.append(f"• Delivery: {delivery_pct}%")
            
        vsa_regime = metrics_snapshot.get("vsa_regime")
        if vsa_regime and str(vsa_regime).strip() not in ("None", "N/A", "UNKNOWN", "NORMAL_VOLUME", ""):
            safe_vsa = html_lib.escape(str(vsa_regime).replace('_', ' '), quote=False)
            snapshot_lines.append(f"• Wyckoff VSA: <b>{safe_vsa}</b>")

        ttm_squeeze = metrics_snapshot.get("ttm_squeeze")
        if ttm_squeeze and str(ttm_squeeze).strip() not in ("None", "N/A", "NORMAL", ""):
            safe_squeeze = html_lib.escape(str(ttm_squeeze).replace('_', ' '), quote=False)
            snapshot_lines.append(f"• Squeeze: <b>{safe_squeeze}</b>")

        if snapshot_lines:
            html += "📊 <b>Market Snapshot:</b>\n"
            for line in snapshot_lines:
                html += f"{line}\n"

    html += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    html += "<i>⚖️ <b>SEBI Non-Advisory Compliance Disclosure:</b> StokVigil AI provides algorithmic quantitative data and mathematical tracking strictly for educational and surveillance purposes. Not investment advice or research recommendations. Trading in securities involves capital risk. Consult a SEBI-registered advisor before executing orders.</i>"
    return html

def build_telegram_inline_keyboard(symbol: str) -> dict:
    """
    Builds interactive institutional inline buttons for Telegram alert:
    1. Direct live StokVigil interactive chart (Web PWA or exchange routed)
    2. Deep link to ICICI Direct Portfolio / Order execution
    3. Official NSE / BSE India quote & corporate actions
    """
    raw_sym = str(symbol).strip().upper()
    clean_sym = raw_sym.replace(".NS", "").replace(".BO", "").strip()
    is_bse = raw_sym.endswith(".BO") or (clean_sym.isdigit() and len(clean_sym) == 6)
    chart_exchange = "BSE" if is_bse else "NSE"
    exchange_name = "BSE India Live" if is_bse else "NSE India Live"
    exchange_url = (
        f"https://www.bseindia.com/stock-share-price/{clean_sym}/"
        if is_bse else
        f"https://www.nseindia.com/get-quotes/equity?symbol={clean_sym}"
    )

    # Deep link to custom StokVigil Web PWA if configured, otherwise direct exchange chart
    web_portal_base = (getattr(settings, "WEB_PORTAL_URL", None) or os.getenv("WEB_PORTAL_URL", "")).strip()
    if web_portal_base:
        chart_url = f"{web_portal_base.rstrip('/')}/chart?symbol={clean_sym}&exchange={chart_exchange}"
    else:
        chart_url = f"https://in.tradingview.com/chart/?symbol={chart_exchange}:{clean_sym}"

    return {
        "inline_keyboard": [
            [
                {"text": "📊 StokVigil Chart", "url": chart_url},
                {"text": "💼 ICICI Direct", "url": "https://secure.icicidirect.com"}
            ],
            [
                {"text": f"🏛️ {exchange_name}", "url": exchange_url}
            ]
        ]
    }


def format_pre_market_war_room_telegram(data: Dict[str, Any]) -> str:
    """
    Formats the 09:00 AM IST Pre-Market War Room Briefing card for Telegram.
    ZERO-DEFAULT RULE: Does not display fake prices or values if not received.
    """
    date_str = data.get("date", "")
    nifty_p = data.get("nifty_price")
    nifty_chg = data.get("nifty_change_pct")
    sensex_p = data.get("sensex_price")
    sensex_chg = data.get("sensex_change_pct")
    vix = data.get("india_vix")
    vix_regime = (data.get("vix_regime") or "").replace('_', ' ')
    
    global_cues = data.get("global_cues") or {}
    dow = global_cues.get("dow_jones_pct")
    nasdaq = global_cues.get("nasdaq_pct")
    nikkei = global_cues.get("nikkei_pct")
    bias = (global_cues.get("bias") or "").replace('_', ' ')
    
    leading = data.get("leading_sectors", [])
    guidance = data.get("tactical_guidance", "")
    
    html = "🌅 <b>STOKVIGIL AI: PRE-MARKET WAR ROOM BRIEFING</b> 🌅\n"
    html += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    if date_str:
        html += f"📅 <b>Date:</b> {date_str} | ⏰ <b>09:00 AM IST (Pre-Open)</b>\n\n"
    
    # Domestic benchmarks (only show actual metrics received)
    benchmark_lines = []
    if nifty_p is not None:
        chg_str = f" (<b>{nifty_chg:+.2f}%</b>)" if nifty_chg is not None else ""
        benchmark_lines.append(f"• <b>NIFTY 50:</b> ₹{nifty_p:,.2f}{chg_str}")
    if sensex_p is not None:
        chg_str = f" (<b>{sensex_chg:+.2f}%</b>)" if sensex_chg is not None else ""
        benchmark_lines.append(f"• <b>SENSEX:</b> {sensex_p:,.2f}{chg_str}")
    if vix is not None:
        regime_str = f" — <i>{vix_regime}</i>" if vix_regime else ""
        benchmark_lines.append(f"• <b>India VIX:</b> {vix}{regime_str}")
    
    if benchmark_lines:
        html += "🏛️ <b>DOMESTIC BENCHMARKS:</b>\n"
        for bline in benchmark_lines:
            html += f"{bline}\n"
        html += "\n"
    
    # Global cues
    cue_lines = []
    if dow is not None or nasdaq is not None:
        parts = []
        if dow is not None:
            parts.append(f"<b>Dow Jones:</b> {dow:+.2f}%")
        if nasdaq is not None:
            parts.append(f"<b>Nasdaq:</b> {nasdaq:+.2f}%")
        cue_lines.append(f"• {' | '.join(parts)}")
    if nikkei is not None:
        cue_lines.append(f"• <b>Nikkei 225:</b> {nikkei:+.2f}%")
    if bias:
        cue_lines.append(f"• <b>Global Bias:</b> <b>{bias}</b>")
        
    if cue_lines:
        html += "🌍 <b>GLOBAL MARKET CUES:</b>\n"
        for cline in cue_lines:
            html += f"{cline}\n"
        html += "\n"
    
    if leading:
        html += "🚀 <b>SECTORAL MOMENTUM WATCH:</b>\n"
        for s in leading:
            safe_name = html_lib.escape(str(s.get('name', 'N/A')), quote=False)
            chg = s.get('change_pct')
            chg_str = f": {chg:+.2f}%" if chg is not None else ""
            html += f"• <b>{safe_name}</b>{chg_str}\n"
        html += "\n"
        
    if guidance:
        safe_guidance = html_lib.escape(str(guidance), quote=False)
        html += "💡 <b>TACTICAL SESSION GUIDANCE:</b>\n"
        html += f"{safe_guidance}\n\n"
    
    html += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    html += "⚡ <i>Automated 5-minute surveillance starts at 09:15 AM IST.</i>"
    return html


def format_post_market_summary_telegram(data: Dict[str, Any]) -> str:
    """
    Formats the 03:45 PM IST Post-Market Executive Closing Bell Scorecard for Telegram.
    ZERO-DEFAULT RULE: Never displays synthetic mock data if an exchange feed is offline.
    """
    date_str = data.get("date") or str(date.today())
    nifty_p = data.get("nifty_price")
    nifty_chg = data.get("nifty_change_pct")
    sensex_p = data.get("sensex_price")
    sensex_chg = data.get("sensex_change_pct")
    vix = data.get("india_vix")
    vix_regime = (data.get("vix_regime") or "").replace('_', ' ')

    adr = data.get("adr_ratio")
    advances = data.get("advances")
    declines = data.get("declines")
    breadth_regime = (data.get("breadth_regime") or "").replace('_', ' ')

    fii_net = data.get("fii_net_cr")
    dii_net = data.get("dii_net_cr")
    fii_dii_bias = data.get("fii_dii_sentiment")

    total_scans = data.get("total_scans_today")
    alerts_fired = data.get("alerts_fired_today")
    t1_hits = data.get("target_1_hit_rate_pct")

    top_sectors = data.get("top_sectors", [])
    laggard_sectors = data.get("laggard_sectors", [])
    notable_movers = data.get("notable_movers", [])

    html = "🔔 <b>STOKVIGIL AI: POST-MARKET EXECUTIVE SUMMARY</b> 🔔\n"
    html += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    html += f"📅 <b>Date:</b> {date_str} | ⏰ <b>03:45 PM IST (Closing Bell)</b>\n\n"

    # 1. Closing Domestic Benchmarks
    b_lines = []
    if nifty_p is not None:
        chg_str = f" (<b>{nifty_chg:+.2f}%</b>)" if nifty_chg is not None else ""
        b_lines.append(f"• <b>NIFTY 50:</b> ₹{nifty_p:,.2f}{chg_str}")
    if sensex_p is not None:
        chg_str = f" (<b>{sensex_chg:+.2f}%</b>)" if sensex_chg is not None else ""
        b_lines.append(f"• <b>BSE SENSEX:</b> {sensex_p:,.2f}{chg_str}")
    if vix is not None:
        reg_str = f" — <i>{vix_regime}</i>" if vix_regime else ""
        b_lines.append(f"• <b>India VIX:</b> {vix}{reg_str}")

    if b_lines:
        html += "🏛️ <b>CLOSING BENCHMARKS:</b>\n"
        for line in b_lines:
            html += f"{line}\n"
        html += "\n"

    # 2. Market Breadth
    if advances is not None and declines is not None:
        html += "⚖️ <b>CASH MARKET BREADTH:</b>\n"
        adr_str = f" (ADR: {adr:.2f})" if adr is not None else ""
        html += f"• <b>Advances:</b> {advances} | <b>Declines:</b> {declines}{adr_str}\n"
        if breadth_regime and breadth_regime != "DATA UNAVAILABLE":
            html += f"• <b>Regime:</b> <b>{breadth_regime}</b>\n"
        html += "\n"

    # 3. Institutional Cash Turnover (FII / DII)
    if fii_net is not None or dii_net is not None:
        html += "💼 <b>INSTITUTIONAL CASH FLOWS (FII / DII):</b>\n"
        if fii_net is not None:
            fii_sign = "+" if fii_net > 0 else ""
            html += f"• <b>FII Net:</b> {fii_sign}₹{fii_net:,.2f} Cr\n"
        if dii_net is not None:
            dii_sign = "+" if dii_net > 0 else ""
            html += f"• <b>DII Net:</b> {dii_sign}₹{dii_net:,.2f} Cr\n"
        if fii_dii_bias:
            html += f"• <b>Flow Sentiment:</b> <b>{fii_dii_bias.replace('_', ' ')}</b>\n"
        html += "\n"

    # 4. Sectoral Winners & Laggards
    if top_sectors or laggard_sectors:
        html += "📊 <b>SECTORAL ROTATION:</b>\n"
        for s in top_sectors[:2]:
            s_name = html_lib.escape(str(s.get('name', 'N/A')), quote=False)
            chg = s.get('change_pct')
            chg_str = f": {chg:+.2f}%" if chg is not None else ""
            html += f"• 🟢 <b>Leader:</b> {s_name}{chg_str}\n"
        for s in laggard_sectors[:2]:
            s_name = html_lib.escape(str(s.get('name', 'N/A')), quote=False)
            chg = s.get('change_pct')
            chg_str = f": {chg:+.2f}%" if chg is not None else ""
            html += f"• 🔴 <b>Laggard:</b> {s_name}{chg_str}\n"
        html += "\n"

    # 5. Algorithmic Surveillance & Performance Scorecard
    scorecard_lines = []
    if total_scans is not None:
        scorecard_lines.append(f"• <b>Surveillance Cycles Today:</b> {total_scans}")
    if alerts_fired is not None:
        scorecard_lines.append(f"• <b>Catalyst Alerts Dispatched:</b> {alerts_fired}")
    if t1_hits is not None and float(t1_hits) > 0:
        scorecard_lines.append(f"• <b>Target 1 Mathematical Hit Rate:</b> <b>{t1_hits:.1f}%</b>")
    if scorecard_lines:
        html += "🎯 <b>ALGORITHMIC SURVEILLANCE SCORECARD:</b>\n"
        for s_line in scorecard_lines:
            html += f"{s_line}\n"
        html += "\n"

    if notable_movers:
        html += "⚡ <b>NOTABLE MOMENTUM CATALYSTS:</b>\n"
        for m in notable_movers[:3]:
            sym = html_lib.escape(str(m.get('symbol', 'N/A')), quote=False)
            m_chg = m.get('change_pct')
            chg_str = f" ({m_chg:+.2f}%)" if m_chg is not None else ""
            bias_m = m.get('bias', 'BREAKOUT')
            html += f"• <b>{sym}</b>{chg_str} — <i>{bias_m}</i>\n"
        html += "\n"

    html += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    html += "🛡️ <i>StokVigil AI surveillance closed for the session. Re-arming for tomorrow's pre-market at 09:00 AM IST.</i>"
    return html

