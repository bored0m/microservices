"""Настройки сервиса. Все переменные окружения имеют префикс BILLING_."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BILLING_", env_file=".env", extra="ignore")

    database_url: str

    # JWT выдаёт Identity & Auth Service; секрет должен совпадать с его JWT_SECRET.
    jwt_secret: str
    jwt_algorithm: str = "HS256"

    # Общий секрет платёжного провайдера для вебхука (заголовок X-Webhook-Secret).
    webhook_secret: str

    identity_service_url: str = "http://auth-service:8000"
    notification_service_url: str = "http://notification_service:8000"
    # Проверять существование пользователя через GET /users/{id} при создании счетов.
    verify_users: bool = True
    http_timeout: float = 5.0

    # Роли, которые могут выставлять счета и смотреть чужие данные.
    privileged_roles: tuple[str, ...] = ("admin", "operator")


@lru_cache
def get_settings() -> Settings:
    return Settings()
