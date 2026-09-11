-- 003_founder_controlled_authorization.down.sql
-- Rollback founder-controlled workforce authorization changes

DROP TRIGGER IF EXISTS trg_check_member_role_assignment ON core.member_role_assignments;
DROP FUNCTION IF EXISTS core.trg_check_member_role_assignment();

DROP TABLE IF EXISTS core.agent_authorization_tickets CASCADE;
DROP TABLE IF EXISTS core.authorization_events CASCADE;
DROP TABLE IF EXISTS core.agent_capability_grants CASCADE;
DROP TABLE IF EXISTS core.capability_permission_bindings CASCADE;
DROP TABLE IF EXISTS core.workspace_authorization_states CASCADE;

ALTER TABLE core.workspace_roles DROP COLUMN IF EXISTS allowed_member_types;
