import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models import InvoiceStatus, PaymentStatus, PaymentMethod


# ---------- Accounts ----------

class AccountCreate(BaseModel):
    user_id: int
    currency: str = "RUB"


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: int
    balance: Decimal
    currency: str
    created_at: datetime


# ---------- Invoices ----------

class InvoiceCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: str = "RUB"
    description: Optional[str] = None
    due_date: date


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    amount: Decimal
    currency: str
    description: Optional[str]
    status: InvoiceStatus
    due_date: date
    created_at: datetime


# ---------- Payments ----------

class PaymentCreate(BaseModel):
    invoice_id: uuid.UUID
    method: PaymentMethod


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_id: uuid.UUID
    amount: Decimal
    method: PaymentMethod
    status: PaymentStatus
    provider_ref: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]


class PaymentWebhookPayload(BaseModel):
    """Payload, присылаемый внешним платёжным провайдером."""
    provider_ref: str
    status: str  # ожидаем "succeeded" для данного endpoint'а
    amount: Decimal
    raw: Optional[dict] = None


class ErrorResponse(BaseModel):
    detail: str
