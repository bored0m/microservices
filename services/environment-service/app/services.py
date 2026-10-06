import logging
import os
from decimal import Decimal
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

NOTIFICATION_SERVICE_URL = os.getenv(
    "NOTIFICATION_SERVICE_URL",
    "http://notification_service:8000",
)
NOTIFICATION_USER_ID = os.getenv("NOTIFICATION_USER_ID")


def send_notification(
    template_code: str,
    template_data: Dict[str, Any],
    user_id: Optional[str] = None,
) -> None:
    recipient = user_id or NOTIFICATION_USER_ID
    if not recipient:
        logger.warning(
            "Sensor alert skipped: NOTIFICATION_USER_ID is not configured"
        )
        return

    payload = {
        "user_id": recipient,
        "source_service": "environment_service",
        "channel": "in_app",
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
            "Environment notification sent: user=%s template=%s",
            recipient,
            template_code,
        )
    except Exception:
        logger.exception(
            "Environment notification request failed: user=%s template=%s",
            recipient,
        )


def check_threshold(sensor_type: str, value: Decimal) -> Optional[str]:
    thresholds = {
        "air_quality": Decimal("100"),
        "noise": Decimal("85"),
        "temperature": Decimal("50"),
    }

    limit = thresholds.get(sensor_type)
    if limit is not None and value > limit:
        return f"Превышен порог {sensor_type}: {value} > {limit}"
    return None
