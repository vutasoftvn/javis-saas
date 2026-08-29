-- Rollback 017_workspace_only_tenancy.sql
ALTER TABLE agent.runs
    ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS company_id VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_agent_runs_tenant ON agent.runs(tenant_id);

ALTER TABLE agent_conversation.conversations
    ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS company_id VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_agent_conversation_conversations_tenant ON agent_conversation.conversations(tenant_id);

ALTER TABLE agent_memory.agent_memories
    ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS company_id VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_agent_memories_tenant_status ON agent_memory.agent_memories(tenant_id, status);

ALTER TABLE agent_artifact.workspace_artifacts
    ADD COLUMN IF NOT EXISTS company_id VARCHAR(64);
