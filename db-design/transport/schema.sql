-- ============================================================
-- Transport Service — база данных: transport_db
-- СУБД: PostgreSQL 15+
-- Назначение: транспортные средства, парковки и бронирования.
-- user_id / reserved_by — ссылка на Identity-сервис БЕЗ FK
-- (валидируется через HTTP-вызов GET /users/{id} в Identity Service).
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TYPE vehicle_type   AS ENUM ('bus', 'tram', 'shuttle', 'municipal_car');
CREATE TYPE vehicle_status AS ENUM ('active', 'idle', 'maintenance', 'offline');
CREATE TYPE reservation_status AS ENUM ('pending', 'confirmed', 'cancelled', 'completed');

CREATE TABLE vehicles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type        vehicle_type NOT NULL,
    plate       VARCHAR(32) UNIQUE,
    latitude    DOUBLE PRECISION NOT NULL,
    longitude   DOUBLE PRECISION NOT NULL,
    speed_kmh   NUMERIC(5,2),
    status      vehicle_status NOT NULL DEFAULT 'active',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_vehicles_status ON vehicles (status);

CREATE TABLE parking_lots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    address         VARCHAR(255),
    latitude        DOUBLE PRECISION NOT NULL,
    longitude       DOUBLE PRECISION NOT NULL,
    total_spots     INTEGER NOT NULL CHECK (total_spots >= 0),
    available_spots INTEGER NOT NULL CHECK (available_spots >= 0),
    price_per_hour  NUMERIC(10,2) NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE parking_reservations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parking_id      UUID NOT NULL REFERENCES parking_lots (id) ON DELETE CASCADE,
    reserved_by     UUID NOT NULL,              -- user_id из Identity Service (внешняя ссылка)
    vehicle_plate   VARCHAR(32),
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ NOT NULL,
    status          reservation_status NOT NULL DEFAULT 'pending',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (end_time > start_time)
);

CREATE INDEX idx_reservations_parking_id  ON parking_reservations (parking_id);
CREATE INDEX idx_reservations_reserved_by ON parking_reservations (reserved_by);
