from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from . import models, schemas


def get_vehicles(db: Session):
    return db.query(models.Vehicle).order_by(models.Vehicle.plate_number).all()


def get_parking_lots(db: Session):
    return db.query(models.ParkingLot).order_by(models.ParkingLot.name).all()


def reserve_parking(
    db: Session,
    parking_lot_id: UUID,
    user_id: UUID,
    payload: schemas.ParkingReservationCreate,
):
    if payload.end_time <= payload.start_time:
        return None, "end_time must be greater than start_time"

    parking = (
        db.query(models.ParkingLot)
        .filter(models.ParkingLot.id == parking_lot_id)
        .with_for_update()
        .first()
    )
    if not parking:
        return None, "Parking lot not found"

    if parking.available_spaces <= 0:
        return None, "No available parking spaces"

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
    return reservation, None
