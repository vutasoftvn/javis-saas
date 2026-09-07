-- Migration 027 Rollback
DROP POLICY IF EXISTS knowledge_chunk_embeddings_workspace_isolation ON knowledge.chunk_embeddings;
DROP POLICY IF EXISTS knowledge_source_versions_workspace_isolation ON knowledge.source_versions;
DROP POLICY IF EXISTS knowledge_chunks_workspace_isolation ON knowledge.knowledge_chunks;
DROP POLICY IF EXISTS knowledge_sources_workspace_isolation ON knowledge.knowledge_sources;

ALTER TABLE knowledge.chunk_embeddings NO FORCE ROW LEVEL SECURITY;
ALTER TABLE knowledge.chunk_embeddings DISABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge.source_versions NO FORCE ROW LEVEL SECURITY;
ALTER TABLE knowledge.source_versions DISABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge.knowledge_chunks NO FORCE ROW LEVEL SECURITY;
ALTER TABLE knowledge.knowledge_chunks DISABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge.knowledge_sources NO FORCE ROW LEVEL SECURITY;
ALTER TABLE knowledge.knowledge_sources DISABLE ROW LEVEL SECURITY;

DROP INDEX IF EXISTS knowledge.idx_knowledge_chunk_embeddings_workspace;
ALTER TABLE knowledge.chunk_embeddings DROP COLUMN IF EXISTS workspace_id;

DROP INDEX IF EXISTS knowledge.idx_knowledge_source_versions_workspace;
ALTER TABLE knowledge.source_versions DROP COLUMN IF EXISTS workspace_id;

ALTER TABLE knowledge.knowledge_sources
    DROP CONSTRAINT IF EXISTS fk_knowledge_sources_vault_version,
    DROP COLUMN IF EXISTS access_policy_version,
    DROP COLUMN IF EXISTS vault_version_id,
    DROP COLUMN IF EXISTS vault_document_id;
