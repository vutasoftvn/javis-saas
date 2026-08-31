-- Migration 33: Strategy canvases, canvas revisions, runtime source signals and actor snoozes

CREATE TABLE IF NOT EXISTS strategy.canvases (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  name TEXT NOT NULL CHECK (length(trim(name)) > 0),
  description TEXT NULL,
  current_revision_id BIGINT NULL,
  created_by_member_id BIGINT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ NULL,
  UNIQUE (id, workspace_id)
);

CREATE TABLE IF NOT EXISTS strategy.canvas_revisions (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  canvas_id BIGINT NOT NULL,
  parent_revision_id BIGINT NULL,
  content JSONB NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('DRAFT', 'IN_REVIEW', 'APPROVED', 'REJECTED')),
  origin TEXT NOT NULL CHECK (origin IN ('USER', 'MODEL_DRAFT')),
  source_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_by_member_id BIGINT NULL,
  reviewed_by_member_id BIGINT NULL,
  review_note TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  reviewed_at TIMESTAMPTZ NULL,
  UNIQUE (id, workspace_id),
  FOREIGN KEY (canvas_id, workspace_id) REFERENCES strategy.canvases(id, workspace_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_strategy_canvases_workspace ON strategy.canvases(workspace_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_strategy_canvas_revisions_workspace ON strategy.canvas_revisions(workspace_id, canvas_id, created_at DESC);

CREATE TABLE IF NOT EXISTS operating.runtime_source_signals (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  source_kind TEXT NOT NULL,
  source_id TEXT NOT NULL,
  sequence BIGINT NOT NULL,
  state TEXT NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL,
  correlation_id TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, source_kind, source_id, sequence)
);

CREATE INDEX IF NOT EXISTS idx_runtime_source_signals_lookup ON operating.runtime_source_signals(workspace_id, source_kind, source_id, observed_at DESC);

CREATE TABLE IF NOT EXISTS operating.runtime_snoozes (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  actor_member_id BIGINT NOT NULL,
  source_kind TEXT NOT NULL,
  source_id TEXT NOT NULL,
  snoozed_until TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, actor_member_id, source_kind, source_id)
);

CREATE INDEX IF NOT EXISTS idx_runtime_snoozes_actor ON operating.runtime_snoozes(workspace_id, actor_member_id, snoozed_until);
