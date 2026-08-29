-- Migration: 010_knowledge_versioning_and_embeddings.sql
-- Description: source versioning + tách chunk_embeddings (Blueprint V2 §27).
-- Additive — không đụng cột/bảng cũ của migration 003. `knowledge.knowledge_chunks`
-- hiện tại có embedding inline (1 embedding/chunk) — vẫn giữ nguyên cho code
-- cũ; bảng chunk_embeddings mới cho phép nhiều embedding/chunk (đổi model mà
-- không mất embedding cũ, đúng yêu cầu Blueprint V2 §27).

ALTER TABLE knowledge.knowledge_sources
    ADD COLUMN IF NOT EXISTS application_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS scope_type VARCHAR(32),
    ADD COLUMN IF NOT EXISTS scope_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS authority_class VARCHAR(32) NOT NULL DEFAULT 'REFERENCE',
    ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT 'active';

-- Backfill scope generic từ workspace_id hiện có (giống pattern memory v2).
UPDATE knowledge.knowledge_sources
SET scope_type = COALESCE(scope_type, 'WORKSPACE'),
    scope_id = COALESCE(scope_id, workspace_id)
WHERE scope_type IS NULL;

CREATE TABLE IF NOT EXISTS knowledge.source_versions (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES knowledge.knowledge_sources(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    ingestion_run_id VARCHAR(64),
    parser_name VARCHAR(128),
    parser_version VARCHAR(32),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_knowledge_source_versions_source_version UNIQUE (source_id, version)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_source_versions_source ON knowledge.source_versions(source_id);

-- Backfill: mỗi source hiện có coi như đã có đúng 1 version (v1), content_hash
-- lấy từ content_hash của chunk đầu tiên nếu có, else NULL-safe placeholder.
INSERT INTO knowledge.source_versions (id, source_id, version, content_hash, created_at)
SELECT
    s.id || '_v1',
    s.id,
    1,
    COALESCE(
        (SELECT c.content_hash FROM knowledge.knowledge_chunks c WHERE c.source_id = s.id AND c.content_hash IS NOT NULL LIMIT 1),
        'unknown_backfill_hash'
    ),
    s.created_at
FROM knowledge.knowledge_sources s
ON CONFLICT (source_id, version) DO NOTHING;

-- Link chunk hiện có sang source_version v1 vừa backfill (nullable — chunk cũ
-- trước migration này không bắt buộc phải có source_version_id).
ALTER TABLE knowledge.knowledge_chunks
    ADD COLUMN IF NOT EXISTS source_version_id TEXT REFERENCES knowledge.source_versions(id),
    ADD COLUMN IF NOT EXISTS chunker_name VARCHAR(128),
    ADD COLUMN IF NOT EXISTS chunker_version VARCHAR(32);

UPDATE knowledge.knowledge_chunks c
SET source_version_id = c.source_id || '_v1'
WHERE c.source_version_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_source_version ON knowledge.knowledge_chunks(source_version_id);

-- Tách embedding thành bảng riêng — cho phép NHIỀU embedding/chunk (đổi model
-- không mất embedding cũ). Cột embedding inline trên knowledge_chunks (migration
-- 003) giữ nguyên cho code cũ, không xoá.
CREATE TABLE IF NOT EXISTS knowledge.chunk_embeddings (
    chunk_id TEXT NOT NULL REFERENCES knowledge.knowledge_chunks(id) ON DELETE CASCADE,
    embedding_model VARCHAR(128) NOT NULL,
    embedding_version VARCHAR(32) NOT NULL,
    dimensions INTEGER NOT NULL,
    embedding vector NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (chunk_id, embedding_model, embedding_version)
);
