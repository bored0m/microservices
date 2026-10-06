import logging
import os
from typing import Any, Dict

import httpx

logger = logging.getLogger(__name__)

NOTIFICATION_SERVICE_URL = os.getenv(
    "NOTIFICATION_SERVICE_URL",
    "http://notification_service:8000",
)


def send_notification(
    user_id: str,
    channel: str,
    template_code: str,
    template_data: Dict[str, Any],
) -> None:
    payload = {
        "user_id": user_id,
        "source_service": "transport_service",
        "channel": channel,
        "template_code": template_code,
        "template_data": template_data,
    }

    try:
        response = httpx.post(
            f"{NOTIFICATION_SERVICE_URL}/notifications",
            json=payload,
            timeout=5.0,
        )
        response.raise_for_status()
        logger.info(
            "Notification sent: user=%s template=%s",
            user_id,
            template_code,
        )
    except Exception:
        logger.exception(
            "Notification request failed: user=%s template=%s",
            user_id,
            template_code,
        )
