-- +goose Up
CREATE TABLE tasks (
    id               UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    name             TEXT            NOT NULL CHECK (name <> ''),
    execution_time   TIMESTAMPTZ     NOT NULL,
    webhook_url      TEXT            NOT NULL CHECK (webhook_url LIKE 'http://%' OR webhook_url LIKE 'https://%'),
    payload          JSONB           NOT NULL DEFAULT '{}',
    recurrence       recurrence_type NOT NULL DEFAULT 'NONE',
    cron_expression  TEXT,
    status           task_status     NOT NULL DEFAULT 'CREATED',
    max_retries      INT             NOT NULL CHECK (max_retries >= 0),
    retry_count      INT             NOT NULL CHECK (retry_count >= 0) DEFAULT 0,
    parent_task_id   UUID            REFERENCES tasks(id) ON DELETE SET NULL,
    created_at       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    -- constraints
    CONSTRAINT chk_retry_count_within_max CHECK (retry_count <= max_retries),

    -- cron_expression must be set if recurrence is CUSTOM_CRON
    CONSTRAINT chk_cron_expression CHECK (
        (recurrence = 'CUSTOM_CRON' AND cron_expression IS NOT NULL) OR
        (recurrence <> 'CUSTOM_CRON' AND cron_expression IS NULL)
    )
);

-- indexes
CREATE INDEX idx_tasks_status_execution_time ON tasks (status, execution_time);
CREATE INDEX idx_tasks_parent_task_id        ON tasks (parent_task_id);


-- +goose Down
DROP TABLE IF EXISTS tasks;