import logging
from decimal import Decimal

import httpx

from .config import AUTH_SERVICE_URL, NOTIFICATION_SERVICE_URL

log = logging.getLogger("environment")

THRESHOLDS = {
    "air_quality": Decimal("100"),
    "noise": Decimal("85"),
    "temperature": Decimal("50"),
}


DEFAULT_UNITS = {
    "air_quality": "µg/m³",
    "noise": "дБ",
    "temperature": "°C",
    "water_quality": "pH",
    "radiation": "µSv/h",
}


def threshold_for(sensor_type: str) -> Decimal | None:
    return THRESHOLDS.get(sensor_type)


def check_threshold(sensor_type: str, value: Decimal) -> str | None:
    limit = THRESHOLDS.get(sensor_type)
    if limit is not None and value > limit:
        return f"Превышен порог {sensor_type}: {value} > {limit}"
    return None


def notify_admins(token: str, fallback_user_id: int, template_code: str, template_data: dict) -> None:
    """Шлёт уведомление всем администраторам (список берётся в Auth Service).

    Если список получить не удалось — уведомление уходит тому, кто передал показание.
    Ошибки только логируются: приём показаний не должен зависеть от Notification Service.
    """
    recipients = [fallback_user_id]
    try:
        resp = httpx.get(f"{AUTH_SERVICE_URL}/users", headers={"Authorization": f"Bearer {token}"}, timeout=5)
        resp.raise_for_status()
        admins = [u["id"] for u in resp.json() if u.get("role") == "admin"]
        recipients = admins or recipients
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        log.error("Could not load admins from auth service: %s", exc)

    for user_id in recipients:
        payload = {
            "user_id": user_id,
            "source_service": "environment",
            "channel": "in_app",
            "template_code": template_code,
            "template_data": template_data,
        }
        try:
            httpx.post(f"{NOTIFICATION_SERVICE_URL}/notifications", json=payload, timeout=5).raise_for_status()
        except httpx.HTTPError as exc:
            log.error("Notification failed: user=%s template=%s: %s", user_id, template_code, exc)
