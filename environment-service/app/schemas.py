from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SensorType(str, Enum):
    air_quality = "air_quality"
    noise = "noise"
    temperature = "temperature"
    water_quality = "water_quality"
    radiation = "radiation"


class SensorStatus(str, Enum):
    active = "active"
    maintenance = "maintenance"
    offline = "offline"


class SensorCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    sensor_type: SensorType
    location: str = Field(min_length=2, max_length=255)
    unit: str | None = Field(default=None, max_length=32)  # если не указана — берётся по типу датчика
    status: SensorStatus = SensorStatus.active


class SensorUpdate(BaseModel):
    status: SensorStatus


class SensorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    sensor_type: str
    location: str
    unit: str | None = None
    status: str
    created_at: datetime | None = None
    threshold: Decimal | None = None  # порог, при превышении которого уходит SENSOR_ALERT
    latest_value: Decimal | None = None
    latest_at: datetime | None = None


class SensorDataCreate(BaseModel):
    sensor_id: UUID
    value: Decimal
    recorded_at: datetime | None = None


class SensorDataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    sensor_id: UUID
    value: Decimal
    recorded_at: datetime
