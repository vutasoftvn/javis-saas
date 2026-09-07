-- Migration 026 Rollback
DROP POLICY IF EXISTS vault_document_access_grants_workspace_isolation ON vault.document_access_grants;
DROP POLICY IF EXISTS vault_document_versions_workspace_isolation ON vault.document_versions;
DROP POLICY IF EXISTS vault_documents_workspace_isolation ON vault.documents;

ALTER TABLE vault.document_versions NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vault.documents NO FORCE ROW LEVEL SECURITY;

-- Khôi phục policy bypass gốc của migration 023.
CREATE POLICY vault_documents_workspace_isolation ON vault.documents
    FOR ALL
    USING (workspace_id = current_setting('cosa.workspace_id', true) OR current_setting('cosa.workspace_id', true) IS NULL OR current_setting('cosa.workspace_id', true) = '');
CREATE POLICY vault_document_versions_workspace_isolation ON vault.document_versions
    FOR ALL
    USING (workspace_id = current_setting('cosa.workspace_id', true) OR current_setting('cosa.workspace_id', true) IS NULL OR current_setting('cosa.workspace_id', true) = '');

DROP TABLE IF EXISTS vault.document_access_grants;

ALTER TABLE vault.document_versions
    DROP CONSTRAINT IF EXISTS chk_vault_document_versions_visibility,
    DROP CONSTRAINT IF EXISTS chk_vault_document_versions_classification,
    DROP COLUMN IF EXISTS legal_hold,
    DROP COLUMN IF EXISTS retention_until,
    DROP COLUMN IF EXISTS access_policy_version,
    DROP COLUMN IF EXISTS visibility,
    DROP COLUMN IF EXISTS classification;

ALTER TABLE vault.documents
    DROP CONSTRAINT IF EXISTS chk_vault_documents_visibility,
    DROP CONSTRAINT IF EXISTS chk_vault_documents_classification,
    DROP COLUMN IF EXISTS legal_hold,
    DROP COLUMN IF EXISTS retention_until,
    DROP COLUMN IF EXISTS access_policy_version,
    DROP COLUMN IF EXISTS visibility,
    DROP COLUMN IF EXISTS classification;
