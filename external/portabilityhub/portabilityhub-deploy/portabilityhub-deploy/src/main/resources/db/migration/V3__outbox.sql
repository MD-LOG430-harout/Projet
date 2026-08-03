CREATE TABLE outbox_event (
    id              UUID         PRIMARY KEY,
    created_at      TIMESTAMPTZ  NOT NULL,
    sent_at         TIMESTAMPTZ,
    callback_url    VARCHAR(512) NOT NULL,
    event_type      VARCHAR(128) NOT NULL,
    correlation_id  VARCHAR(64),
    payload         JSONB        NOT NULL,
    status          VARCHAR(16)  NOT NULL,
    attempts        INT          NOT NULL DEFAULT 0,
    last_error      TEXT
);

CREATE INDEX idx_outbox_status_created ON outbox_event (status, created_at);
