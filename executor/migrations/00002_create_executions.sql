-- +goose Up
CREATE TABLE executions (
    id              UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID             NOT NULL,
    attempt_id      UUID             NOT NULL,
    webhook_url     TEXT             NOT NULL CHECK (webhook_url LIKE 'http://%' OR webhook_url LIKE 'https://%'),
    payload         JSONB            NOT NULL DEFAULT '{}',
    status          execution_status NOT NULL DEFAULT 'RECEIVED',
    http_status     INT              CHECK (http_status IS NULL OR http_status BETWEEN 100 AND 599),
    response_body   TEXT,
    started_at      TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    duration_ms     INT              CHECK (duration_ms IS NULL OR duration_ms >= 0),
    error_message   TEXT,
    created_at      TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ      NOT NULL DEFAULT NOW(),

    -- constraints
    CONSTRAINT chk_completed_after_started CHECK (completed_at IS NULL OR completed_at >= started_at),
    CONSTRAINT uq_executions_attempt_id    UNIQUE (attempt_id)
);

-- indexes
CREATE INDEX idx_executions_task_id ON executions (task_id);
-- attempt_id index is created automatically by the uq_executions_attempt_id constraint

-- index
CREATE INDEX idx_executions_status_started_at ON executions (status, started_at);


-- +goose Down
DROP TABLE IF EXISTS executions;