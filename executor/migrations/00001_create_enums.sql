-- +goose Up
CREATE TYPE execution_status AS ENUM (
    'RECEIVED',    -- webhook received, queued for processing
    'PROCESSING',  -- actively running
    'COMPLETED',   -- finished with a response
    'FAILED'       -- errored out or timed out
);


-- +goose Down
DROP TYPE IF EXISTS execution_status;