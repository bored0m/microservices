import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .models import InvoiceStatus, PaymentMethod, PaymentStatus

Money = Decimal


class AccountCreate(BaseModel):
    # Если не указан — счёт создаётся для текущего пользователя.
    user_id: uuid.UUID | None = None


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    balance: Money
    currency: str
    created_at: datetime


class InvoiceCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    description: str | None = Field(default=None, max_length=255)
    due_date: date


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    account_id: uuid.UUID
    amount: Money
    currency: str
    description: str | None
    status: InvoiceStatus
    due_date: date
    created_at: datetime


class PaymentCreate(BaseModel):
    invoice_id: uuid.UUID
    method: PaymentMethod


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    invoice_id: uuid.UUID
    amount: Money
    method: PaymentMethod
    status: PaymentStatus
    provider_ref: str | None
    created_at: datetime
    completed_at: datetime | None


class WebhookSuccessIn(BaseModel):
    provider_ref: str = Field(min_length=1, max_length=255)
    status: Literal["succeeded"] = "succeeded"
    amount: Decimal | None = Field(default=None, gt=0)


class WebhookAck(BaseModel):
    status: Literal["processed", "already_processed"]
    payment_id: uuid.UUID
