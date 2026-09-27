from typing import Optional
from pydantic import BaseModel

class RegisterDeviceRequest(BaseModel):
    user_id: str
    fcm_device_token: Optional[str] = None
    fcm_enabled: Optional[bool] = None
    telegram_chat_id: Optional[str] = None
    telegram_enabled: Optional[bool] = None
    alert_sensitivity: Optional[str] = None  # 'HIGH', 'ALL', 'FII'
    execution_mode: Optional[str] = None  # 'INSTANT', 'CONFIRM'
    demat_auto_sync: Optional[bool] = None
    tnc_accepted: Optional[bool] = True

class SaveCredentialsRequest(BaseModel):
    user_id: str
    session_token: str
    broker: str = "icici"

class DeleteAccountRequest(BaseModel):
    user_id: str
