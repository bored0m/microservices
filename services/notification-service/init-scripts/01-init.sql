CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TYPE notification_channel AS ENUM ('email', 'sms', 'push', 'in_app');
CREATE TYPE notification_status  AS ENUM ('queued', 'sent', 'failed');

CREATE TABLE notification_templates (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code             VARCHAR(64) NOT NULL UNIQUE,
    subject_template VARCHAR(255),
    body_template    TEXT NOT NULL
);

CREATE TABLE notifications (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID NOT NULL,
    source_service VARCHAR(64) NOT NULL,
    channel        notification_channel NOT NULL,
    title          VARCHAR(255),
    message        TEXT NOT NULL,
    status         notification_status NOT NULL DEFAULT 'queued',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_at        TIMESTAMPTZ
);

CREATE INDEX idx_notifications_user_id ON notifications (user_id);
CREATE INDEX idx_notifications_status  ON notifications (status);