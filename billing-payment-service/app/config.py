from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://billing:billing_pass@billing-db:5432/billing_db"

    # Токен проверяется через Auth Service (GET /users/me), как в utility-service
    auth_service_url: str = "http://auth-service:8000"
    notification_service_url: str = "http://notification-service:8000"

    # Секрет вебхука платёжного провайдера (заголовок X-Webhook-Secret)
    payment_webhook_secret: str = "webhook-secret-change-me"

    # Учебный режим: платёж подтверждается сразу, без внешнего провайдера
    simulate_payment_success: bool = False

    cors_origins: str = "*"
    service_name: str = "billing"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="BILLING_")


settings = Settings()
