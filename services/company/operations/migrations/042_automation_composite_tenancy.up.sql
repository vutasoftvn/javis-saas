-- 042_automation_composite_tenancy.up.sql
--
-- Tenancy-consistent FKs for operating.automation_*: the plain id FKs restored by
-- 041 only guarantee the parent exists, not that it belongs to the same workspace.
-- Repo convention (020, 038/039, fk_*_proj_ws) is a composite (id, workspace_id) FK.
-- This adds, alongside the plain FKs:
--   * UNIQUE (id, workspace_id) on definitions / revisions / invocations,
--   * 4 composite FKs ON DELETE CASCADE, so a child row can never point at a
--     parent of another workspace (rejected by the database).
-- Expand-only: the plain FKs from 041 are intentionally KEPT here (migration-check
-- rejects DROPs without backup evidence); a later contract migration may drop them.
-- Idempotent. FKs are added NOT VALID then VALIDATEd; a cross-workspace orphan
-- aborts the migration (see docs/runbooks/migration-041-042-preflight.md).

CREATE UNIQUE INDEX IF NOT EXISTS uix_automation_definitions_id_workspace
  ON operating.automation_definitions (id, workspace_id);
CREATE UNIQUE INDEX IF NOT EXISTS uix_automation_revisions_id_workspace
  ON operating.automation_revisions (id, workspace_id);
CREATE UNIQUE INDEX IF NOT EXISTS uix_automation_invocations_id_workspace
  ON operating.automation_invocations (id, workspace_id);

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_automation_revisions_definition_ws') THEN
    ALTER TABLE operating.automation_revisions
      ADD CONSTRAINT fk_automation_revisions_definition_ws
      FOREIGN KEY (definition_id, workspace_id) REFERENCES operating.automation_definitions(id, workspace_id)
      ON DELETE CASCADE NOT VALID;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_automation_invocations_definition_ws') THEN
    ALTER TABLE operating.automation_invocations
      ADD CONSTRAINT fk_automation_invocations_definition_ws
      FOREIGN KEY (definition_id, workspace_id) REFERENCES operating.automation_definitions(id, workspace_id)
      ON DELETE CASCADE NOT VALID;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_automation_invocations_revision_ws') THEN
    ALTER TABLE operating.automation_invocations
      ADD CONSTRAINT fk_automation_invocations_revision_ws
      FOREIGN KEY (revision_id, workspace_id) REFERENCES operating.automation_revisions(id, workspace_id)
      ON DELETE CASCADE NOT VALID;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_automation_invocation_events_invocation_ws') THEN
    ALTER TABLE operating.automation_invocation_events
      ADD CONSTRAINT fk_automation_invocation_events_invocation_ws
      FOREIGN KEY (invocation_id, workspace_id) REFERENCES operating.automation_invocations(id, workspace_id)
      ON DELETE CASCADE NOT VALID;
  END IF;
END $$;

ALTER TABLE operating.automation_revisions VALIDATE CONSTRAINT fk_automation_revisions_definition_ws;
ALTER TABLE operating.automation_invocations VALIDATE CONSTRAINT fk_automation_invocations_definition_ws;
ALTER TABLE operating.automation_invocations VALIDATE CONSTRAINT fk_automation_invocations_revision_ws;
ALTER TABLE operating.automation_invocation_events VALIDATE CONSTRAINT fk_automation_invocation_events_invocation_ws;
