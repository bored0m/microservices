import logging

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from . import auth, crud, database, schemas, services

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("environment_service")

app = FastAPI(
    title="Environment Service",
    description="Датчики окружающей среды умного города",
    version="1.0.0",
)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


@app.get(
    "/sensors",
    response_model=list[schemas.SensorResponse],
    tags=["sensors"],
)
def get_sensors(
    db: Session = Depends(database.get_db),
    _user_id=Depends(auth.get_current_user_id),
):
    return crud.get_sensors(db)


@app.get(
    "/sensors/{sensor_id}/data",
    response_model=list[schemas.SensorDataResponse],
    tags=["sensors"],
)
def get_sensor_data(
    sensor_id,
    db: Session = Depends(database.get_db),
    _user_id=Depends(auth.get_current_user_id),
):
    data = crud.get_sensor_data(db, sensor_id)
    return data


@app.post(
    "/sensors/data",
    response_model=schemas.SensorDataResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["sensors"],
)
def create_sensor_data(
    payload: schemas.SensorDataCreate,
    db: Session = Depends(database.get_db),
    _user_id=Depends(auth.get_current_user_id),
):
    result, error = crud.create_sensor_data(db, payload)
    if error:
        raise HTTPException(status_code=404, detail=error)

    sensor, data = result
    logger.info(
        "Sensor data received: sensor=%s value=%s",
        sensor.id,
        data.value,
    )

    alert = services.check_threshold(sensor.sensor_type, data.value)
    if alert:
        logger.warning(
            "Sensor threshold exceeded: sensor=%s alert=%s",
            sensor.id,
            alert,
        )
        services.send_notification(
            template_code="SENSOR_ALERT",
            template_data={
                "sensor_name": sensor.name,
                "sensor_type": sensor.sensor_type,
                "value": str(data.value),
                "location": sensor.location,
                "alert": alert,
            },
        )

    return data
