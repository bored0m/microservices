import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Sensor(Base):
    __tablename__ = "sensors"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    sensor_type: Mapped[str] = mapped_column(String(64))  # air_quality | noise | temperature | ...
    location: Mapped[str] = mapped_column(String(255))
    unit: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class SensorData(Base):
    __tablename__ = "sensor_data"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    sensor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sensors.id"), index=True)
    value: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
