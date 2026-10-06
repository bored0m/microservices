import uuid
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from .database import Base


class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    sensor_type = Column(String(64), nullable=False)
    location = Column(String(255), nullable=False)
    unit = Column(String(32), nullable=True)
    status = Column(String(32), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SensorData(Base):
    __tablename__ = "sensor_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sensor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sensors.id"),
        nullable=False,
        index=True,
    )
    value = Column(Numeric(14, 4), nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
