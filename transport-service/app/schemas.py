from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VehicleType(str, Enum):
    bus = "bus"
    tram = "tram"
    shuttle = "shuttle"
    municipal_car = "municipal_car"


class VehicleStatus(str, Enum):
    active = "active"
    idle = "idle"
    maintenance = "maintenance"
    offline = "offline"


class VehicleCreate(BaseModel):
    plate_number: str = Field(min_length=2, max_length=32)
    vehicle_type: VehicleType
    model: str | None = Field(default=None, max_length=128)
    status: VehicleStatus = VehicleStatus.active


class VehicleUpdate(BaseModel):
    status: VehicleStatus


class ParkingCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    address: str = Field(min_length=2, max_length=255)
    total_spaces: int = Field(ge=1, le=100000)


class VehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    plate_number: str
    vehicle_type: str
    model: str | None = None
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
    user_id: int
    start_time: datetime
    end_time: datetime
    status: str
    created_at: datetime
