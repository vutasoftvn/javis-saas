-- Migration: 009_memory_v2.sql
-- Description: Generic scope/provenance/lifecycle cho agent_memory.agent_memories
-- (Blueprint V2 §26) + agent_memory.memory_embeddings (memory hiện tại chưa có
-- khả năng embedding/similarity search nào). Additive — backfill từ metadata
-- JSONB đã pack sẵn (packages/agent/memory/providers/postgres.py trước
-- đây pack tenant_id/company_id/sensitivity/provenance_run_id/expires_at vào
-- metadata để tránh mở migration mới "trong cùng epic" — nay mở migration
-- riêng, promote các field đó thành cột thật + thêm field Blueprint V2 còn thiếu).

ALTER TABLE agent_memory.agent_memories
    ADD COLUMN IF NOT EXISTS application_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS company_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS scope_type VARCHAR(32),
    ADD COLUMN IF NOT EXISTS scope_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS subject_type VARCHAR(32),
    ADD COLUMN IF NOT EXISTS subject_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64),
    ADD COLUMN IF NOT EXISTS sensitivity VARCHAR(32) NOT NULL DEFAULT 'normal',
    ADD COLUMN IF NOT EXISTS source_run_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS source_event_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS provenance JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    ADD COLUMN IF NOT EXISTS valid_from TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS valid_until TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS supersedes_memory_id TEXT REFERENCES agent_memory.agent_memories(id),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

-- Backfill từ field đã pack trong metadata (PostgresMemoryStore._pack_metadata
-- cũ) — chỉ chạy 1 lần, idempotent nhờ điều kiện cột đích còn NULL.
UPDATE agent_memory.agent_memories
SET tenant_id = COALESCE(tenant_id, metadata->>'_tenant_id'),
    company_id = COALESCE(company_id, metadata->>'_company_id'),
    sensitivity = CASE WHEN metadata ? '_sensitivity' THEN metadata->>'_sensitivity' ELSE sensitivity END,
    source_run_id = COALESCE(source_run_id, metadata->>'_provenance_run_id'),
    valid_until = COALESCE(valid_until, NULLIF(metadata->>'_expires_at', '')::timestamptz)
WHERE metadata ? '_tenant_id' OR metadata ? '_company_id' OR metadata ? '_sensitivity'
   OR metadata ? '_provenance_run_id' OR metadata ? '_expires_at';

-- workspace_id hiện có là scope cụ thể duy nhất -> backfill scope_type/scope_id
-- generic tương ứng, giữ workspace_id nguyên vẹn (không phá cột cũ).
UPDATE agent_memory.agent_memories
SET scope_type = COALESCE(scope_type, 'WORKSPACE'),
    scope_id = COALESCE(scope_id, workspace_id)
WHERE scope_type IS NULL;

CREATE INDEX IF NOT EXISTS idx_agent_memories_tenant_status ON agent_memory.agent_memories(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_agent_memories_scope ON agent_memory.agent_memories(scope_type, scope_id);
CREATE INDEX IF NOT EXISTS idx_agent_memories_supersedes ON agent_memory.agent_memories(supersedes_memory_id);

CREATE TABLE IF NOT EXISTS agent_memory.memory_embeddings (
    memory_id TEXT NOT NULL REFERENCES agent_memory.agent_memories(id) ON DELETE CASCADE,
    embedding_model VARCHAR(128) NOT NULL,
    embedding_version VARCHAR(32) NOT NULL,
    dimensions INTEGER NOT NULL,
    embedding vector NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (memory_id, embedding_model, embedding_version)
);
