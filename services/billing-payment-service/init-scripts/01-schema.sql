-- ============================================================
-- Billing & Payment Service — база данных: billing_db
-- СУБД: PostgreSQL 15+
-- Назначение: лицевые счета, счета-фактуры, платежи.
-- user_id — ссылка на Identity Service БЕЗ FK.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TYPE invoice_status AS ENUM ('pending', 'paid', 'overdue', 'cancelled');
CREATE TYPE payment_status AS ENUM ('created', 'processing', 'succeeded', 'failed');
CREATE TYPE payment_method AS ENUM ('card', 'bank_transfer', 'wallet');

CREATE TABLE accounts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL UNIQUE,          -- 1:1 с пользователем Identity Service
    balance     NUMERIC(12,2) NOT NULL DEFAULT 0,
    currency    CHAR(3) NOT NULL DEFAULT 'RUB',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_accounts_user_id ON accounts (user_id);

CREATE TABLE invoices (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id  UUID NOT NULL REFERENCES accounts (id) ON DELETE CASCADE,
    amount      NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    currency    CHAR(3) NOT NULL DEFAULT 'RUB',
    description VARCHAR(255),
    status      invoice_status NOT NULL DEFAULT 'pending',
    due_date    DATE NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_invoices_account_id ON invoices (account_id);
CREATE INDEX idx_invoices_status     ON invoices (status);

CREATE TABLE payments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id      UUID NOT NULL REFERENCES invoices (id) ON DELETE CASCADE,
    amount          NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    method          payment_method NOT NULL,
    status          payment_status NOT NULL DEFAULT 'created',
    provider_ref    VARCHAR(255),             -- id транзакции у внешнего платёжного провайдера
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX idx_payments_invoice_id   ON payments (invoice_id);
CREATE INDEX idx_payments_provider_ref ON payments (provider_ref);

-- Журнал входящих вебхуков от платёжного провайдера (для идемпотентности и аудита)
CREATE TABLE payment_webhook_events (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id    UUID REFERENCES payments (id) ON DELETE SET NULL,
    event_type    VARCHAR(64) NOT NULL,
    raw_payload   JSONB NOT NULL,
    received_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed     BOOLEAN NOT NULL DEFAULT FALSE
);
