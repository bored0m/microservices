import logging
import uuid
from decimal import Decimal

import httpx

from ..config import get_settings

log = logging.getLogger("billing.notification")


def send_payment_success(user_id: uuid.UUID, amount: Decimal) -> None:
    """POST /notifications (шаблон PAYMENT_SUCCESS).

    Сбой отправки не влияет на платёж: ошибка только логируется.
    Вызывается через BackgroundTasks уже после коммита транзакции.
    """
    s = get_settings()
    payload = {
        "user_id": str(user_id),
        "source_service": "billing_payment_service",
        "channel": "in_app",
        "template_code": "PAYMENT_SUCCESS",
        "template_data": {"amount": str(amount)},
    }
    try:
        resp = httpx.post(f"{s.notification_service_url}/notifications", json=payload, timeout=s.http_timeout)
        resp.raise_for_status()
        log.info("Notification sent: user=%s template=PAYMENT_SUCCESS", user_id)
    except Exception:
        log.exception("Notification failed (payment is unaffected): user=%s", user_id)
