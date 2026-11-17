import logging
from dataclasses import dataclass

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

logger = logging.getLogger(settings.service_name)
bearer_scheme = HTTPBearer(auto_error=False)

# Роли, которые выдаёт Identity & Auth Service: resident | admin
ADMIN_ROLES = {"admin"}


@dataclass
class CurrentUser:
    id: int
    username: str
    role: str


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    """Проверяет токен, спрашивая Auth Service по HTTP (GET /users/me)."""
    if credentials is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Missing token", headers={"WWW-Authenticate": "Bearer"}
        )
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"{settings.auth_service_url}/users/me",
                headers={"Authorization": f"Bearer {credentials.credentials}"},
            )
    except httpx.RequestError as exc:
        logger.error("Auth service unreachable: %s", exc)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Auth service unavailable")

    if resp.status_code == 401:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Invalid token", headers={"WWW-Authenticate": "Bearer"}
        )
    if resp.status_code != 200:
        logger.error("Unexpected auth response: %s", resp.status_code)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Auth service error")
    data = resp.json()
    return CurrentUser(id=data["id"], username=data["username"], role=data["role"])


def require_self_or_admin(user_id: int, current_user: CurrentUser) -> None:
    if current_user.role not in ADMIN_ROLES and current_user.id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden: чужие данные")
