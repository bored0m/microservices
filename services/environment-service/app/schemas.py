from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SensorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    sensor_type: str
    location: str
    unit: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None


class SensorDataCreate(BaseModel):
    sensor_id: UUID
    value: Decimal
    recorded_at: Optional[datetime] = None


class SensorDataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sensor_id: UUID
    value: Decimal
    recorded_at: datetime
