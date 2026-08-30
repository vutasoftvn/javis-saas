-- services/company/operations/migrations/29_pilot_runs.up.sql
-- Strategy Domain: human-owned durable pilot runs

CREATE TABLE IF NOT EXISTS strategy.pilot_runs (
  id                              BIGINT PRIMARY KEY,
  workspace_id                    BIGINT NOT NULL,
  project_id                      BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
  experiment_id                   BIGINT REFERENCES strategy.experiments(id) ON DELETE SET NULL,
  status                          VARCHAR(50) NOT NULL DEFAULT 'DRAFT',
  design_partner_evidence_refs    JSONB NOT NULL DEFAULT '[]'::jsonb,
  metric_contract_artifact_ref    TEXT,
  instrumentation_artifact_ref    TEXT,
  onboarding_artifact_ref         TEXT,
  support_escalation_artifact_ref TEXT,
  rollback_artifact_ref           TEXT,
  release_owner_member_id         BIGINT NOT NULL,
  approved_by_member_id           BIGINT,
  approval_ref                    TEXT,
  approved_at                     TIMESTAMPTZ,
  activated_by_member_id          BIGINT,
  activated_at                    TIMESTAMPTZ,
  completed_at                    TIMESTAMPTZ,
  cancelled_at                    TIMESTAMPTZ,
  cancellation_reason             TEXT,
  version                         INTEGER NOT NULL DEFAULT 1,
  created_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at                      TIMESTAMPTZ,
  CONSTRAINT pilot_runs_status_chk
    CHECK (status IN ('DRAFT', 'APPROVED', 'ACTIVE', 'COMPLETED', 'CANCELLED'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_pilot_runs_active_project
  ON strategy.pilot_runs(workspace_id, project_id)
  WHERE status = 'ACTIVE' AND deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_pilot_runs_ws_proj
  ON strategy.pilot_runs(workspace_id, project_id);
