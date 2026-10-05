import uuid
from sqlalchemy import Column, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, ENUM
from .database import Base


channel_enum = ENUM(
    'email', 'sms', 'push', 'in_app',
    name='notification_channel',
    create_type=False
)
status_enum = ENUM(
    'queued', 'sent', 'failed',
    name='notification_status',
    create_type=False
)


class NotificationTemplate(Base):
    __tablename__ = "notification_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(64), unique=True, nullable=False, index=True)
    subject_template = Column(String(255))
    body_template = Column(Text, nullable=False)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    source_service = Column(String(64), nullable=False)
    channel = Column(channel_enum, nullable=False)
    title = Column(String(255))
    message = Column(Text, nullable=False)
    status = Column(status_enum, nullable=False, default='queued')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)