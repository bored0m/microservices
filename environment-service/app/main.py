import logging
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import crud, schemas, services
from .config import CORS_ORIGINS
from .database import Base, engine, get_db
from .deps import CurrentUser, get_current_user, require_admin

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("environment")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    log.info("Environment service started, tables ready")
    yield


app = FastAPI(
    title="Environment Service",
    description=(
        "Датчики окружающей среды умного города. Датчики и показания добавляет администратор; "
        "при превышении порога администраторам уходит уведомление SENSOR_ALERT."
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


@app.get("/sensors", response_model=list[schemas.SensorResponse], tags=["sensors"])
def get_sensors(db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user)):
    return crud.get_sensors(db)


@app.post("/sensors", response_model=schemas.SensorResponse, status_code=status.HTTP_201_CREATED, tags=["sensors"])
def create_sensor(payload: schemas.SensorCreate, db: Session = Depends(get_db), _: CurrentUser = Depends(require_admin)):
    sensor = crud.create_sensor(db, payload)
    item = schemas.SensorResponse.model_validate(sensor)
    item.threshold = services.threshold_for(sensor.sensor_type)
    return item


@app.patch("/sensors/{sensor_id}", response_model=schemas.SensorResponse, tags=["sensors"])
def update_sensor(
    sensor_id: UUID,
    payload: schemas.SensorUpdate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
):
    sensor = crud.update_sensor(db, sensor_id, payload)
    if sensor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sensor not found")
    item = schemas.SensorResponse.model_validate(sensor)
    item.threshold = services.threshold_for(sensor.sensor_type)
    return item


@app.delete("/sensors/{sensor_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["sensors"])
def delete_sensor(sensor_id: UUID, db: Session = Depends(get_db), _: CurrentUser = Depends(require_admin)):
    if not crud.delete_sensor(db, sensor_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sensor not found")


@app.get("/sensors/{sensor_id}/data", response_model=list[schemas.SensorDataResponse], tags=["sensors"])
def get_sensor_data(
    sensor_id: UUID,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    return crud.get_sensor_data(db, sensor_id, limit)


@app.post(
    "/sensors/data",
    response_model=schemas.SensorDataResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["sensors"],
)
def create_sensor_data(
    payload: schemas.SensorDataCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(require_admin),
):
    result, error = crud.create_sensor_data(db, payload)
    if error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, error)

    sensor, data = result
    log.info("Sensor data received: sensor=%s value=%s", sensor.id, data.value)

    alert = services.check_threshold(sensor.sensor_type, data.value)
    if alert:
        log.warning("Sensor threshold exceeded: sensor=%s alert=%s", sensor.id, alert)
        background.add_task(
            services.notify_admins,
            admin.token,
            admin.id,
            "SENSOR_ALERT",
            {
                "sensor_name": sensor.name,
                "sensor_type": sensor.sensor_type,
                "value": f"{data.value.normalize():f} {sensor.unit or ''}".strip(),
                "location": sensor.location,
                "alert": alert,
            },
        )
    return data
