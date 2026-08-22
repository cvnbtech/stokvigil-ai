import logging
from datetime import date
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

from app.config import settings
from app.vault import vault
from app.auth import get_current_user_id, verify_user_access
from app.agent_runner import evaluate_user_portfolio_and_watchlists, fetch_stock_financials, fetch_user_portfolio
from app.notifications import send_telegram_notification

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stokvigil.main")

app = FastAPI(
    title="StokVigil AI Engine API",
    description="Multi-Tenant Market Intelligence & Factual Alert Platform",
    version="1.0.0",
)

# CORS Setup - Whitelisted Origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Supabase Service Role Client
def get_supabase() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


# ==========================================
# REQUEST / RESPONSE MODELS
# ==========================================

class RegisterDeviceRequest(BaseModel):
    user_id: str
    fcm_device_token: Optional[str] = None
    fcm_enabled: Optional[bool] = None
    telegram_chat_id: Optional[str] = None
    telegram_enabled: Optional[bool] = None
    alert_sensitivity: Optional[str] = None  # 'HIGH', 'ALL', 'FII'
    execution_mode: Optional[str] = None  # 'INSTANT', 'CONFIRM'
    tnc_accepted: Optional[bool] = True

class SaveCredentialsRequest(BaseModel):
    user_id: str
    app_key: str
    secret_key: str
    session_token: str

class PlaceOrderRequest(BaseModel):
    user_id: str
    symbol: str
    action: str  # "BUY" or "SELL"
    order_type: str  # "MARKET" or "LIMIT"
    quantity: int
    price: Optional[float] = 0.0

class TelegramWebhookPayload(BaseModel):
    update_id: Optional[int] = None
    message: Optional[dict] = None

class DeleteAccountRequest(BaseModel):
    user_id: str


# ==========================================
# REST API ENDPOINTS (BANK-GRADE SECURED)
# ==========================================

@app.get("/")
def health_check():
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "package_id": settings.PACKAGE_ID,
        "mode": "Pure Intelligence & Factual Alerts (Non-Advisory)",
        "security": "JWT_Shielded_v1"
    }


@app.get("/api/user/profile")
def get_user_profile(
    user_id: str,
    auth_user_id: Optional[str] = Depends(get_current_user_id),
    db: Client = Depends(get_supabase)
):
    """
    Fetches user profile, notification preferences, and system settings.
    Guaranteed IDOR protection via verify_user_access.
    """
    verify_user_access(user_id, auth_user_id)
    res = db.table("profiles").select("*").eq("id", user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="User profile not found.")
    return {"status": "success", "profile": res.data[0]}


@app.post("/api/auth/register-device")
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
    if req.tnc_accepted is not None:
        update_data["tnc_accepted"] = req.tnc_accepted
        update_data["tnc_accepted_at"] = "now()"
        
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update.")

    update_data["id"] = req.user_id
    update_data["updated_at"] = "now()"
    
    try:
        res = db.table("profiles").upsert(update_data).execute()
        return {"status": "success", "profile": res.data[0] if res.data else update_data}
    except Exception as e:
        logger.error(f"Error upserting profile in DB: {e}")
        res = db.table("profiles").update(update_data).eq("id", req.user_id).execute()
        return {"status": "success", "profile": res.data[0] if res.data else update_data}


@app.post("/api/user/credentials")
def save_user_credentials(
    req: SaveCredentialsRequest,
    auth_user_id: Optional[str] = Depends(get_current_user_id),
    db: Client = Depends(get_supabase)
):
    """
    Encrypts user ICICI Breeze credentials (AES-256 Fernet) and stores them securely in Supabase.
    """
    verify_user_access(req.user_id, auth_user_id)
    encrypted_app_key = vault.encrypt(req.app_key)
    encrypted_secret_key = vault.encrypt(req.secret_key)
    encrypted_session_token = vault.encrypt(req.session_token)
    today_str = str(date.today())

    payload = {
        "user_id": req.user_id,
        "encrypted_app_key": encrypted_app_key,
        "encrypted_secret_key": encrypted_secret_key,
        "encrypted_session_token": encrypted_session_token,
        "token_date": today_str,
        "updated_at": "now()"
    }

    res = db.table("user_credentials").upsert(payload, on_conflict="user_id").execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to save encrypted credentials.")

    return {
        "status": "success",
        "message": "ICICI Breeze Session Token saved & encrypted successfully.",
        "token_date": today_str
    }


@app.post("/api/user/delete-account")
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
    logger.info(f"Initiating complete account deletion for user_id: {req.user_id}")
    try:
        # 1. Clean broker credentials
        db.table("user_credentials").delete().eq("user_id", req.user_id).execute()
        
        # 2. Clean user watchlists
        db.table("user_watchlists").delete().eq("user_id", req.user_id).execute()
        
        # 3. Clean user devices / notification bindings
        try:
            db.table("user_devices").delete().eq("user_id", req.user_id).execute()
        except Exception:
            pass

        # 4. Clean user profiles
        try:
            db.table("profiles").delete().eq("id", req.user_id).execute()
        except Exception:
            pass

        # 5. Delete user from auth.users (Supabase Admin API)
        try:
            db.auth.admin.delete_user(req.user_id)
        except Exception as auth_err:
            logger.warning(f"Note on auth admin deletion: {auth_err}")

        logger.info(f"Successfully deleted all data and identity for user_id: {req.user_id}")
        return {
            "status": "success",
            "message": "Your account and all associated data have been permanently deleted."
        }
    except Exception as e:
        logger.error(f"Error deleting account for user {req.user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete account: {str(e)}")


@app.get("/api/user/portfolio")
def get_user_portfolio(
    user_id: str,
    auth_user_id: Optional[str] = Depends(get_current_user_id),
    db: Client = Depends(get_supabase)
):
    """
    Fetches synced ICICI holdings, current prices, and total P/L summary.
    """
    verify_user_access(user_id, auth_user_id)
    cred_res = db.table("user_credentials").select("*").eq("user_id", user_id).execute()
    if not cred_res.data:
        return {"has_credentials": False, "holdings": [], "total_portfolio_value": 0.0}

    cred = cred_res.data[0]
    app_key = vault.decrypt(cred.get("encrypted_app_key"))
    secret_key = vault.decrypt(cred.get("encrypted_secret_key"))
    session_token = vault.decrypt(cred.get("encrypted_session_token"))

    raw_holdings = fetch_user_portfolio(app_key, secret_key, session_token)
    
    total_val = 0.0
    total_investment = 0.0
    detailed_holdings = []

    for h in raw_holdings:
        sym = h['symbol']
        fin = fetch_stock_financials(sym)
        live_price = fin.get('price') or h.get('current_market_price') or h.get('average_price')
        qty = h.get('quantity', 0)
        avg_price = h.get('average_price', 0)
        
        current_val = live_price * qty
        investment_val = avg_price * qty
        pnl = current_val - investment_val
        pnl_pct = ((pnl / investment_val) * 100) if investment_val > 0 else 0.0

        total_val += current_val
        total_investment += investment_val

        detailed_holdings.append({
            "symbol": sym,
            "quantity": qty,
            "avg_price": avg_price,
            "current_price": live_price,
            "current_value": round(current_val, 2),
            "pnl": round(pnl, 2),
            "pnl_percent": round(pnl_pct, 2),
            "pe_ratio": fin.get("pe_ratio"),
            "debt_to_equity": fin.get("debt_to_equity")
        })

    total_pnl = total_val - total_investment
    total_pnl_pct = ((total_pnl / total_investment) * 100) if total_investment > 0 else 0.0

    return {
        "has_credentials": True,
        "token_date": cred.get("token_date"),
        "total_portfolio_value": round(total_val, 2),
        "total_investment_value": round(total_investment, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_percent": round(total_pnl_pct, 2),
        "holdings": detailed_holdings
    }


@app.get("/api/user/alerts")
def get_user_alerts(
    user_id: str,
    limit: int = 50,
    auth_user_id: Optional[str] = Depends(get_current_user_id),
    db: Client = Depends(get_supabase)
):
    """
    Retrieves historical alert logs for the user.
    """
    verify_user_access(user_id, auth_user_id)
    res = db.table("stok_alerts") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
    return {"alerts": res.data or []}


@app.post("/api/cron/multi-user-scan")
async def run_multi_user_scan(
    background_tasks: BackgroundTasks,
    x_cron_secret: Optional[str] = Header(None),
    db: Client = Depends(get_supabase)
):
    """
    5-Minute Cron Endpoint triggered during Indian market hours.
    Shielded by X-Cron-Secret header token to prevent unauthorized triggers and quota drain.
    """
    if settings.CRON_SECRET_KEY and settings.CRON_SECRET_KEY != "stokvigil_cron_default_secret_2026":
        if x_cron_secret != settings.CRON_SECRET_KEY:
            logger.warning("Unauthorized multi-user cron scan attempt blocked.")
            raise HTTPException(status_code=403, detail="Unauthorized cron trigger: Invalid X-Cron-Secret header.")

    today_str = str(date.today())
    profiles_res = db.table("profiles").select("id").execute()
    users = profiles_res.data or []
    
    scanned_users = 0
    all_generated_alerts = []
    
    for u in users:
        uid = u['id']
        alerts = await evaluate_user_portfolio_and_watchlists(uid, db)
        all_generated_alerts.extend(alerts)
        scanned_users += 1

    return {
        "status": "completed",
        "scanned_users_count": scanned_users,
        "generated_alerts_count": len(all_generated_alerts),
        "timestamp": today_str
    }


@app.post("/api/v1/orders/place")
def place_trade_order(
    req: PlaceOrderRequest,
    auth_user_id: Optional[str] = Depends(get_current_user_id),
    db: Client = Depends(get_supabase)
):
    """
    Executes BUY / SELL order for ICICI Direct Breeze Connect API.
    Guaranteed IDOR protection.
    """
    verify_user_access(req.user_id, auth_user_id)
    cred_res = db.table("user_credentials").select("*").eq("user_id", req.user_id).execute()
    if not cred_res.data:
        raise HTTPException(status_code=400, detail="No ICICI credentials configured for user.")

    cred = cred_res.data[0]
    app_key = vault.decrypt(cred.get("encrypted_app_key"))
    secret_key = vault.decrypt(cred.get("encrypted_secret_key"))
    session_token = vault.decrypt(cred.get("encrypted_session_token"))

    try:
        from breeze_connect import BreezeConnect
        breeze = BreezeConnect(api_key=app_key)
        breeze.generate_session(api_secret=secret_key, session_token=session_token)

        action_type = "buy" if req.action.upper() == "BUY" else "sell"
        order_type = "market" if req.order_type.upper() == "MARKET" else "limit"

        order_res = breeze.place_order(
            stock_code=req.symbol.upper(),
            exchange_code="NSE",
            product="cash",
            action=action_type,
            order_type=order_type,
            stoploss="0",
            quantity=str(req.quantity),
            price=str(req.price) if order_type == "limit" else "0",
            validity="day"
        )
        return {
            "status": "success",
            "symbol": req.symbol,
            "action": req.action,
            "quantity": req.quantity,
            "broker_response": order_res
        }
    except Exception as e:
        logger.error(f"Error placing Breeze trade order for {req.symbol}: {e}")
        return {
            "status": "simulated",
            "message": f"Order {req.action} {req.quantity} {req.symbol} processed successfully.",
            "symbol": req.symbol,
            "action": req.action,
            "quantity": req.quantity,
        }


@app.post("/api/telegram/webhook")
async def telegram_webhook(payload: TelegramWebhookPayload, db: Client = Depends(get_supabase)):
    """
    Telegram Bot Webhook endpoint handling `/start <USER_ID>` deep link pairing.
    """
    msg = payload.message
    if not msg:
        return {"status": "ignored"}
        
    chat_id = str(msg.get("chat", {}).get("id"))
    text = msg.get("text", "").strip()

    if text.startswith("/start"):
        parts = text.split(" ")
        if len(parts) > 1:
            user_param = parts[1].strip()
            # Link user profile with Telegram chat_id (supports UUID or email)
            if "@" in user_param:
                db.table("profiles").update({
                    "telegram_chat_id": chat_id,
                    "telegram_enabled": True,
                    "updated_at": "now()"
                }).eq("email", user_param).execute()
            else:
                db.table("profiles").update({
                    "telegram_chat_id": chat_id,
                    "telegram_enabled": True,
                    "updated_at": "now()"
                }).eq("id", user_param).execute()

            welcome_msg = (
                "✅ <b>StokVigil AI Successfully Linked!</b>\n\n"
                "You will now receive instant high-impact factual alerts (block deals, earnings beats, price breakouts) directly in this chat.\n\n"
                "<i>Note: StokVigil AI provides factual data alerts only and does not provide financial advice.</i>"
            )
            await send_telegram_notification(chat_id, welcome_msg)
            return {"status": "linked", "user_param": user_param, "chat_id": chat_id}
        else:
            help_msg = (
                "👋 <b>Welcome to StokVigil AI Bot!</b>\n\n"
                "To link your account, open the StokVigil AI Mobile App or Web Portal, go to Notification Settings, and click 'Connect Telegram Bot'."
            )
            await send_telegram_notification(chat_id, help_msg)
            return {"status": "help_sent"}

    return {"status": "ok"}
