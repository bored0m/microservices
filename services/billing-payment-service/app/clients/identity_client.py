import logging
import uuid

import httpx

from ..config import get_settings

log = logging.getLogger("billing.identity")


class IdentityUnavailable(Exception):
    """Identity & Auth Service недоступен или вернул неожиданный ответ."""


def user_exists(user_id: uuid.UUID, token: str) -> bool:
    """GET /users/{id} в Identity Service. Токен вызывающего пробрасывается как есть."""
    s = get_settings()
    if not s.verify_users:
        return True
    try:
        resp = httpx.get(
            f"{s.identity_service_url}/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=s.http_timeout,
        )
    except httpx.HTTPError as exc:
        log.error("Identity Service unreachable: %s", exc)
        raise IdentityUnavailable() from exc
    if resp.status_code == 200:
        return True
    if resp.status_code == 404:
        return False
    log.error("Identity Service unexpected status %s for user=%s", resp.status_code, user_id)
    raise IdentityUnavailable()
