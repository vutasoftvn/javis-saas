-- Rollback 11_workspace_connectors_and_schedules.up.sql
DROP TABLE IF EXISTS control_plane.workspace_schedule_executions CASCADE;
DROP TABLE IF EXISTS control_plane.workspace_schedule_definitions CASCADE;
DROP TABLE IF EXISTS control_plane.session_connector_grants CASCADE;
DROP TABLE IF EXISTS control_plane.connector_authorizations CASCADE;
DROP TABLE IF EXISTS control_plane.workspace_connector_installations CASCADE;
