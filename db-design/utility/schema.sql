-- ============================================================
-- Utility Service — база данных: utility_db
-- СУБД: PostgreSQL 15+
-- Назначение: заявки ЖКХ (issues) и история изменения статусов.
-- user_id — ссылка на Identity Service БЕЗ FK.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TYPE issue_category AS ENUM ('water', 'electricity', 'heating', 'road', 'garbage', 'other');
CREATE TYPE issue_status   AS ENUM ('new', 'in_progress', 'resolved', 'rejected');

CREATE TABLE issues (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL,                 -- автор заявки (Identity Service)
    category    issue_category NOT NULL,
    description TEXT NOT NULL,
    address     VARCHAR(255),
    latitude    DOUBLE PRECISION,
    longitude   DOUBLE PRECISION,
    status      issue_status NOT NULL DEFAULT 'new',
    assigned_to UUID,                          -- id оператора (Identity Service), опционально
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_issues_user_id ON issues (user_id);
CREATE INDEX idx_issues_status  ON issues (status);

CREATE TABLE issue_status_history (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id    UUID NOT NULL REFERENCES issues (id) ON DELETE CASCADE,
    old_status  issue_status,
    new_status  issue_status NOT NULL,
    changed_by  UUID NOT NULL,                 -- id пользователя, изменившего статус
    comment     TEXT,
    changed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_status_history_issue_id ON issue_status_history (issue_id);

CREATE OR REPLACE FUNCTION trg_set_updated_at_issues() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER issues_set_updated_at
BEFORE UPDATE ON issues
FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at_issues();
