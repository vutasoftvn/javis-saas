-- Migration 026: Vault access policy (grants + classification/visibility) và
-- RLS fail-closed thật (Task 2, plan local-first-enterprise-knowledge).
--
-- Migration 023 đã tạo vault.documents/document_versions với RLS BYPASS khi
-- `cosa.workspace_id` thiếu (`OR current_setting(...) IS NULL OR ... = ''`) —
-- KHÔNG fail-closed đúng nghĩa (một transaction quên set_config sẽ đọc được
-- TOÀN BỘ workspace). Migration này DROP policy cũ, tạo lại chặt (không có
-- nhánh bypass) và bật FORCE ROW LEVEL SECURITY để chủ sở hữu bảng
-- (agent_migrator) cũng không tự động bypass.

-- ── Cột classification/visibility/access_policy_version/retention/legal_hold ──

ALTER TABLE vault.documents
    ADD COLUMN IF NOT EXISTS classification TEXT NOT NULL DEFAULT 'INTERNAL',
    ADD COLUMN IF NOT EXISTS visibility TEXT NOT NULL DEFAULT 'PRIVATE',
    ADD COLUMN IF NOT EXISTS access_policy_version INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS retention_until TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS legal_hold BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE vault.documents
    ADD CONSTRAINT chk_vault_documents_classification
        CHECK (classification IN ('PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED'));

ALTER TABLE vault.documents
    ADD CONSTRAINT chk_vault_documents_visibility
        CHECK (visibility IN ('PRIVATE', 'WORKSPACE', 'ROLE'));

ALTER TABLE vault.document_versions
    ADD COLUMN IF NOT EXISTS classification TEXT NOT NULL DEFAULT 'INTERNAL',
    ADD COLUMN IF NOT EXISTS visibility TEXT NOT NULL DEFAULT 'PRIVATE',
    ADD COLUMN IF NOT EXISTS access_policy_version INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS retention_until TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS legal_hold BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE vault.document_versions
    ADD CONSTRAINT chk_vault_document_versions_classification
        CHECK (classification IN ('PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED'));

ALTER TABLE vault.document_versions
    ADD CONSTRAINT chk_vault_document_versions_visibility
        CHECK (visibility IN ('PRIVATE', 'WORKSPACE', 'ROLE'));

-- ── vault.document_access_grants — ACL tường minh cho document/subject/permission ──

CREATE TABLE IF NOT EXISTS vault.document_access_grants (
    grant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id TEXT NOT NULL,
    document_id UUID NOT NULL,
    subject_type TEXT NOT NULL CHECK (subject_type IN ('user', 'team', 'role')),
    subject_id TEXT NOT NULL,
    permission TEXT NOT NULL CHECK (permission IN ('read', 'review', 'publish', 'manage')),
    granted_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, document_id, subject_type, subject_id, permission),
    FOREIGN KEY (workspace_id, document_id) REFERENCES vault.documents(workspace_id, document_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_vault_access_grants_workspace_doc
    ON vault.document_access_grants (workspace_id, document_id);
CREATE INDEX IF NOT EXISTS idx_vault_access_grants_workspace_subject
    ON vault.document_access_grants (workspace_id, subject_type, subject_id);

-- ── RLS fail-closed thật cho toàn bộ vault.* ──

ALTER TABLE vault.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE vault.documents FORCE ROW LEVEL SECURITY;
ALTER TABLE vault.document_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE vault.document_versions FORCE ROW LEVEL SECURITY;
ALTER TABLE vault.document_access_grants ENABLE ROW LEVEL SECURITY;
ALTER TABLE vault.document_access_grants FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS vault_documents_workspace_isolation ON vault.documents;
CREATE POLICY vault_documents_workspace_isolation ON vault.documents
    FOR ALL
    USING (workspace_id = current_setting('cosa.workspace_id', true))
    WITH CHECK (workspace_id = current_setting('cosa.workspace_id', true));

DROP POLICY IF EXISTS vault_document_versions_workspace_isolation ON vault.document_versions;
CREATE POLICY vault_document_versions_workspace_isolation ON vault.document_versions
    FOR ALL
    USING (workspace_id = current_setting('cosa.workspace_id', true))
    WITH CHECK (workspace_id = current_setting('cosa.workspace_id', true));

DROP POLICY IF EXISTS vault_document_access_grants_workspace_isolation ON vault.document_access_grants;
CREATE POLICY vault_document_access_grants_workspace_isolation ON vault.document_access_grants
    FOR ALL
    USING (workspace_id = current_setting('cosa.workspace_id', true))
    WITH CHECK (workspace_id = current_setting('cosa.workspace_id', true));
