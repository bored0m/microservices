from datetime import datetime, timezone
from sqlalchemy.orm import Session
from . import models, schemas


def get_template_by_code(db: Session, code: str):
    return (
        db.query(models.NotificationTemplate)
        .filter(models.NotificationTemplate.code == code)
        .first()
    )


def create_notification(
    db: Session,
    payload: schemas.NotificationCreate,
    title: str,
    message: str,
):
    notification = models.Notification(
        user_id=payload.user_id,
        source_service=payload.source_service,
        channel=payload.channel,
        title=title,
        message=message,
        status="queued",
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def mark_as_sent(db: Session, notification_id):
    notification = (
        db.query(models.Notification)
        .filter(models.Notification.id == notification_id)
        .first()
    )
    if notification:
        notification.status = "sent"
        notification.sent_at = datetime.now(timezone.utc)
        db.commit()


def mark_as_failed(db: Session, notification_id):
    notification = (
        db.query(models.Notification)
        .filter(models.Notification.id == notification_id)
        .first()
    )
    if notification:
        notification.status = "failed"
        db.commit()