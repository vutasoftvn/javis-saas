-- Rollback migration 006
ALTER TABLE core.workspace_memberships
  DROP COLUMN IF EXISTS session_not_before;
