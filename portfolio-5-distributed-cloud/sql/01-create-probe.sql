-- Portfolio 5 probe table.
-- It lives in its own schema so the NexaCart `public` tables keep exactly the
-- Portfolio 1 data. Each row is written on the primary and read back on the
-- replica to show when a change becomes visible.
CREATE SCHEMA IF NOT EXISTS p5_distributed;

CREATE TABLE p5_distributed.replication_probe (
    probe_id BIGSERIAL PRIMARY KEY,
    note VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
