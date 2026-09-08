-- Rollback migration 34: Workspace invitations

ALTER TABLE cosa.workspace_memberships
  DROP CONSTRAINT IF EXISTS workspace_memberships_role_check;
ALTER TABLE cosa.workspace_memberships
  ADD CONSTRAINT platform_workspace_memberships_role_check
  CHECK (role IN ('founder', 'member', 'viewer'));

DROP INDEX IF EXISTS cosa.idx_workspace_invitations_workspace;
DROP INDEX IF EXISTS cosa.ux_workspace_invitations_token_hash;
DROP INDEX IF EXISTS cosa.ux_workspace_invitations_pending_email;
DROP TABLE IF EXISTS cosa.workspace_invitations;
