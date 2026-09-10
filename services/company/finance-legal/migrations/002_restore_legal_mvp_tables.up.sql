-- 002_restore_legal_mvp_tables.up.sql
--
-- Startup Core Task-2 reconciliation: the clean-slate 001 finance-legal baseline
-- kept the new template/instance legal model (legal.legal_obligation_templates,
-- legal.legal_obligation_instances) but dropped the two MVP tables that
-- finance-legal/services/legal-obligation.service.ts and
-- legal-checklist-item.service.ts + their handlers/tests still use.
-- Restores them with plain BIGINT ids (app supplies snowflake) matching
-- shared/db/schema/finance-legal.ts. Expand-only, idempotent.

CREATE SCHEMA IF NOT EXISTS legal;

CREATE TABLE IF NOT EXISTS legal.legal_checklist_items (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'OPEN',
  evidence_artifact_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_legal_checklist_items_workspace_id ON legal.legal_checklist_items(workspace_id);

CREATE TABLE IF NOT EXISTS legal.legal_obligations (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  due_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'OPEN',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_legal_obligations_workspace_id ON legal.legal_obligations(workspace_id);
