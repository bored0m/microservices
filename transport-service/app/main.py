import logging
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import crud, schemas, services
from .config import CORS_ORIGINS
from .database import Base, engine, get_db
from .deps import CurrentUser, get_current_user, require_admin

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("transport")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    log.info("Transport service started, tables ready")
    yield


app = FastAPI(
    title="Transport Service",
    description=(
        "Транспорт и парковки умного города. Токены проверяются через Auth Service по HTTP. "
        "Транспорт и парковки создаёт и удаляет администратор; жители бронируют места."
    ),
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"]
)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


@app.get("/vehicles", response_model=list[schemas.VehicleResponse], tags=["transport"])
def get_vehicles(db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user)):
    return crud.get_vehicles(db)


def _http(exc: Exception) -> HTTPException:
    code = {crud.NotFound: 404, crud.Conflict: 409, crud.Invalid: 422}[type(exc)]
    return HTTPException(code, str(exc))


@app.post("/vehicles", response_model=schemas.VehicleResponse, status_code=status.HTTP_201_CREATED, tags=["transport"])
def create_vehicle(payload: schemas.VehicleCreate, db: Session = Depends(get_db), _: CurrentUser = Depends(require_admin)):
    try:
        return crud.create_vehicle(db, payload)
    except (crud.NotFound, crud.Conflict, crud.Invalid) as exc:
        raise _http(exc)


@app.patch("/vehicles/{vehicle_id}", response_model=schemas.VehicleResponse, tags=["transport"])
def update_vehicle(
    vehicle_id: UUID,
    payload: schemas.VehicleUpdate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
):
    try:
        return crud.update_vehicle(db, vehicle_id, payload)
    except (crud.NotFound, crud.Conflict, crud.Invalid) as exc:
        raise _http(exc)


@app.delete("/vehicles/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["transport"])
def delete_vehicle(vehicle_id: UUID, db: Session = Depends(get_db), _: CurrentUser = Depends(require_admin)):
    try:
        crud.delete_vehicle(db, vehicle_id)
    except (crud.NotFound, crud.Conflict, crud.Invalid) as exc:
        raise _http(exc)


@app.get("/parking", response_model=list[schemas.ParkingResponse], tags=["parking"])
def get_parking(db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user)):
    return crud.get_parking_lots(db)


@app.post("/parking", response_model=schemas.ParkingResponse, status_code=status.HTTP_201_CREATED, tags=["parking"])
def create_parking(payload: schemas.ParkingCreate, db: Session = Depends(get_db), _: CurrentUser = Depends(require_admin)):
    return crud.create_parking(db, payload)


@app.delete("/parking/{parking_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["parking"])
def delete_parking(parking_id: UUID, db: Session = Depends(get_db), _: CurrentUser = Depends(require_admin)):
    try:
        crud.delete_parking(db, parking_id)
    except (crud.NotFound, crud.Conflict, crud.Invalid) as exc:
        raise _http(exc)


@app.get("/parking/reservations", response_model=list[schemas.ParkingReservationResponse], tags=["parking"])
def my_reservations(db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    """Житель видит свои брони, администратор — все."""
    return crud.get_reservations(db, None if user.is_admin else user.id)


@app.post(
    "/parking/{parking_id}/reserve",
    response_model=schemas.ParkingReservationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["parking"],
)
def reserve_parking(
    parking_id: UUID,
    payload: schemas.ParkingReservationCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    try:
        reservation, parking = crud.reserve_parking(db, parking_id, user.id, payload)
    except crud.NotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    except crud.Invalid as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    except crud.Conflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))

    log.info("Parking reserved: reservation=%s parking=%s user=%s", reservation.id, parking_id, user.id)
    background.add_task(
        services.send_notification,
        user.id,
        "PARKING_RESERVED",
        {
            "parking_name": parking.name,
            "end_time": reservation.end_time.strftime("%d.%m.%Y %H:%M"),
        },
    )
    return reservation


@app.post(
    "/parking/reservations/{reservation_id}/cancel",
    response_model=schemas.ParkingReservationResponse,
    tags=["parking"],
)
def cancel_reservation(
    reservation_id: UUID,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    try:
        return crud.cancel_reservation(db, reservation_id, user.id, user.is_admin)
    except crud.NotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    except crud.Conflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
