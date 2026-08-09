import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "StokVigil AI"
    PACKAGE_ID: str = "com.app.stokvigil"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Supabase Settings
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://your-supabase-project.supabase.co")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "your-service-role-key")
    
    # Vault Encryption Key (Fernet AES-256 base64 key)
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3c=")
    
    # Gemini AI Agent Key
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Firebase Cloud Messaging
    FIREBASE_CREDENTIALS_JSON: str = os.getenv("FIREBASE_CREDENTIALS_JSON", "")
    
    # Telegram Bot Settings
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
