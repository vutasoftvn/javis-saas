-- Rollback for 030_backfill_agent_capability_grants.up.sql: chỉ gỡ grant do chính backfill này tạo.
DELETE FROM core.agent_capability_grants
WHERE id IN (
  SELECT grant_id FROM core.authorization_events
  WHERE reason = 'Startup team activation backfill (030)' AND grant_id IS NOT NULL
);
DELETE FROM core.authorization_events WHERE reason = 'Startup team activation backfill (030)';
-- Role startup_team_agent (kéo theo role_permissions và member_role_assignments qua CASCADE).
DELETE FROM core.workspace_roles WHERE role_key = 'startup_team_agent';
