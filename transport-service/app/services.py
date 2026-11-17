import logging
from typing import Any

import httpx

from .config import NOTIFICATION_SERVICE_URL

log = logging.getLogger("transport")


def send_notification(user_id: int, template_code: str, template_data: dict[str, Any]) -> None:
    """Fire-and-forget: сбой уведомления не должен ломать бронирование."""
    payload = {
        "user_id": user_id,
        "source_service": "transport",
        "channel": "in_app",
        "template_code": template_code,
        "template_data": template_data,
    }
    try:
        resp = httpx.post(f"{NOTIFICATION_SERVICE_URL}/notifications", json=payload, timeout=5)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        log.error("Notification failed: user=%s template=%s: %s", user_id, template_code, exc)
