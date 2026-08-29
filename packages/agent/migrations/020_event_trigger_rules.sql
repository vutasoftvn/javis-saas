-- Production event-intake wiring: rule store bền + rate-limit theo aggregate/ngày.
-- EventTriggerRule (spec §3.3) — workspace-scoped, exact event type + AgentSpec pin.
CREATE TABLE IF NOT EXISTS event_trigger_rules (
  rule_id                       TEXT PRIMARY KEY,
  workspace_id                  TEXT        NOT NULL,
  event_type                    TEXT        NOT NULL,
  agent_spec_id                 TEXT        NOT NULL,
  agent_spec_version            TEXT        NOT NULL,
  agent_spec_hash               TEXT        NOT NULL,
  mode                          TEXT        NOT NULL
                                  CHECK (mode IN ('artifact_only','proposal','write')),
  max_runs_per_aggregate_per_day INTEGER    NOT NULL DEFAULT 1,
  required_capabilities         JSONB       NOT NULL DEFAULT '[]'::jsonb,
  aggregate_filter              JSONB,
  owner                         TEXT        NOT NULL DEFAULT 'operator',
  enabled                       BOOLEAN     NOT NULL DEFAULT false,
  eval_evidence_ref             TEXT,
  event_schema_version          INTEGER     NOT NULL DEFAULT 1,
  created_at                    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, event_type)
);

-- event_inbox: thêm aggregate ref để rate-limit theo aggregate/ngày (PostgresRunCounter).
ALTER TABLE event_inbox
  ADD COLUMN IF NOT EXISTS aggregate_type TEXT,
  ADD COLUMN IF NOT EXISTS aggregate_id   TEXT;

CREATE INDEX IF NOT EXISTS idx_event_inbox_agg_day
  ON event_inbox (workspace_id, aggregate_id, received_at);
