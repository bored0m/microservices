from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plate_number: str
    vehicle_type: str
    model: Optional[str] = None
    status: str


class ParkingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    address: str
    total_spaces: int
    available_spaces: int


class ParkingReservationCreate(BaseModel):
    start_time: datetime
    end_time: datetime


class ParkingReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    parking_lot_id: UUID
    user_id: UUID
    start_time: datetime
    end_time: datetime
    status: str
    created_at: datetime
