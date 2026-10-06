import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from .database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plate_number = Column(String(32), nullable=False, unique=True, index=True)
    vehicle_type = Column(String(64), nullable=False)
    model = Column(String(128), nullable=True)
    status = Column(String(32), nullable=False, default="active")


class ParkingLot(Base):
    __tablename__ = "parking_lots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    address = Column(String(255), nullable=False)
    total_spaces = Column(Integer, nullable=False)
    available_spaces = Column(Integer, nullable=False)


class ParkingReservation(Base):
    __tablename__ = "parking_reservations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parking_lot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("parking_lots.id"),
        nullable=False,
        index=True,
    )
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(32), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
