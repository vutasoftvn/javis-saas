-- Rollback migration 004
DROP TABLE IF EXISTS core.membership_event_inbox;
ALTER TABLE core.workspace_memberships
  DROP COLUMN IF EXISTS membership_state,
  DROP COLUMN IF EXISTS source_membership_version,
  DROP COLUMN IF EXISTS revoked_at;
