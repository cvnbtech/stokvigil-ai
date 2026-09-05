import json
import logging
import httpx
from typing import Optional, Dict, Any, List
from app.config import settings

logger = logging.getLogger("stokvigil.notifications")

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

async def send_telegram_notification(chat_id: str, formatted_html_text: str, reply_markup: Optional[dict] = None) -> bool:
    """
    Sends styled HTML Telegram market intelligence alert straight to Telegram chat.
    Uses Telegram Bot HTTP API with optional inline keyboard buttons.
    """
    if not chat_id:
        logger.warning("No Telegram Chat ID provided, skipping Telegram alert.")
        return False
        
    bot_token = settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        logger.info(f"[DRY RUN - Telegram Alert to Chat {chat_id}] Message:\n{formatted_html_text}")
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
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, json=payload)
            if res.status_code == 200:
                logger.info(f"Telegram alert sent to Chat ID: {chat_id}")
                return True
            else:
                logger.error(f"Telegram Bot API error [{res.status_code}]: {res.text}")
                return False
    except Exception as e:
        logger.error(f"Exception sending Telegram notification: {e}")
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
    if "BUY" in bias_upper or "ACCUMULATE" in bias_upper:
        header_badge = "🟢 <b>STOKVIGIL SIGNAL: ACCUMULATE / BUY WATCH</b> 🟢"
    elif "SELL" in bias_upper:
        header_badge = "🔴 <b>STOKVIGIL SIGNAL: PROFIT BOOK / SELL WATCH</b> 🔴"
    elif "TRAILING" in bias_upper:
        header_badge = "🟡 <b>STOKVIGIL ALERT: TRAILING STOP-LOSS TRIGGER</b> 🟡"
    else:
        header_badge = "⚪ <b>STOKVIGIL UPDATE: MARKET WATCHTOWER</b> ⚪"

    is_bse = str(symbol).strip().upper().endswith(".BO")
    clean_sym = symbol.replace(".NS", "").replace(".BO", "").strip().upper()
    exch_label = "BSE" if is_bse else "NSE"

    html = f"{header_badge}\n"
    html += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    html += f"📈 <b>Ticker:</b> #{clean_sym} ({exch_label})\n"
    html += f"🎯 <b>Confluence Score:</b> <b>{confluence_score}/100</b>\n"
    html += f"⚡ <b>Catalyst:</b> {catalyst_type.replace('_', ' ')}\n\n"
    html += f"📌 <b>{alert_title}</b>\n\n"

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
            html += f"• <i>Guidance: {holding_guidance}</i>\n"
        html += "\n"

    # Factual Confluence Drivers
    if confluence_drivers:
        html += "🔍 <b>Multi-Factor Drivers:</b>\n"
        for driver in confluence_drivers[:4]:
            html += f"• {driver}\n"
        html += "\n"

    # Tactical Levels (Entry, Target, Stop-Loss, R:R)
    if tactical_levels:
        entry = tactical_levels.get("entry_range", "N/A")
        t1 = tactical_levels.get("target_1", "N/A")
        t2 = tactical_levels.get("target_2", "N/A")
        sl = tactical_levels.get("protective_stop_loss", "N/A")
        rr = tactical_levels.get("risk_reward_ratio", "N/A")
        
        html += "📐 <b>Tactical Risk-Reward Levels:</b>\n"
        html += f"• <b>Entry Range:</b> {entry}\n"
        html += f"• <b>Target 1 (1.5x ATR):</b> {t1}\n"
        html += f"• <b>Target 2 (Swing High):</b> {t2}\n"
        html += f"• <b>Stop-Loss:</b> {sl} (R:R: {rr})\n\n"

    # Technical Metrics Snapshot
    if metrics_snapshot:
        html += "📊 <b>Market Snapshot:</b>\n"
        if "current_price" in metrics_snapshot or "price" in metrics_snapshot:
            p = metrics_snapshot.get("current_price") or metrics_snapshot.get("price")
            html += f"• LTP: ₹{p}\n"
        if "rsi_15m" in metrics_snapshot:
            html += f"• 15m RSI: {metrics_snapshot['rsi_15m']} | 5m RSI: {metrics_snapshot.get('rsi_5m', 'N/A')}\n"
        if "vwap" in metrics_snapshot and metrics_snapshot['vwap'] > 0:
            html += f"• VWAP: ₹{metrics_snapshot['vwap']}\n"
        if "delivery_pct" in metrics_snapshot:
            html += f"• Delivery: {metrics_snapshot['delivery_pct']}%\n"
        if "vsa_regime" in metrics_snapshot and metrics_snapshot.get("vsa_regime"):
            html += f"• Wyckoff VSA: <b>{metrics_snapshot['vsa_regime'].replace('_', ' ')}</b>\n"

    html += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    html += "<i>⚠️ Factual quantitative intelligence alert. Non-advisory analytical tracking.</i>"
    return html

def build_telegram_inline_keyboard(symbol: str) -> dict:
    """
    Builds interactive institutional inline buttons for Telegram alert:
    1. Direct live TradingView interactive technical chart (NSE or BSE)
    2. Deep link to ICICI Direct Portfolio / Order execution
    3. Official NSE / BSE India quote & corporate actions
    """
    is_bse = str(symbol).strip().upper().endswith(".BO")
    clean_sym = symbol.replace(".NS", "").replace(".BO", "").strip().upper()
    chart_exchange = "BSE" if is_bse else "NSE"
    exchange_name = "BSE India Live" if is_bse else "NSE India Live"
    exchange_url = (
        f"https://www.bseindia.com/stock-share-price/{clean_sym}/"
        if is_bse else
        f"https://www.nseindia.com/get-quotes/equity?symbol={clean_sym}"
    )
    return {
        "inline_keyboard": [
            [
                {"text": "📈 TradingView Chart", "url": f"https://in.tradingview.com/chart/?symbol={chart_exchange}:{clean_sym}"},
                {"text": "💼 ICICI Direct", "url": "https://secure.icicidirect.com"}
            ],
            [
                {"text": f"🏛️ {exchange_name}", "url": exchange_url}
            ]
        ]
    }
