-- Migration 023 Rollback
DROP POLICY IF EXISTS vault_document_versions_workspace_isolation ON vault.document_versions;
DROP POLICY IF EXISTS vault_documents_workspace_isolation ON vault.documents;
DROP TABLE IF EXISTS vault.document_versions;
DROP TABLE IF EXISTS vault.documents;
