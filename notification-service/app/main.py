import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import CORS_ORIGINS
from .database import Base, SessionLocal, engine, get_db
from .deps import CurrentUser, get_current_user
from .models import Notification, NotificationTemplate
from .schemas import NotificationCreate, NotificationOut, TemplateOut
from .services import DEFAULT_TEMPLATES, render_template, send_via_provider

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("notification")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        existing = set(db.scalars(select(NotificationTemplate.code)))
        for code, subject, body in DEFAULT_TEMPLATES:
            if code not in existing:
                db.add(NotificationTemplate(code=code, subject_template=subject, body_template=body))
        db.commit()
    log.info("Notification service started, tables and templates ready")
    yield


app = FastAPI(
    title="Notification Service",
    description=(
        "Централизованная отправка уведомлений. `POST /notifications` вызывают другие сервисы "
        "(внутренний вызов, без токена); `GET /notifications` — пользователь читает свои уведомления."
    ),
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"]
)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


@app.post(
    "/notifications", response_model=NotificationOut, status_code=status.HTTP_201_CREATED, tags=["notifications"]
)
def send_notification(data: NotificationCreate, db: Session = Depends(get_db)):
    title, message = data.title, data.message
    if data.template_code:
        tpl = db.scalar(select(NotificationTemplate).where(NotificationTemplate.code == data.template_code))
        if tpl is None:
            log.error("Template %s not found", data.template_code)
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")
        title = render_template(tpl.subject_template, data.template_data)
        message = render_template(tpl.body_template, data.template_data)

    notification = Notification(
        user_id=data.user_id,
        source_service=data.source_service,
        channel=data.channel.value,
        title=title,
        message=message,
        status="queued",
    )
    db.add(notification)
    db.commit()

    try:
        send_via_provider(notification.channel, notification.user_id, title or "", message)
        notification.status = "sent"
        notification.sent_at = datetime.now(timezone.utc)
    except Exception:
        log.exception("Sending failed for notification %s", notification.id)
        notification.status = "failed"
    db.commit()
    db.refresh(notification)
    return notification


@app.get("/notifications", response_model=list[NotificationOut], tags=["notifications"])
def list_notifications(
    user_id: int | None = Query(None, description="Только для admin: уведомления другого пользователя"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Житель видит свои уведомления, администратор может указать `user_id`."""
    target = user.id
    if user_id is not None and user_id != user.id:
        if not user.is_admin:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin role required")
        target = user_id
    stmt = (
        select(Notification)
        .where(Notification.user_id == target)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    return db.scalars(stmt).all()


@app.get("/templates", response_model=list[TemplateOut], tags=["notifications"])
def list_templates(db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user)):
    return db.scalars(select(NotificationTemplate).order_by(NotificationTemplate.code)).all()
