import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Channel(str, Enum):
    email = "email"
    sms = "sms"
    push = "push"
    in_app = "in_app"


class NotificationCreate(BaseModel):
    """Либо `template_code` (+ `template_data`), либо готовые `message` (и `title`)."""

    user_id: int
    source_service: str = Field(min_length=1, max_length=64)
    channel: Channel = Channel.in_app
    template_code: str | None = None
    template_data: dict[str, Any] = Field(default_factory=dict)
    title: str | None = Field(default=None, max_length=255)
    message: str | None = None

    @model_validator(mode="after")
    def _template_or_message(self):
        if not self.template_code and not self.message:
            raise ValueError("Provide template_code or message")
        return self


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: int
    source_service: str
    channel: Channel
    title: str | None
    message: str
    status: str
    created_at: datetime
    sent_at: datetime | None


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    subject_template: str | None
    body_template: str
