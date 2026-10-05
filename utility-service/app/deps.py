import logging
from dataclasses import dataclass

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import AUTH_SERVICE_URL

log = logging.getLogger("utility")
bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    id: int
    username: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> CurrentUser:
    """Проверяет токен, спрашивая Auth Service по HTTP (GET /users/me)."""
    if creds is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Missing token", headers={"WWW-Authenticate": "Bearer"}
        )
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"{AUTH_SERVICE_URL}/users/me",
                headers={"Authorization": f"Bearer {creds.credentials}"},
            )
    except httpx.RequestError as exc:
        log.error("Auth service unreachable: %s", exc)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Auth service unavailable")

    if resp.status_code == 401:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Invalid token", headers={"WWW-Authenticate": "Bearer"}
        )
    if resp.status_code != 200:
        log.error("Unexpected auth response: %s", resp.status_code)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Auth service error")
    data = resp.json()
    return CurrentUser(id=data["id"], username=data["username"], role=data["role"])


async def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin role required")
    return user
