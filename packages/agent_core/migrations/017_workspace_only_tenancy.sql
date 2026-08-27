-- Migration 017: Workspace-only tenancy
-- Description: Make workspace_id the sole tenant key for Agent Core tenant-owned records.
-- Removes company_id (never used) and redundant tenant_id from tenant-scoped tables.
-- After Task 7 (2026-08-27).

-- ============================================================================
-- Step 1: Validate workspace_id is never NULL in tenant-owned tables
-- ============================================================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM agent_core.runs WHERE workspace_id IS NULL LIMIT 1) THEN
        RAISE EXCEPTION 'Cannot migrate: agent_core.runs has NULL workspace_id';
    END IF;

    IF EXISTS (SELECT 1 FROM agent_conversation.conversations WHERE workspace_id IS NULL LIMIT 1) THEN
        RAISE EXCEPTION 'Cannot migrate: agent_conversation.conversations has NULL workspace_id';
    END IF;

    IF EXISTS (SELECT 1 FROM agent_memory.agent_memories WHERE workspace_id IS NULL LIMIT 1) THEN
        RAISE EXCEPTION 'Cannot migrate: agent_memory.agent_memories has NULL workspace_id';
    END IF;

    IF EXISTS (SELECT 1 FROM agent_artifact.workspace_artifacts WHERE workspace_id IS NULL LIMIT 1) THEN
        RAISE EXCEPTION 'Cannot migrate: agent_artifact.workspace_artifacts has NULL workspace_id';
    END IF;
END $$;

-- ============================================================================
-- Step 2: Remove redundant company_id and tenant_id from agent_core.runs
-- ============================================================================

DROP INDEX IF EXISTS idx_agent_core_runs_tenant;
DROP INDEX IF EXISTS idx_agent_core_runs_company_id;

ALTER TABLE agent_core.runs
    DROP COLUMN IF EXISTS tenant_id,
    DROP COLUMN IF EXISTS company_id;

-- ============================================================================
-- Step 3: Remove redundant company_id and tenant_id from agent_conversation.conversations
-- ============================================================================

DROP INDEX IF EXISTS idx_agent_conversation_conversations_tenant;
DROP INDEX IF EXISTS idx_agent_conversation_conversations_company_id;

ALTER TABLE agent_conversation.conversations
    DROP COLUMN IF EXISTS tenant_id,
    DROP COLUMN IF EXISTS company_id;

-- ============================================================================
-- Step 4: Remove redundant company_id and tenant_id from agent_memory.agent_memories
-- ============================================================================

DROP INDEX IF EXISTS idx_agent_memories_tenant_status;
DROP INDEX IF EXISTS idx_agent_memories_company_id;

ALTER TABLE agent_memory.agent_memories
    DROP COLUMN IF EXISTS tenant_id,
    DROP COLUMN IF EXISTS company_id;

-- ============================================================================
-- Step 5: Remove company_id from agent_artifact.workspace_artifacts
-- ============================================================================

DROP INDEX IF EXISTS idx_workspace_artifacts_lookup;

-- Recreate index without company_id
CREATE INDEX IF NOT EXISTS idx_workspace_artifacts_lookup
    ON agent_artifact.workspace_artifacts(workspace_id, conversation_id, created_at DESC);

ALTER TABLE agent_artifact.workspace_artifacts
    DROP COLUMN IF EXISTS company_id;

-- ============================================================================
-- Final: Ensure workspace_id is NOT NULL where it matters
-- ============================================================================

ALTER TABLE agent_core.runs
    ALTER COLUMN workspace_id SET NOT NULL;

ALTER TABLE agent_conversation.conversations
    ALTER COLUMN workspace_id SET NOT NULL;

ALTER TABLE agent_memory.agent_memories
    ALTER COLUMN workspace_id SET NOT NULL;

ALTER TABLE agent_artifact.workspace_artifacts
    ALTER COLUMN workspace_id SET NOT NULL;
