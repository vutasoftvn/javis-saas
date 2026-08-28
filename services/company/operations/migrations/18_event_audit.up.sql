CREATE TABLE IF NOT EXISTS integration.event_audit (
  id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  workspace_id TEXT        NOT NULL,
  action       TEXT        NOT NULL,
  payload      JSONB       NOT NULL,
  actor_id     TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_event_audit_ws_action ON integration.event_audit (workspace_id, action, created_at DESC);
