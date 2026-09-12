import os
import json
from typing import List, Union, Any, Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "StokVigil AI"
    PACKAGE_ID: str = "com.app.stokvigil"
    ENVIRONMENT: str = ""
    
    # Supabase Settings
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    DATABASE_URL: str = ""
    
    # Vault Encryption Key (Fernet AES-256 base64 key)
    ENCRYPTION_KEY: str = ""
    
    # Gemini AI Agent Key
    GEMINI_API_KEY: str = ""
    
    # Firebase Cloud Messaging
    FIREBASE_CREDENTIALS_JSON: str = ""
    
    # Telegram Bot Settings
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""
    
    # Cron Security Token (Supports both CRON_SECRET_KEY and CRON_SECRET)
    CRON_SECRET_KEY: str = ""
    CRON_SECRET: Optional[str] = None

    # Admin Security Token
    ADMIN_SECRET_KEY: Optional[str] = None

    @property
    def active_cron_secret(self) -> str:
        secret = self.CRON_SECRET if (self.CRON_SECRET and self.CRON_SECRET.strip()) else self.CRON_SECRET_KEY
        return str(secret or "").strip().strip('"').strip("'")
    
    # Raw ALLOWED_ORIGINS string or list from env (str first to prevent EnvSettingsSource JSON decode error)
    ALLOWED_ORIGINS: Union[str, List[str]] = ""

    @property
    def allowed_origins_list(self) -> List[str]:
        val = self.ALLOWED_ORIGINS
        if isinstance(val, list):
            return [str(x).strip().strip('"').strip("'") for x in val if str(x).strip()]
        if isinstance(val, str) and val.strip():
            # Check if it's a JSON array string
            if val.strip().startswith("[") and val.strip().endswith("]"):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, list):
                        return [str(x).strip().strip('"').strip("'") for x in parsed if str(x).strip()]
                except Exception:
                    pass
            # Comma-separated string or single URL
            return [x.strip().strip('"').strip("'") for x in val.split(",") if x.strip()]
        if self.ENVIRONMENT == "production":
            return []
        return ["*"]

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
