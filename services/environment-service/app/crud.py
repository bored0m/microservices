from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from . import models, schemas


def get_sensors(db: Session):
    return db.query(models.Sensor).order_by(models.Sensor.name).all()


def get_sensor_data(db: Session, sensor_id: UUID):
    return (
        db.query(models.SensorData)
        .filter(models.SensorData.sensor_id == sensor_id)
        .order_by(models.SensorData.recorded_at.desc())
        .all()
    )


def create_sensor_data(
    db: Session,
    payload: schemas.SensorDataCreate,
):
    sensor = (
        db.query(models.Sensor)
        .filter(models.Sensor.id == payload.sensor_id)
        .first()
    )
    if not sensor:
        return None, "Sensor not found"

    data = models.SensorData(
        sensor_id=payload.sensor_id,
        value=payload.value,
        recorded_at=payload.recorded_at,
    )
    db.add(data)
    db.commit()
    db.refresh(data)
    return (sensor, data), None
