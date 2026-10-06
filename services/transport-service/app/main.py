import logging

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from . import auth, crud, database, schemas, services, models

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("transport_service")

app = FastAPI(
    title="Transport Service",
    description="Транспорт и парковки умного города",
    version="1.0.0",
)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


@app.get(
    "/vehicles",
    response_model=list[schemas.VehicleResponse],
    tags=["transport"],
)
def get_vehicles(
    db: Session = Depends(database.get_db),
    _user_id=Depends(auth.get_current_user_id),
):
    return crud.get_vehicles(db)


@app.get(
    "/parking",
    response_model=list[schemas.ParkingResponse],
    tags=["parking"],
)
def get_parking(
    db: Session = Depends(database.get_db),
    _user_id=Depends(auth.get_current_user_id),
):
    return crud.get_parking_lots(db)


@app.post(
    "/parking/{parking_id}/reserve",
    response_model=schemas.ParkingReservationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["parking"],
)
def reserve_parking(
    parking_id,
    payload: schemas.ParkingReservationCreate,
    db: Session = Depends(database.get_db),
    user_id=Depends(auth.get_current_user_id),
):
    reservation, error = crud.reserve_parking(
        db=db,
        parking_lot_id=parking_id,
        user_id=user_id,
        payload=payload,
    )

    if error:
        if error == "Parking lot not found":
            raise HTTPException(status_code=404, detail=error)
        raise HTTPException(status_code=409, detail=error)

    logger.info(
        "Parking reserved: reservation=%s parking=%s user=%s",
        reservation.id,
        parking_id,
        user_id,
    )

    services.send_notification(
        user_id=str(user_id),
        channel="in_app",
        template_code="PARKING_RESERVED",
        template_data={
            "parking_name": (
                db.query(models.ParkingLot)
                .filter(models.ParkingLot.id == parking_id)
                .first()
                .name
            ),
            "end_time": reservation.end_time.isoformat(),
        },
    )

    return reservation
