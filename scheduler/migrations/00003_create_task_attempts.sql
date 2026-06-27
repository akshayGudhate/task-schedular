-- +goose Up
CREATE TABLE task_attempts (
    id              UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID           NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    attempt_number  INT            NOT NULL    CHECK (attempt_number >= 1),
    started_at      TIMESTAMPTZ    NOT NULL,
    completed_at    TIMESTAMPTZ,
    http_status     INT            CHECK (http_status IS NULL OR http_status BETWEEN 100 AND 599),
    response_body   TEXT,
    duration_ms     INT            CHECK (duration_ms IS NULL OR duration_ms >= 0),
    status          attempt_status NOT NULL,
    error_message   TEXT,

    -- constraints
    CONSTRAINT uq_task_attempt UNIQUE (task_id, attempt_number),
    CONSTRAINT chk_completed_after_started CHECK (completed_at IS NULL OR completed_at >= started_at)
);

-- index
CREATE INDEX idx_task_attempts_task_id ON task_attempts (task_id);


-- +goose Down
DROP TABLE IF EXISTS task_attempts;