-- 041_restore_automation_constraints.up.sql
--
-- The clean-slate baseline (d8ed690d) deleted 003_cosa_automation_mvp, and
-- 002_restore_baseline_gaps recreated the four operating.automation_* tables with
-- primary keys ONLY. This restores the constraints and indexes of the deleted
-- migration (and still declared by shared/db/schema/operations.ts):
--   * 4 intra-DB FKs ON DELETE CASCADE (Drizzle declares plain id FKs, so the
--     same shape is restored; tenancy is carried by the workspace-leading
--     unique indexes below),
--   * 4 CHECKs (lifecycle_state, autonomy_class, trigger_kind, state),
--   * 4 UNIQUE indexes (uix_automation_invocations_identity is what makes
--     automation-invocation.service.ts select-then-insert idempotency race-safe),
--   * 4 supporting indexes.
-- Expand-only and idempotent. Constraints are added NOT VALID then VALIDATEd:
-- existing rows that violate them (orphans / duplicates) make this migration
-- fail loudly rather than being silently accepted.

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_automation_revisions_definition') THEN
    ALTER TABLE operating.automation_revisions
      ADD CONSTRAINT fk_automation_revisions_definition
      FOREIGN KEY (definition_id) REFERENCES operating.automation_definitions(id)
      ON DELETE CASCADE NOT VALID;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_automation_invocations_definition') THEN
    ALTER TABLE operating.automation_invocations
      ADD CONSTRAINT fk_automation_invocations_definition
      FOREIGN KEY (definition_id) REFERENCES operating.automation_definitions(id)
      ON DELETE CASCADE NOT VALID;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_automation_invocations_revision') THEN
    ALTER TABLE operating.automation_invocations
      ADD CONSTRAINT fk_automation_invocations_revision
      FOREIGN KEY (revision_id) REFERENCES operating.automation_revisions(id)
      ON DELETE CASCADE NOT VALID;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_automation_invocation_events_invocation') THEN
    ALTER TABLE operating.automation_invocation_events
      ADD CONSTRAINT fk_automation_invocation_events_invocation
      FOREIGN KEY (invocation_id) REFERENCES operating.automation_invocations(id)
      ON DELETE CASCADE NOT VALID;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_automation_definitions_lifecycle_state') THEN
    ALTER TABLE operating.automation_definitions
      ADD CONSTRAINT chk_automation_definitions_lifecycle_state
      CHECK (lifecycle_state IN ('DRAFT', 'PUBLISHED', 'SUSPENDED', 'RETIRED')) NOT VALID;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_automation_revisions_autonomy_class') THEN
    ALTER TABLE operating.automation_revisions
      ADD CONSTRAINT chk_automation_revisions_autonomy_class
      CHECK (autonomy_class IN ('read_only', 'draft_only', 'gated_effect')) NOT VALID;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_automation_invocations_trigger_kind') THEN
    ALTER TABLE operating.automation_invocations
      ADD CONSTRAINT chk_automation_invocations_trigger_kind
      CHECK (trigger_kind IN ('manual', 'schedule', 'business_event')) NOT VALID;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_automation_invocations_state') THEN
    ALTER TABLE operating.automation_invocations
      ADD CONSTRAINT chk_automation_invocations_state
      CHECK (state IN ('REQUESTED', 'QUEUED', 'LEASED', 'RUNNING', 'WAITING_APPROVAL',
                       'COMPLETED', 'FAILED', 'CANCELLED', 'BLOCKED', 'CANCEL_REQUESTED')) NOT VALID;
  END IF;
END $$;

ALTER TABLE operating.automation_revisions VALIDATE CONSTRAINT fk_automation_revisions_definition;
ALTER TABLE operating.automation_invocations VALIDATE CONSTRAINT fk_automation_invocations_definition;
ALTER TABLE operating.automation_invocations VALIDATE CONSTRAINT fk_automation_invocations_revision;
ALTER TABLE operating.automation_invocation_events VALIDATE CONSTRAINT fk_automation_invocation_events_invocation;
ALTER TABLE operating.automation_definitions VALIDATE CONSTRAINT chk_automation_definitions_lifecycle_state;
ALTER TABLE operating.automation_revisions VALIDATE CONSTRAINT chk_automation_revisions_autonomy_class;
ALTER TABLE operating.automation_invocations VALIDATE CONSTRAINT chk_automation_invocations_trigger_kind;
ALTER TABLE operating.automation_invocations VALIDATE CONSTRAINT chk_automation_invocations_state;

CREATE UNIQUE INDEX IF NOT EXISTS uix_automation_definitions_ws_key
  ON operating.automation_definitions (workspace_id, automation_key)
  WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_automation_definitions_workspace
  ON operating.automation_definitions (workspace_id);

CREATE UNIQUE INDEX IF NOT EXISTS uix_automation_revisions_definition_no
  ON operating.automation_revisions (definition_id, revision_no);
CREATE INDEX IF NOT EXISTS idx_automation_revisions_ws_definition
  ON operating.automation_revisions (workspace_id, definition_id, revision_no DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uix_automation_invocations_identity
  ON operating.automation_invocations (workspace_id, revision_id, idempotency_key);
CREATE INDEX IF NOT EXISTS idx_automation_invocations_ws_state
  ON operating.automation_invocations (workspace_id, state, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_automation_invocations_ws_run
  ON operating.automation_invocations (workspace_id, agent_run_id);

CREATE UNIQUE INDEX IF NOT EXISTS uix_automation_invocation_events_seq
  ON operating.automation_invocation_events (workspace_id, invocation_id, seq);
