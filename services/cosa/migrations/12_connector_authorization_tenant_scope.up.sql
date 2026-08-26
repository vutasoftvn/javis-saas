-- Migration 12: Tenant scope cho connector_authorizations — vá lỗ hổng
-- cross-tenant: registerConnectorAuthorization trước đây chỉ query theo
-- installation_id, không xác nhận installation thuộc đúng company/workspace
-- của caller.
ALTER TABLE control_plane.connector_authorizations
  ADD COLUMN company_id TEXT NOT NULL DEFAULT '',
  ADD COLUMN workspace_id TEXT NOT NULL DEFAULT '';

UPDATE control_plane.connector_authorizations ca
SET company_id = wci.company_id, workspace_id = wci.workspace_id
FROM control_plane.workspace_connector_installations wci
WHERE ca.installation_id = wci.id;

ALTER TABLE control_plane.connector_authorizations
  ALTER COLUMN company_id DROP DEFAULT,
  ALTER COLUMN workspace_id DROP DEFAULT;

CREATE INDEX IF NOT EXISTS idx_connector_authorizations_tenant
  ON control_plane.connector_authorizations(company_id, workspace_id);
