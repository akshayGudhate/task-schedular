-- +goose Up
CREATE TYPE task_status AS ENUM (
    'CREATED',    -- just landed, waiting for its scheduled time
    'PENDING',    -- picked up by the scheduler, about to fire
    'RUNNING',    -- webhook in-flight or being polled
    'RETRYING',   -- failed but has retries left, sitting out the backoff
    'SUCCESS',    -- clean 2xx received
    'FAILED',     -- exhausted all retries
    'CANCELLED'   -- killed before it ever ran
);

CREATE TYPE recurrence_type AS ENUM (
    'NONE',         -- one-shot
    'HOURLY',
    'DAILY',
    'CUSTOM_CRON'   -- next run computed via cron_expression
);

CREATE TYPE attempt_status AS ENUM (
    'RUNNING',  -- http request in-flight
    'SUCCESS',  -- clean response received
    'FAILED'    -- non-2xx, timeout, or connection error
);


-- +goose Down
DROP TYPE IF EXISTS attempt_status;
DROP TYPE IF EXISTS recurrence_type;
DROP TYPE IF EXISTS task_status;
