-- Migration 15: Customer Engagement P4 Autopilot Feature Flag & Settings

CREATE TABLE IF NOT EXISTS engagement.engagement_autopilot_settings (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL UNIQUE,
  enabled BOOLEAN NOT NULL DEFAULT FALSE,
  env_allowlist JSONB NOT NULL DEFAULT '["test", "staging"]'::jsonb,
  trigger_rule_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  containment_min NUMERIC(5, 4) NOT NULL DEFAULT 0.8000,
  error_max NUMERIC(5, 4) NOT NULL DEFAULT 0.0500,
  takeover_max NUMERIC(5, 4) NOT NULL DEFAULT 0.1500,
  updated_by_workforce_member_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS engagement.engagement_autopilot_templates (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  template_key TEXT NOT NULL,
  version INT NOT NULL DEFAULT 1,
  body_hash TEXT NOT NULL,
  body TEXT NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_engagement_autopilot_template UNIQUE (workspace_id, template_key, version)
);

CREATE TABLE IF NOT EXISTS engagement.engagement_autopilot_runs (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  run_id TEXT NOT NULL UNIQUE,
  trigger_rule_id TEXT NOT NULL,
  thread_id BIGINT NOT NULL,
  outcome TEXT NOT NULL DEFAULT 'completed',
  handed_off BOOLEAN NOT NULL DEFAULT FALSE,
  approval_count INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_engagement_autopilot_runs_ws_created
  ON engagement.engagement_autopilot_runs (workspace_id, created_at DESC);
