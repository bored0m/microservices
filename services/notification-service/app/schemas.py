from pydantic import BaseModel, UUID4
from typing import Dict, Any, Optional


class NotificationCreate(BaseModel):
    user_id: UUID4
    source_service: str
    channel: str  # email | sms | push | in_app
    template_code: str
    template_data: Optional[Dict[str, Any]] = {}


class NotificationResponse(BaseModel):
    id: UUID4
    status: str
    message: str