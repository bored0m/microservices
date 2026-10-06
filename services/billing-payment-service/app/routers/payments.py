import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import CurrentUser, get_current_user, verify_webhook_secret
from ..clients.notification_client import send_payment_success
from ..database import get_db
from ..models import Invoice, InvoiceStatus, Payment, PaymentStatus, PaymentWebhookEvent
from ..schemas import PaymentCreate, PaymentOut, WebhookAck, WebhookSuccessIn

log = logging.getLogger("billing.payments")
router = APIRouter(tags=["payments"])


@router.post("/payments", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(
    data: PaymentCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Инициирование оплаты счёта целиком.

    Платёж создаётся в статусе `processing` с идентификатором транзакции у провайдера
    (`provider_ref`); итог приходит вебхуком POST /payments/webhook/success.
    Реальный провайдер здесь имитируется.
    """
    # Блокируем счёт на время проверки, чтобы два параллельных запроса не создали два платежа.
    invoice = db.scalar(select(Invoice).where(Invoice.id == data.invoice_id).with_for_update())
    if invoice is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invoice not found")
    if invoice.account.user_id != user.id and not user.is_privileged:
        log.warning("Forbidden payment attempt: user=%s invoice=%s", user.id, invoice.id)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invoice belongs to another user")
    if invoice.status == InvoiceStatus.paid:
        raise HTTPException(status.HTTP_409_CONFLICT, "Invoice is already paid")
    if invoice.status == InvoiceStatus.cancelled:
        raise HTTPException(status.HTTP_409_CONFLICT, "Invoice is cancelled")

    in_progress = db.scalar(
        select(Payment.id)
        .where(
            Payment.invoice_id == invoice.id,
            Payment.status.in_([PaymentStatus.created, PaymentStatus.processing]),
        )
        .limit(1)
    )
    if in_progress:
        raise HTTPException(status.HTTP_409_CONFLICT, "Payment for this invoice is already in progress")

    payment = Payment(
        invoice_id=invoice.id,
        amount=invoice.amount,
        method=data.method,
        status=PaymentStatus.processing,
        provider_ref=f"sim_{uuid.uuid4().hex}",
    )
    db.add(payment)
    db.commit()
    log.info(
        "Payment created: payment=%s invoice=%s amount=%s method=%s provider_ref=%s by=%s",
        payment.id, invoice.id, payment.amount, payment.method.value, payment.provider_ref, user.id,
    )
    return payment


@router.get("/payments/{payment_id}", response_model=PaymentOut)
def get_payment(
    payment_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Статус платежа (для опроса клиентом после инициирования оплаты)."""
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")
    if payment.invoice.account.user_id != user.id and not user.is_privileged:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Payment belongs to another user")
    return payment


@router.post(
    "/payments/webhook/success",
    response_model=WebhookAck,
    dependencies=[Depends(verify_webhook_secret)],
)
def webhook_success(
    data: WebhookSuccessIn,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Коллбэк платёжного провайдера об успешной оплате. Идемпотентен."""
    # Блокировка строки платежа: параллельные дубли вебхука выстроятся в очередь
    # и увидят уже итоговый статус.
    payment = db.scalar(select(Payment).where(Payment.provider_ref == data.provider_ref).with_for_update())

    event = PaymentWebhookEvent(
        payment_id=payment.id if payment else None,
        event_type="payment.succeeded",
        raw_payload=data.model_dump(mode="json"),
    )
    db.add(event)

    def reject(code: int, detail: str):
        db.commit()  # сохраняем событие в журнале для аудита, состояние платежа не меняем
        log.warning("Webhook rejected (%s): %s provider_ref=%s", code, detail, data.provider_ref)
        raise HTTPException(code, detail)

    if payment is None:
        reject(status.HTTP_404_NOT_FOUND, "Payment not found")
    if payment.status == PaymentStatus.succeeded:
        event.processed = True
        db.commit()
        log.info("Webhook duplicate ignored: payment=%s", payment.id)
        return WebhookAck(status="already_processed", payment_id=payment.id)
    if payment.status == PaymentStatus.failed:
        reject(status.HTTP_409_CONFLICT, "Payment has already failed")
    if data.amount is not None and data.amount != payment.amount:
        reject(status.HTTP_409_CONFLICT, "Amount does not match the payment")

    invoice = db.scalar(select(Invoice).where(Invoice.id == payment.invoice_id).with_for_update())
    payment.status = PaymentStatus.succeeded
    payment.completed_at = datetime.now(timezone.utc)
    invoice.status = InvoiceStatus.paid
    event.processed = True
    user_id, amount = invoice.account.user_id, payment.amount
    db.commit()
    log.info("Payment succeeded: payment=%s invoice=%s amount=%s", payment.id, invoice.id, amount)

    # Уведомление — после коммита и вне транзакции; его сбой платёж не откатывает.
    background.add_task(send_payment_success, user_id, amount)
    return WebhookAck(status="processed", payment_id=payment.id)
