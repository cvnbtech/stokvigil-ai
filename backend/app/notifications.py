import json
import logging
import httpx
from typing import Optional
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
    Sends Lock-Screen FCM Push Alert to Android/iOS devices.
    Factual & Non-Advisory payload only.
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

async def send_telegram_notification(chat_id: str, formatted_markdown_text: str) -> bool:
    """
    Sends styled Markdown Telegram market intelligence alert straight to Telegram chat.
    Uses Telegram Bot HTTP API.
    """
    if not chat_id:
        logger.warning("No Telegram Chat ID provided, skipping Telegram alert.")
        return False
        
    bot_token = settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        logger.info(f"[DRY RUN - Telegram Alert to Chat {chat_id}] Message:\n{formatted_markdown_text}")
        return True
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": formatted_markdown_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
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

def format_telegram_alert(symbol: str, alert_title: str, catalyst_type: str, impact_score: int, factual_reasons: list, metrics_snapshot: dict) -> str:
    """
    Formats factual market alert as clean HTML for Telegram Bot API.
    """
    badge_emoji = "🔴" if impact_score >= 80 else ("🟡" if impact_score >= 60 else "🟢")
    
    html = f"⚡ <b>StokVigil AI Market Alert</b> ⚡\n\n"
    html += f"<b>Ticker:</b> #{symbol}\n"
    html += f"<b>Catalyst:</b> {catalyst_type.replace('_', ' ')}\n"
    html += f"<b>Impact Score:</b> {badge_emoji} {impact_score}/100\n\n"
    html += f"📌 <b>{alert_title}</b>\n\n"
    
    html += "🔍 <b>Factual Drivers:</b>\n"
    for reason in factual_reasons:
        html += f"• {reason}\n"
        
    html += "\n📊 <b>Key Financial Snapshot:</b>\n"
    if "price" in metrics_snapshot:
        html += f"• Live Price: ₹{metrics_snapshot['price']}\n"
    if "pe_ratio" in metrics_snapshot and metrics_snapshot['pe_ratio']:
        html += f"• Trailing P/E: {metrics_snapshot['pe_ratio']}\n"
    if "debt_to_equity" in metrics_snapshot and metrics_snapshot['debt_to_equity']:
        html += f"• Debt-to-Equity: {metrics_snapshot['debt_to_equity']}\n"
    if "revenue_growth" in metrics_snapshot and metrics_snapshot['revenue_growth']:
        html += f"• Revenue Growth (YoY): {metrics_snapshot['revenue_growth']}%\n"

    html += "\n<i>⚠️ Note: StokVigil AI provides factual data alerts only and does not provide financial advice.</i>"
    return html
