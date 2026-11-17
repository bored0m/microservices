import logging

import httpx

from app.config import settings

logger = logging.getLogger(settings.service_name)


async def notify_user(user_id: int, title: str, message: str, channel: str = "in_app") -> None:
    """
    Отправляет уведомление через Notification Service.
    Намеренно "fire-and-forget с таймаутом" — сбой нотификации не должен
    откатывать уже совершённый платёж, поэтому ошибки только логируются.
    """
    url = f"{settings.notification_service_url}/notifications"
    payload = {
        "user_id": user_id,
        "source_service": settings.service_name,
        "channel": channel,
        "title": title,
        "message": message,
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            logger.info("Уведомление отправлено пользователю %s", user_id)
    except httpx.HTTPError as exc:
        logger.error("Не удалось отправить уведомление пользователю %s: %s", user_id, exc)
