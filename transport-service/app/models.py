import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    plate_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    vehicle_type: Mapped[str] = mapped_column(String(64))  # bus | tram | shuttle | municipal_car
    model: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="active")  # active | idle | maintenance | offline


class ParkingLot(Base):
    __tablename__ = "parking_lots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str] = mapped_column(String(255))
    total_spaces: Mapped[int]
    available_spaces: Mapped[int]


class ParkingReservation(Base):
    __tablename__ = "parking_reservations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    parking_lot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("parking_lots.id"), index=True)
    user_id: Mapped[int] = mapped_column(index=True)  # id из Auth Service (без FK)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="active")  # active | cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
