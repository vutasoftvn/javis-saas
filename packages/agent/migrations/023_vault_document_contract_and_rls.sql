-- Migration 023: Vault Document Metadata, Versioning, and Workspace Isolation
CREATE SCHEMA IF NOT EXISTS vault;

CREATE TABLE IF NOT EXISTS vault.documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id TEXT NOT NULL,
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    kind TEXT NOT NULL DEFAULT 'document',
    state TEXT NOT NULL DEFAULT 'DRAFT',
    current_version_id UUID NULL,
    knowledge_source_id UUID NULL,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, document_id)
);

CREATE TABLE IF NOT EXISTS vault.document_versions (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id TEXT NOT NULL,
    document_id UUID NOT NULL,
    object_ref JSONB NOT NULL,
    checksum_sha256 TEXT NOT NULL,
    size_bytes BIGINT NOT NULL CHECK (size_bytes >= 0),
    source_uri TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, version_id),
    FOREIGN KEY (workspace_id, document_id) REFERENCES vault.documents(workspace_id, document_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_vault_documents_workspace_state_updated ON vault.documents (workspace_id, state, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_vault_document_versions_workspace_doc ON vault.document_versions (workspace_id, document_id, created_at DESC);

-- RLS
ALTER TABLE vault.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE vault.document_versions ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE schemaname = 'vault' AND tablename = 'documents' AND policyname = 'vault_documents_workspace_isolation'
    ) THEN
        CREATE POLICY vault_documents_workspace_isolation ON vault.documents
            FOR ALL
            USING (workspace_id = current_setting('cosa.workspace_id', true) OR current_setting('cosa.workspace_id', true) IS NULL OR current_setting('cosa.workspace_id', true) = '');
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE schemaname = 'vault' AND tablename = 'document_versions' AND policyname = 'vault_document_versions_workspace_isolation'
    ) THEN
        CREATE POLICY vault_document_versions_workspace_isolation ON vault.document_versions
            FOR ALL
            USING (workspace_id = current_setting('cosa.workspace_id', true) OR current_setting('cosa.workspace_id', true) IS NULL OR current_setting('cosa.workspace_id', true) = '');
    END IF;
END $$;
