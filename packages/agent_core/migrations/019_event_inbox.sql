-- AgentOS inbox: idempotency theo (workspace_id, event_id, consumer_name).
-- At-least-once delivery từ relay → duplicate POST không tạo run thứ hai.
CREATE TABLE IF NOT EXISTS event_inbox (
  id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  workspace_id      TEXT        NOT NULL,
  event_id          UUID        NOT NULL,
  consumer_name     TEXT        NOT NULL,
  event_type        TEXT        NOT NULL,
  correlation_id    TEXT        NOT NULL,
  received_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  outcome           TEXT        NOT NULL,
  scheduled_task_id TEXT,
  UNIQUE (workspace_id, event_id, consumer_name)
);
CREATE INDEX IF NOT EXISTS idx_event_inbox_correlation ON event_inbox (workspace_id, correlation_id);
