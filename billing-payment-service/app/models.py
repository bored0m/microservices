import uuid
import enum

from sqlalchemy import (
    Column, String, Numeric, Date, DateTime, ForeignKey, Enum as SAEnum, Boolean, Integer,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class InvoiceStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    overdue = "overdue"
    cancelled = "cancelled"


class PaymentStatus(str, enum.Enum):
    created = "created"
    processing = "processing"
    succeeded = "succeeded"
    failed = "failed"


class PaymentMethod(str, enum.Enum):
    card = "card"
    bank_transfer = "bank_transfer"
    wallet = "wallet"


class Account(Base):
    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, nullable=False, unique=True, index=True)  # ref: identity_db.users.id
    balance = Column(Numeric(12, 2), nullable=False, default=0)
    currency = Column(String(3), nullable=False, default="RUB")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    invoices = relationship("Invoice", back_populates="account", cascade="all, delete-orphan")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="RUB")
    description = Column(String(255))
    status = Column(SAEnum(InvoiceStatus, name="invoice_status"), nullable=False, default=InvoiceStatus.pending, index=True)
    due_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    account = relationship("Account", back_populates="invoices")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    method = Column(SAEnum(PaymentMethod, name="payment_method"), nullable=False)
    status = Column(SAEnum(PaymentStatus, name="payment_status"), nullable=False, default=PaymentStatus.created)
    provider_ref = Column(String(255), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    invoice = relationship("Invoice", back_populates="payments")


class PaymentWebhookEvent(Base):
    __tablename__ = "payment_webhook_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id", ondelete="SET NULL"), nullable=True)
    event_type = Column(String(64), nullable=False)
    raw_payload = Column(JSONB, nullable=False)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    processed = Column(Boolean, nullable=False, default=False)
