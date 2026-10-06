"""Тесты идут в реальный PostgreSQL (схема из init-scripts/01-schema.sql).

    BILLING_TEST_DATABASE_URL=postgresql+psycopg2://billing_user:billing_pass@localhost:5434/billing_db pytest
"""
import os

os.environ["BILLING_DATABASE_URL"] = os.environ.get(
    "BILLING_TEST_DATABASE_URL",
    "postgresql+psycopg2://billing_user:billing_pass@localhost:5432/billing_db",
)
os.environ["BILLING_JWT_SECRET"] = "test-jwt-secret"
os.environ["BILLING_WEBHOOK_SECRET"] = "test-webhook-secret"
os.environ["BILLING_VERIFY_USERS"] = "false"

import uuid  # noqa: E402

import jwt  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.database import engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def clean_db():
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE payment_webhook_events, payments, invoices, accounts CASCADE"))


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sent_notifications(monkeypatch):
    sent = []
    monkeypatch.setattr(
        "app.routers.payments.send_payment_success", lambda user_id, amount: sent.append((user_id, amount))
    )
    return sent


def make_token(user_id=None, role="resident"):
    user_id = user_id or uuid.uuid4()
    token = jwt.encode({"sub": str(user_id), "role": role}, "test-jwt-secret", algorithm="HS256")
    return user_id, {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user():
    return make_token()


@pytest.fixture
def operator():
    return make_token(role="operator")


WEBHOOK_HEADERS = {"X-Webhook-Secret": "test-webhook-secret"}
