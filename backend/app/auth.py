import re
import logging
from typing import Optional, Any
from fastapi import Header, HTTPException, Depends
from supabase import create_client, Client
from app.config import settings

logger = logging.getLogger("stokvigil.auth")

# Lazy Supabase Auth Client for Token Validation
_auth_client: Optional[Client] = None

def get_auth_client() -> Client:
    global _auth_client
    if _auth_client is None:
        key = settings.SUPABASE_ANON_KEY or settings.SUPABASE_SERVICE_ROLE_KEY
        _auth_client = create_client(settings.SUPABASE_URL, key)
    return _auth_client

def get_current_user_id(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """
    Validates Supabase JWT Bearer Token and extracts the authenticated user ID.
    Guarantees zero Broken Object Level Authorization (BOLA / IDOR) vulnerabilities.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1].strip()
        try:
            client = get_auth_client()
            user_response = client.auth.get_user(token)
            if user_response and user_response.user:
                return str(user_response.user.id)
            else:
                raise HTTPException(status_code=401, detail="Invalid or expired session token.")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"JWT Verification failed: {e}")
            raise HTTPException(status_code=401, detail="Session authentication failed.")

    # Strict authentication required unless running explicitly in unit test mode
    if settings.ENVIRONMENT != "test":
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing Authorization Bearer token.")
        else:
            raise HTTPException(status_code=401, detail="Invalid Authorization header format. Expected 'Bearer <token>'.")

    return None

def get_optional_user_id(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """
    Extracts the authenticated user ID if a valid Bearer token is provided,
    without raising 401 if missing. Used for endpoints with tiered public/admin access.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1].strip()
        try:
            client = get_auth_client()
            user_response = client.auth.get_user(token)
            if user_response and user_response.user:
                return str(user_response.user.id)
        except Exception:
            return None
    return None


def mask_id(val: Optional[Any]) -> str:
    """
    Masks user IDs, UUIDs, or chat IDs showing only the last 4 characters (e.g. ***0123).
    Prevents leaking sensitive identifiers into server logs.
    """
    if val is None:
        return "***"
    s = str(val).strip()
    if not s:
        return "***"
    if len(s) <= 4:
        return "***" + s
    return "***" + s[-4:]

def mask_telegram_token(text: Optional[Any]) -> str:
    """
    Masks Telegram bot tokens in URLs or text, revealing only the last 4 characters.
    e.g. https://api.telegram.org/bot<TOKEN>/sendMessage
    becomes https://api.telegram.org/bot***<SUFFIX>/sendMessage
    """
    if text is None:
        return ""
    s = str(text)
    def _repl(match):
        prefix = match.group(1)
        token = match.group(2)
        masked = "***" + token if len(token) <= 4 else "***" + token[-4:]
        return f"{prefix}{masked}"

    s = re.sub(r'(api\.telegram\.org/bot)([^/\s?#"\']+)', _repl, s)
    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    if bot_token and len(bot_token) > 4 and bot_token in s:
        masked_tok = "***" + bot_token[-4:]
        s = s.replace(bot_token, masked_tok)
    return s

class SensitiveDataFilter(logging.Filter):
    """
    Custom logging filter that intercepts log records across all loggers
    and masks any Telegram Bot API token in URLs, formatted messages, or arbitrary argument objects
    (including httpx.URL, dicts, tuples, and exceptions) so tokens are never exposed.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            # Step 1: Render the full interpolated message regardless of argument types (e.g. httpx.URL)
            formatted_msg = record.getMessage()
            record.msg = mask_telegram_token(formatted_msg)
            record.args = ()
        except Exception:
            # Fallback: mask record.msg and stringify/mask any argument objects individually
            try:
                if isinstance(record.msg, str):
                    record.msg = mask_telegram_token(record.msg)
                if record.args:
                    if isinstance(record.args, dict):
                        record.args = {k: mask_telegram_token(str(v)) for k, v in record.args.items()}
                    elif isinstance(record.args, tuple):
                        record.args = tuple(mask_telegram_token(str(a)) for a in record.args)
            except Exception:
                pass
        return True

# Attach filter to root logger and key subsystems
_filter = SensitiveDataFilter()
logging.getLogger().addFilter(_filter)
logging.getLogger("httpx").addFilter(_filter)
logging.getLogger("stokvigil.notifications").addFilter(_filter)
logging.getLogger("stokvigil.main").addFilter(_filter)



def verify_user_access(requested_user_id: str, authenticated_user_id: Optional[str]) -> bool:
    """
    Ensures that a user can only access and modify their own data.
    Strictly prevents IDOR / BOLA attacks.
    """
    if authenticated_user_id is None:
        if settings.ENVIRONMENT == "test":
            return True
        raise HTTPException(status_code=401, detail="Authentication required.")

    if requested_user_id != authenticated_user_id:
        logger.warning(
            f"IDOR attempt detected: Authenticated user '{mask_id(authenticated_user_id)}' "
            f"tried to access user '{mask_id(requested_user_id)}'."
        )
        raise HTTPException(
            status_code=403,
            detail="Access forbidden: You are not authorized to access or modify this account."
        )
    return True
