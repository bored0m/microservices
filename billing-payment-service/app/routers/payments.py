import hmac
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import ADMIN_ROLES, CurrentUser, get_current_user
from app.clients.notification_client import notify_user
from app.config import settings
from app.database import get_db

logger = logging.getLogger(settings.service_name)
router = APIRouter(tags=["payments"])


async def _complete_payment(db: Session, payment: models.Payment) -> models.Invoice:
    """Помечает платёж успешным, счёт — оплаченным и уведомляет пользователя."""
    payment.status = models.PaymentStatus.succeeded
    payment.completed_at = datetime.now(timezone.utc)
    invoice = db.get(models.Invoice, payment.invoice_id)
    invoice.status = models.InvoiceStatus.paid
    db.commit()
    db.refresh(payment)
    logger.info("Платёж %s успешен, счёт %s оплачен", payment.id, invoice.id)

    account = db.get(models.Account, invoice.account_id)
    await notify_user(
        user_id=account.user_id,
        title="Платёж успешно выполнен",
        message=f"Платёж на сумму {payment.amount} {invoice.currency} по счёту {invoice.id} выполнен.",
    )
    return invoice


@router.post("/payments", response_model=schemas.PaymentOut, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payload: schemas.PaymentCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Инициирует платёж по счёту. Платёж создаётся в статусе 'processing' и
    переводится в 'succeeded' вебхуком провайдера. При
    BILLING_SIMULATE_PAYMENT_SUCCESS=true подтверждение происходит сразу
    (учебный режим без внешнего эквайринга).
    """
    invoice = db.get(models.Invoice, payload.invoice_id)
    if invoice is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Счёт не найден")

    account = db.get(models.Account, invoice.account_id)
    if current_user.role not in ADMIN_ROLES and account.user_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Нельзя оплатить чужой счёт")
    if invoice.status == models.InvoiceStatus.paid:
        raise HTTPException(status.HTTP_409_CONFLICT, "Счёт уже оплачен")
    if invoice.status == models.InvoiceStatus.cancelled:
        raise HTTPException(status.HTTP_409_CONFLICT, "Счёт отменён, оплата невозможна")

    payment = models.Payment(
        invoice_id=invoice.id,
        amount=invoice.amount,
        method=payload.method,
        status=models.PaymentStatus.processing,
        provider_ref=f"sim_{uuid.uuid4().hex[:16]}",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    logger.info(
        "Создан платёж %s (provider_ref=%s) на %s по счёту %s, метод=%s",
        payment.id, payment.provider_ref, payment.amount, invoice.id, payload.method.value,
    )

    if settings.simulate_payment_success:
        await _complete_payment(db, payment)
    return payment


@router.post("/payments/webhook/success", status_code=status.HTTP_200_OK)
async def payment_webhook_success(
    request: Request,
    payload: schemas.PaymentWebhookPayload,
    db: Session = Depends(get_db),
    x_webhook_secret: str | None = Header(default=None),
):
    """Коллбэк платёжного провайдера. Авторизация — общий секрет, не JWT."""
    if not x_webhook_secret or not hmac.compare_digest(x_webhook_secret, settings.payment_webhook_secret):
        logger.warning("Вебхук с невалидным секретом от %s", request.client.host if request.client else "unknown")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Невалидный секрет вебхука")

    payment = db.query(models.Payment).filter(models.Payment.provider_ref == payload.provider_ref).first()
    event = models.PaymentWebhookEvent(
        payment_id=payment.id if payment else None,
        event_type="payment.success",
        raw_payload=payload.model_dump(mode="json"),
    )
    db.add(event)

    if payment is None:
        db.commit()
        logger.error("Вебхук с неизвестным provider_ref=%s", payload.provider_ref)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Платёж с данным provider_ref не найден")

    if payment.status == models.PaymentStatus.succeeded:  # идемпотентность
        event.processed = True
        db.commit()
        return {"status": "already_processed", "payment_id": str(payment.id)}

    event.processed = True
    await _complete_payment(db, payment)
    return {"status": "ok", "payment_id": str(payment.id)}
