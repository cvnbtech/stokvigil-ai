from typing import Optional, Dict, Any
from pydantic import BaseModel

class TelegramWebhookPayload(BaseModel):
    update_id: Optional[int] = None
    message: Optional[Dict[str, Any]] = None
