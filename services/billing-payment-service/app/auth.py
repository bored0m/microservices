import hmac
import logging
import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings

log = logging.getLogger("billing.auth")
bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    role: str
    token: str  # исходный JWT — пробрасываем в Identity Service при межсервисных вызовах

    @property
    def is_privileged(self) -> bool:
        return self.role in get_settings().privileged_roles


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> CurrentUser:
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Invalid or missing token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if creds is None:
        raise unauthorized
    s = get_settings()
    try:
        payload = jwt.decode(creds.credentials, s.jwt_secret, algorithms=[s.jwt_algorithm])
        user_id = uuid.UUID(str(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        log.warning("Rejected invalid token")
        raise unauthorized
    return CurrentUser(id=user_id, role=str(payload.get("role", "resident")), token=creds.credentials)


def require_self_or_privileged(user: CurrentUser, target_user_id: uuid.UUID) -> None:
    if user.id != target_user_id and not user.is_privileged:
        log.warning("Forbidden: user=%s tried to access data of user=%s", user.id, target_user_id)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access to another user's data is forbidden")


def require_privileged(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not user.is_privileged:
        log.warning("Forbidden: user=%s role=%s lacks privileges", user.id, user.role)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient privileges")
    return user


def verify_webhook_secret(x_webhook_secret: str | None = Header(default=None)) -> None:
    expected = get_settings().webhook_secret
    if not x_webhook_secret or not hmac.compare_digest(x_webhook_secret, expected):
        log.warning("Webhook rejected: bad or missing X-Webhook-Secret")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid webhook secret")
