-- Rollback 010_knowledge_versioning_and_embeddings.sql
DROP TABLE IF EXISTS knowledge.chunk_embeddings CASCADE;

ALTER TABLE knowledge.knowledge_chunks
    DROP COLUMN IF EXISTS chunker_version,
    DROP COLUMN IF EXISTS chunker_name,
    DROP COLUMN IF EXISTS source_version_id;

DROP TABLE IF EXISTS knowledge.source_versions CASCADE;

ALTER TABLE knowledge.knowledge_sources
    DROP COLUMN IF EXISTS status,
    DROP COLUMN IF EXISTS authority_class,
    DROP COLUMN IF EXISTS scope_id,
    DROP COLUMN IF EXISTS scope_type,
    DROP COLUMN IF EXISTS tenant_id,
    DROP COLUMN IF EXISTS application_id;
