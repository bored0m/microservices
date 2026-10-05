-- ============================================================
-- Environment Service — база данных: environment_db
-- СУБД: PostgreSQL 15+ (рекомендуется расширение TimescaleDB
-- для sensor_data как time-series, но не обязательно)
-- Назначение: датчики и показания экологического мониторинга.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TYPE sensor_type   AS ENUM ('air_quality', 'noise', 'water_quality', 'temperature', 'radiation');
CREATE TYPE sensor_status AS ENUM ('online', 'offline', 'maintenance');

CREATE TABLE sensors (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type           sensor_type NOT NULL,
    location_name  VARCHAR(255),
    latitude       DOUBLE PRECISION NOT NULL,
    longitude      DOUBLE PRECISION NOT NULL,
    status         sensor_status NOT NULL DEFAULT 'online',
    installed_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_sensors_type   ON sensors (type);
CREATE INDEX idx_sensors_status ON sensors (status);

CREATE TABLE sensor_data (
    id           BIGSERIAL PRIMARY KEY,
    sensor_id    UUID NOT NULL REFERENCES sensors (id) ON DELETE CASCADE,
    metric_name  VARCHAR(64) NOT NULL,      -- напр. 'PM2.5', 'CO2', 'dB', 'pH'
    value        NUMERIC(12,4) NOT NULL,
    unit         VARCHAR(16) NOT NULL,      -- напр. 'µg/m3', 'dB', 'ppm'
    recorded_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_sensor_data_sensor_id    ON sensor_data (sensor_id);
CREATE INDEX idx_sensor_data_recorded_at  ON sensor_data (recorded_at);
CREATE INDEX idx_sensor_data_sensor_time  ON sensor_data (sensor_id, recorded_at DESC);
