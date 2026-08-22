CREATE SCHEMA IF NOT EXISTS legal;

CREATE TABLE legal.legal_checklist_items (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'OPEN',
  evidence_artifact_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_legal_checklist_items_workspace_id ON legal.legal_checklist_items(workspace_id);

CREATE TABLE legal.legal_obligations (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  due_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'OPEN',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_legal_obligations_workspace_id ON legal.legal_obligations(workspace_id);
