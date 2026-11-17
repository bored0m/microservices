import os

DATABASE_URL = os.environ["DATABASE_URL"]
AUTH_SERVICE_URL = os.environ["AUTH_SERVICE_URL"].rstrip("/")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8000").rstrip("/")
