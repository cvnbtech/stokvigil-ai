import hmac
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from fastapi import HTTPException
from supabase import create_client, Client
from app.config import settings

logger = logging.getLogger("stokvigil.dependencies")

# Supabase Service Role Singleton Client (High-Performance HTTP Keep-Alive Connection Pool)
_supabase_client: Optional[Client] = None

def get_supabase() -> Client:
    """Returns the singleton Supabase client with service-role privileges."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    return _supabase_client


def verify_cron_secret(x_cron_secret: Optional[str]) -> None:
    """
    Validates X-Cron-Secret header using constant-time comparison (hmac.compare_digest).
    In production mode, enforces that CRON_SECRET_KEY is configured and not the public placeholder.
    """
    expected = settings.active_cron_secret
    if settings.ENVIRONMENT == "production":
        if not expected or expected == "stokvigil_cron_default_secret_2026":
            logger.critical("FATAL: CRON_SECRET_KEY is unconfigured or using default placeholder in production.")
            raise HTTPException(
                status_code=503,
                detail="Cron service is unconfigured in production mode."
            )
    incoming = (x_cron_secret or "").strip().strip('"').strip("'")
    if not incoming or not expected or not hmac.compare_digest(incoming, expected):
        logger.warning("Unauthorized cron trigger attempt blocked.")
        raise HTTPException(
            status_code=403,
            detail="Unauthorized cron trigger: Invalid or missing X-Cron-Secret header."
        )


def get_market_session_status() -> Tuple[bool, str]:
    """
    Checks if current time is within standard Indian market hours (09:15 to 15:30 IST, Monday-Friday).
    Returns (is_open: bool, message: str).
    """
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist_tz)
    # Weekday: 0 = Mon, 4 = Fri, 5 = Sat, 6 = Sun
    if now_ist.weekday() >= 5:
        return False, "Market is closed today (Weekend). Regular trading hours are Mon-Fri, 09:15 AM - 03:30 PM IST."
    
    market_open = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
    
    if now_ist < market_open:
        return False, f"Market is pre-open. Regular market trading opens at 09:15 AM IST (Current IST: {now_ist.strftime('%H:%M:%S')})."
    if now_ist > market_close:
        return False, f"Market is closed. Regular market hours ended at 03:30 PM IST (Current IST: {now_ist.strftime('%H:%M:%S')})."
    
    return True, "Market is open."


def is_indian_market_open() -> bool:
    """
    Checks if Indian stock exchanges (NSE & BSE) are currently open for regular trading.
    Regular trading hours: Monday through Friday, 09:15 AM to 03:30 PM IST.
    """
    is_open, _ = get_market_session_status()
    return is_open
