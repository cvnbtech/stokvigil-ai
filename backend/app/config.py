import os
from typing import List, Union
from pydantic_settings import BaseSettings

def get_allowed_origins() -> List[str]:
    raw = os.getenv("ALLOWED_ORIGINS", "")
    if raw.strip():
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    
    env = os.getenv("ENVIRONMENT", "development").lower()
    if env == "production":
        return ["https://stokvigil-ai.vercel.app"]
    else:
        return [
            "https://stokvigil-ai.vercel.app",
            "http://localhost:3000",
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000"
        ]

class Settings(BaseSettings):
    APP_NAME: str = "StokVigil AI"
    PACKAGE_ID: str = "com.app.stokvigil"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Supabase Settings
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://your-supabase-project.supabase.co")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "your-service-role-key")
    
    # Vault Encryption Key (Fernet AES-256 base64 key)
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3c=")
    
    # Gemini AI Agent Key
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Firebase Cloud Messaging
    FIREBASE_CREDENTIALS_JSON: str = os.getenv("FIREBASE_CREDENTIALS_JSON", "")
    
    # Telegram Bot Settings
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # Cron Security Token
    CRON_SECRET_KEY: str = os.getenv("CRON_SECRET_KEY", "stokvigil_cron_default_secret_2026")
    
    # CORS Allowed Origins (Loaded dynamically from ALLOWED_ORIGINS in .env)
    ALLOWED_ORIGINS: List[str] = get_allowed_origins()

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
