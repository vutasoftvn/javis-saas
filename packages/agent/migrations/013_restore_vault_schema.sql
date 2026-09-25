-- 013_restore_vault_schema.sql
--
-- Khôi phục schema `vault.*` mà baseline clean-slate 001 đã bỏ ra (002 cố ý
-- chưa khôi phục, xem comment đầu file 002). Code runtime vẫn dùng schema này:
--   * packages/agent/vault/repository.py  (PostgresVaultRepository — được
--     storage_factory chọn mỗi khi có AGENT_DATABASE_URL)
--   * packages/agent/knowledge/providers/postgres.py
--     (retrieve_authorized_citations JOIN vault.document_versions/documents/
--      document_access_grants)
-- Thiếu schema -> mọi route vault và mọi lượt tìm knowledge có lọc quyền trên
-- Postgres đều lỗi UndefinedTableError.
--
-- Cột lấy đúng theo câu SQL mà PostgresVaultRepository đọc/ghi. Chỉ Expand,
-- idempotent. RLS theo cùng mẫu với knowledge.* (cosa.workspace_id, fail-closed).

CREATE SCHEMA IF NOT EXISTS vault;

-- ============================================================================
-- vault.documents
-- ============================================================================
CREATE TABLE IF NOT EXISTS vault.documents (
  document_id           uuid PRIMARY KEY,
  workspace_id          text NOT NULL,
  title                 text NOT NULL,
  kind                  text NOT NULL DEFAULT 'document',
  -- Không CHECK state: vòng đời ingestion/purge có nhiều trạng thái
  -- (DRAFT, REVIEW_PENDING, PUBLISHED, ARCHIVED, PURGE_PENDING, PURGED, ...)
  -- do code quản lý; ràng buộc cứng ở DB dễ lệch khi thêm trạng thái mới.
  state                 text NOT NULL DEFAULT 'DRAFT',
  current_version_id    uuid,
  knowledge_source_id   uuid,
  created_by            text NOT NULL,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now(),
  classification        text NOT NULL DEFAULT 'INTERNAL'
    CHECK (classification IN ('PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED')),
  visibility            text NOT NULL DEFAULT 'PRIVATE'
    CHECK (visibility IN ('PRIVATE', 'WORKSPACE', 'ROLE')),
  access_policy_version integer NOT NULL DEFAULT 1,
  retention_until       timestamptz,
  legal_hold            boolean NOT NULL DEFAULT false,
  CONSTRAINT uq_vault_documents_workspace_document UNIQUE (workspace_id, document_id)
);
CREATE INDEX IF NOT EXISTS idx_vault_documents_workspace_updated
  ON vault.documents (workspace_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_vault_documents_workspace_state
  ON vault.documents (workspace_id, state);

-- ============================================================================
-- vault.document_versions  (immutable, append-only theo từng document)
-- ============================================================================
CREATE TABLE IF NOT EXISTS vault.document_versions (
  version_id      uuid PRIMARY KEY,
  workspace_id    text NOT NULL,
  document_id     uuid NOT NULL,
  object_ref      jsonb NOT NULL DEFAULT '{}'::jsonb,
  checksum_sha256 text NOT NULL,
  size_bytes      bigint NOT NULL CHECK (size_bytes >= 0),
  source_uri      text NOT NULL,
  created_by      text NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_vault_document_versions_workspace_version UNIQUE (workspace_id, version_id),
  -- FK composite kèm workspace_id: version không thể trỏ sang document của
  -- workspace khác.
  CONSTRAINT fk_vault_document_versions_document
    FOREIGN KEY (workspace_id, document_id)
    REFERENCES vault.documents (workspace_id, document_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_vault_document_versions_document
  ON vault.document_versions (workspace_id, document_id, created_at DESC);

-- ============================================================================
-- vault.document_access_grants
-- ============================================================================
CREATE TABLE IF NOT EXISTS vault.document_access_grants (
  grant_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id text NOT NULL,
  document_id  uuid NOT NULL,
  subject_type text NOT NULL CHECK (subject_type IN ('user', 'team', 'role')),
  subject_id   text NOT NULL,
  permission   text NOT NULL CHECK (permission IN ('read', 'review', 'publish', 'manage')),
  granted_by   text NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now(),
  -- Khớp ON CONFLICT (...) DO NOTHING trong PostgresVaultRepository.grant_access.
  CONSTRAINT uq_vault_document_access_grants_subject
    UNIQUE (workspace_id, document_id, subject_type, subject_id, permission),
  CONSTRAINT fk_vault_document_access_grants_document
    FOREIGN KEY (workspace_id, document_id)
    REFERENCES vault.documents (workspace_id, document_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_vault_document_access_grants_subject
  ON vault.document_access_grants (workspace_id, subject_type, subject_id);

-- ============================================================================
-- knowledge_sources -> vault.document_versions provenance FK
-- ============================================================================
-- NOT VALID: chỉ áp cho row mới/được sửa, không quét dữ liệu đã có (Expand-only,
-- không làm hỏng migrate trên DB đang có knowledge_sources trỏ version cũ).
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_knowledge_sources_vault_version'
  ) THEN
    ALTER TABLE knowledge.knowledge_sources
      ADD CONSTRAINT fk_knowledge_sources_vault_version
      FOREIGN KEY (vault_version_id) REFERENCES vault.document_versions (version_id)
      ON DELETE SET NULL NOT VALID;
  END IF;
END $$;

-- ============================================================================
-- Row-level security (fail-closed khi thiếu cosa.workspace_id)
-- ============================================================================
ALTER TABLE vault.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE vault.documents FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS vault_documents_workspace_isolation ON vault.documents;
CREATE POLICY vault_documents_workspace_isolation ON vault.documents
  USING ((workspace_id = current_setting('cosa.workspace_id'::text, true)))
  WITH CHECK ((workspace_id = current_setting('cosa.workspace_id'::text, true)));

ALTER TABLE vault.document_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE vault.document_versions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS vault_document_versions_workspace_isolation ON vault.document_versions;
CREATE POLICY vault_document_versions_workspace_isolation ON vault.document_versions
  USING ((workspace_id = current_setting('cosa.workspace_id'::text, true)))
  WITH CHECK ((workspace_id = current_setting('cosa.workspace_id'::text, true)));

ALTER TABLE vault.document_access_grants ENABLE ROW LEVEL SECURITY;
ALTER TABLE vault.document_access_grants FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS vault_document_access_grants_workspace_isolation ON vault.document_access_grants;
CREATE POLICY vault_document_access_grants_workspace_isolation ON vault.document_access_grants
  USING ((workspace_id = current_setting('cosa.workspace_id'::text, true)))
  WITH CHECK ((workspace_id = current_setting('cosa.workspace_id'::text, true)));
