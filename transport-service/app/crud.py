from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas


class NotFound(Exception):
    pass


class Conflict(Exception):
    pass


class Invalid(Exception):
    pass


def get_vehicles(db: Session):
    return db.scalars(select(models.Vehicle).order_by(models.Vehicle.plate_number)).all()


def get_parking_lots(db: Session):
    return db.scalars(select(models.ParkingLot).order_by(models.ParkingLot.name)).all()


def get_reservations(db: Session, user_id: int | None):
    stmt = select(models.ParkingReservation).order_by(models.ParkingReservation.created_at.desc())
    if user_id is not None:
        stmt = stmt.where(models.ParkingReservation.user_id == user_id)
    return db.scalars(stmt).all()


def reserve_parking(db: Session, parking_lot_id: UUID, user_id: int, payload: schemas.ParkingReservationCreate):
    if payload.end_time <= payload.start_time:
        raise Invalid("end_time must be greater than start_time")
    parking = db.scalar(
        select(models.ParkingLot).where(models.ParkingLot.id == parking_lot_id).with_for_update()
    )
    if parking is None:
        raise NotFound("Parking lot not found")
    if parking.available_spaces <= 0:
        raise Conflict("No available parking spaces")

    reservation = models.ParkingReservation(
        parking_lot_id=parking_lot_id,
        user_id=user_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        status="active",
    )
    parking.available_spaces -= 1
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation, parking


def cancel_reservation(db: Session, reservation_id: UUID, user_id: int, is_admin: bool):
    reservation = db.get(models.ParkingReservation, reservation_id)
    if reservation is None or (reservation.user_id != user_id and not is_admin):
        raise NotFound("Reservation not found")
    if reservation.status != "active":
        raise Conflict("Reservation is not active")
    parking = db.scalar(
        select(models.ParkingLot).where(models.ParkingLot.id == reservation.parking_lot_id).with_for_update()
    )
    reservation.status = "cancelled"
    if parking is not None:
        parking.available_spaces = min(parking.total_spaces, parking.available_spaces + 1)
    db.commit()
    db.refresh(reservation)
    return reservation


def create_vehicle(db: Session, payload: schemas.VehicleCreate):
    plate = payload.plate_number.strip().upper()
    if db.scalar(select(models.Vehicle.id).where(models.Vehicle.plate_number == plate)):
        raise Conflict("Vehicle with this plate number already exists")
    vehicle = models.Vehicle(
        plate_number=plate,
        vehicle_type=payload.vehicle_type.value,
        model=payload.model,
        status=payload.status.value,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


def update_vehicle(db: Session, vehicle_id: UUID, payload: schemas.VehicleUpdate):
    vehicle = db.get(models.Vehicle, vehicle_id)
    if vehicle is None:
        raise NotFound("Vehicle not found")
    vehicle.status = payload.status.value
    db.commit()
    db.refresh(vehicle)
    return vehicle


def delete_vehicle(db: Session, vehicle_id: UUID) -> None:
    vehicle = db.get(models.Vehicle, vehicle_id)
    if vehicle is None:
        raise NotFound("Vehicle not found")
    db.delete(vehicle)
    db.commit()


def create_parking(db: Session, payload: schemas.ParkingCreate):
    lot = models.ParkingLot(
        name=payload.name.strip(),
        address=payload.address.strip(),
        total_spaces=payload.total_spaces,
        available_spaces=payload.total_spaces,
    )
    db.add(lot)
    db.commit()
    db.refresh(lot)
    return lot


def delete_parking(db: Session, parking_id: UUID) -> None:
    lot = db.get(models.ParkingLot, parking_id)
    if lot is None:
        raise NotFound("Parking lot not found")
    reservations = db.scalars(
        select(models.ParkingReservation).where(models.ParkingReservation.parking_lot_id == parking_id)
    ).all()
    if any(r.status == "active" for r in reservations):
        raise Conflict("Parking lot has active reservations; cancel them first")
    for r in reservations:
        db.delete(r)
    db.delete(lot)
    db.commit()
