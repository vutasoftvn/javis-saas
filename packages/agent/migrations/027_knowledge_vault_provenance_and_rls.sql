-- Migration 027: Knowledge → Vault provenance + RLS fail-closed cho toàn bộ
-- schema knowledge (Task 2, plan local-first-enterprise-knowledge).
--
-- knowledge.* trước đây KHÔNG có RLS nào (chỉ lọc bằng WHERE workspace_id ở
-- tầng application — một query quên điều kiện đó đọc được toàn bộ workspace
-- khác). Migration này thêm RLS fail-closed (không nhánh bypass) + FORCE cho
-- knowledge_sources, knowledge_chunks, source_versions, chunk_embeddings —
-- 2 bảng sau không có sẵn workspace_id nên denormalize thêm (cùng pattern đã
-- dùng cho knowledge_chunks từ migration 003), backfill từ bảng cha.
--
-- knowledge_sources.vault_document_id/vault_version_id là bằng chứng
-- provenance: một knowledge source đã publish PHẢI trỏ về đúng 1 Vault
-- document version cụ thể (không suy diễn ngầm) — publish_knowledge_source
-- (Task 5/8) phải set các cột này, repository publish reject nếu thiếu.

ALTER TABLE knowledge.knowledge_sources
    ADD COLUMN IF NOT EXISTS vault_document_id UUID,
    ADD COLUMN IF NOT EXISTS vault_version_id UUID,
    ADD COLUMN IF NOT EXISTS access_policy_version INTEGER;

ALTER TABLE knowledge.knowledge_sources
    ADD CONSTRAINT fk_knowledge_sources_vault_version
        FOREIGN KEY (vault_version_id) REFERENCES vault.document_versions(version_id);

-- ── Denormalize workspace_id cho source_versions/chunk_embeddings (RLS) ──

ALTER TABLE knowledge.source_versions
    ADD COLUMN IF NOT EXISTS workspace_id TEXT;

UPDATE knowledge.source_versions sv
SET workspace_id = ks.workspace_id
FROM knowledge.knowledge_sources ks
WHERE sv.source_id = ks.id AND sv.workspace_id IS NULL;

ALTER TABLE knowledge.source_versions
    ALTER COLUMN workspace_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_knowledge_source_versions_workspace
    ON knowledge.source_versions(workspace_id);

ALTER TABLE knowledge.chunk_embeddings
    ADD COLUMN IF NOT EXISTS workspace_id TEXT;

UPDATE knowledge.chunk_embeddings ce
SET workspace_id = kc.workspace_id
FROM knowledge.knowledge_chunks kc
WHERE ce.chunk_id = kc.id AND ce.workspace_id IS NULL;

ALTER TABLE knowledge.chunk_embeddings
    ALTER COLUMN workspace_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_knowledge_chunk_embeddings_workspace
    ON knowledge.chunk_embeddings(workspace_id);

-- ── RLS fail-closed cho toàn bộ schema knowledge ──

ALTER TABLE knowledge.knowledge_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge.knowledge_sources FORCE ROW LEVEL SECURITY;
ALTER TABLE knowledge.knowledge_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge.knowledge_chunks FORCE ROW LEVEL SECURITY;
ALTER TABLE knowledge.source_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge.source_versions FORCE ROW LEVEL SECURITY;
ALTER TABLE knowledge.chunk_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge.chunk_embeddings FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS knowledge_sources_workspace_isolation ON knowledge.knowledge_sources;
CREATE POLICY knowledge_sources_workspace_isolation ON knowledge.knowledge_sources
    FOR ALL
    USING (workspace_id = current_setting('cosa.workspace_id', true))
    WITH CHECK (workspace_id = current_setting('cosa.workspace_id', true));

DROP POLICY IF EXISTS knowledge_chunks_workspace_isolation ON knowledge.knowledge_chunks;
CREATE POLICY knowledge_chunks_workspace_isolation ON knowledge.knowledge_chunks
    FOR ALL
    USING (workspace_id = current_setting('cosa.workspace_id', true))
    WITH CHECK (workspace_id = current_setting('cosa.workspace_id', true));

DROP POLICY IF EXISTS knowledge_source_versions_workspace_isolation ON knowledge.source_versions;
CREATE POLICY knowledge_source_versions_workspace_isolation ON knowledge.source_versions
    FOR ALL
    USING (workspace_id = current_setting('cosa.workspace_id', true))
    WITH CHECK (workspace_id = current_setting('cosa.workspace_id', true));

DROP POLICY IF EXISTS knowledge_chunk_embeddings_workspace_isolation ON knowledge.chunk_embeddings;
CREATE POLICY knowledge_chunk_embeddings_workspace_isolation ON knowledge.chunk_embeddings
    FOR ALL
    USING (workspace_id = current_setting('cosa.workspace_id', true))
    WITH CHECK (workspace_id = current_setting('cosa.workspace_id', true));
