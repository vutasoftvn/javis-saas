-- Rollback 13_workspace_only_product_scope.up.sql
ALTER TABLE control_plane.workspace_connector_installations
  ADD COLUMN IF NOT EXISTS company_id BIGINT;

ALTER TABLE control_plane.workspace_connector_installations
  DROP CONSTRAINT IF EXISTS uq_connector_installation;

ALTER TABLE control_plane.workspace_connector_installations
  ADD CONSTRAINT uq_connector_installation UNIQUE (company_id, workspace_id, connector_key);

ALTER TABLE control_plane.connector_authorizations
  ADD COLUMN IF NOT EXISTS company_id BIGINT;

DROP INDEX IF EXISTS control_plane.idx_connector_authorizations_workspace;

CREATE INDEX IF NOT EXISTS idx_connector_authorizations_tenant
  ON control_plane.connector_authorizations(company_id, workspace_id);

ALTER TABLE control_plane.session_connector_grants
  ADD COLUMN IF NOT EXISTS company_id BIGINT;

ALTER TABLE control_plane.workspace_schedule_definitions
  ADD COLUMN IF NOT EXISTS company_id BIGINT;

ALTER TABLE control_plane.workspace_schedule_executions
  ADD COLUMN IF NOT EXISTS company_id BIGINT;
