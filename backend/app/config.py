import os
from typing import List, Any
from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    APP_NAME: str = "StokVigil AI"
    PACKAGE_ID: str = "com.app.stokvigil"
    ENVIRONMENT: str = "development"
    
    # Supabase Settings
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    
    # Vault Encryption Key (Fernet AES-256 base64 key)
    ENCRYPTION_KEY: str = ""
    
    # Gemini AI Agent Key
    GEMINI_API_KEY: str = ""
    
    # Firebase Cloud Messaging
    FIREBASE_CREDENTIALS_JSON: str = ""
    
    # Telegram Bot Settings
    TELEGRAM_BOT_TOKEN: str = ""
    
    # Cron Security Token
    CRON_SECRET_KEY: str = ""
    
    # CORS Allowed Origins
    ALLOWED_ORIGINS: List[str] = [
        "https://stokvigil-ai.vercel.app",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000"
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Any) -> List[str]:
        if isinstance(v, list):
            return [str(x).strip().strip('"').strip("'") for x in v if str(x).strip()]
        if isinstance(v, str) and v.strip():
            # Support JSON array format
            if v.strip().startswith("[") and v.strip().endswith("]"):
                try:
                    import json
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(x).strip().strip('"').strip("'") for x in parsed if str(x).strip()]
                except Exception:
                    pass
            # Support comma-separated strings (e.g. "https://domain1.com, https://domain2.com")
            return [x.strip().strip('"').strip("'") for x in v.split(",") if x.strip()]
        return [
            "https://stokvigil-ai.vercel.app",
            "http://localhost:3000",
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000"
        ]

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
