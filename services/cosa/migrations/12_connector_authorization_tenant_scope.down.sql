-- Rollback 12_connector_authorization_tenant_scope.up.sql
DROP INDEX IF EXISTS control_plane.idx_connector_authorizations_tenant;

ALTER TABLE control_plane.connector_authorizations
  DROP COLUMN IF EXISTS workspace_id,
  DROP COLUMN IF EXISTS company_id;
