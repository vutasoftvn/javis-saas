-- Rollback 009_memory_v2.sql
DROP TABLE IF EXISTS agent_memory.memory_embeddings CASCADE;

ALTER TABLE agent_memory.agent_memories
    DROP COLUMN IF EXISTS updated_at,
    DROP COLUMN IF EXISTS supersedes_memory_id,
    DROP COLUMN IF EXISTS valid_until,
    DROP COLUMN IF EXISTS valid_from,
    DROP COLUMN IF EXISTS status,
    DROP COLUMN IF EXISTS provenance,
    DROP COLUMN IF EXISTS source_event_id,
    DROP COLUMN IF EXISTS source_run_id,
    DROP COLUMN IF EXISTS sensitivity,
    DROP COLUMN IF EXISTS content_hash,
    DROP COLUMN IF EXISTS subject_id,
    DROP COLUMN IF EXISTS subject_type,
    DROP COLUMN IF EXISTS scope_id,
    DROP COLUMN IF EXISTS scope_type,
    DROP COLUMN IF EXISTS company_id,
    DROP COLUMN IF EXISTS tenant_id,
    DROP COLUMN IF EXISTS application_id;
