from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from . import models, schemas, services

def get_sensors(db: Session) -> list[schemas.SensorResponse]:
    result = []
    for sensor in db.scalars(select(models.Sensor).order_by(models.Sensor.name)):
        latest = db.scalar(
            select(models.SensorData)
            .where(models.SensorData.sensor_id == sensor.id)
            .order_by(models.SensorData.recorded_at.desc())
            .limit(1)
        )
        item = schemas.SensorResponse.model_validate(sensor)
        item.threshold = services.threshold_for(sensor.sensor_type)
        if latest is not None:
            item.latest_value, item.latest_at = latest.value, latest.recorded_at
        result.append(item)
    return result


def get_sensor_data(db: Session, sensor_id: UUID, limit: int):
    return db.scalars(
        select(models.SensorData)
        .where(models.SensorData.sensor_id == sensor_id)
        .order_by(models.SensorData.recorded_at.desc())
        .limit(limit)
    ).all()


def create_sensor_data(db: Session, payload: schemas.SensorDataCreate):
    sensor = db.get(models.Sensor, payload.sensor_id)
    if sensor is None:
        return None, "Sensor not found"
    data = models.SensorData(sensor_id=payload.sensor_id, value=payload.value)
    if payload.recorded_at is not None:
        data.recorded_at = payload.recorded_at
    db.add(data)
    db.commit()
    db.refresh(data)
    return (sensor, data), None


def create_sensor(db: Session, payload: schemas.SensorCreate):
    sensor = models.Sensor(
        name=payload.name.strip(),
        sensor_type=payload.sensor_type.value,
        location=payload.location.strip(),
        unit=payload.unit or services.DEFAULT_UNITS.get(payload.sensor_type.value),
        status=payload.status.value,
    )
    db.add(sensor)
    db.commit()
    db.refresh(sensor)
    return sensor


def update_sensor(db: Session, sensor_id: UUID, payload: schemas.SensorUpdate):
    sensor = db.get(models.Sensor, sensor_id)
    if sensor is None:
        return None
    sensor.status = payload.status.value
    db.commit()
    db.refresh(sensor)
    return sensor


def delete_sensor(db: Session, sensor_id: UUID) -> bool:
    sensor = db.get(models.Sensor, sensor_id)
    if sensor is None:
        return False
    db.execute(delete(models.SensorData).where(models.SensorData.sensor_id == sensor_id))
    db.delete(sensor)
    db.commit()
    return True
