import logging
from fastapi import FastAPI, HTTPException, Depends, status
from sqlalchemy.orm import Session

from . import schemas, crud, database, services

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("notification_service")

app = FastAPI(
    title="Notification Service",
    description="Централизованная отправка уведомлений (Умный город)",
    version="1.0.0",
)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


@app.post(
    "/notifications",
    response_model=schemas.NotificationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["notifications"],
)
def send_notification(
    payload: schemas.NotificationCreate,
    db: Session = Depends(database.get_db),
):
    logger.info(
        "Received request: user=%s source=%s channel=%s template=%s",
        payload.user_id, payload.source_service,
        payload.channel, payload.template_code,
    )

    template = crud.get_template_by_code(db, payload.template_code)
    if not template:
        logger.error("Template %s not found", payload.template_code)
        raise HTTPException(status_code=404, detail="Template not found")

    try:
        title = services.render_template(template.subject_template, payload.template_data)
        message = services.render_template(template.body_template, payload.template_data)
    except Exception as exc:
        logger.exception("Template rendering failed")
        raise HTTPException(status_code=400, detail=f"Rendering failed: {exc}")

    notification = crud.create_notification(db, payload, title, message)

    try:
        services.send_via_provider(
            payload.channel, str(payload.user_id), title, message
        )
        crud.mark_as_sent(db, notification.id)
    except Exception:
        logger.exception("Sending failed for notification %s", notification.id)
        crud.mark_as_failed(db, notification.id)

    return {
        "id": notification.id,
        "status": "queued",
        "message": "Notification processed",
    }