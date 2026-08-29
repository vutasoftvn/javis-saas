-- Migration: 006_conversation_substrate.sql
-- Description: Durable conversation/message substrate, thay thế in-memory globals
-- (_conversations, _messages, _pending_runs) tại apps/cosa/api/routes.py.
-- Theo COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md Phần C.1.

CREATE SCHEMA IF NOT EXISTS agent_conversation;

-- 1. agent_conversation.conversations
CREATE TABLE IF NOT EXISTS agent_conversation.conversations (
    conversation_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64),
    company_id VARCHAR(64),
    workspace_id VARCHAR(64),
    created_by_principal VARCHAR(128) NOT NULL,
    title VARCHAR(256) NOT NULL DEFAULT 'New Conversation',
    active_agent_profile VARCHAR(128),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_agent_conversation_conversations_workspace
    ON agent_conversation.conversations(workspace_id, archived_at);
CREATE INDEX IF NOT EXISTS idx_agent_conversation_conversations_tenant
    ON agent_conversation.conversations(tenant_id);

-- 2. agent_conversation.messages
CREATE TABLE IF NOT EXISTS agent_conversation.messages (
    message_id VARCHAR(64) PRIMARY KEY,
    conversation_id VARCHAR(64) NOT NULL REFERENCES agent_conversation.conversations(conversation_id) ON DELETE CASCADE,
    sequence_no BIGSERIAL,
    role VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    run_id VARCHAR(64),
    parent_message_id VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'completed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_agent_conversation_messages_conv_seq UNIQUE (conversation_id, sequence_no)
);

CREATE INDEX IF NOT EXISTS idx_agent_conversation_messages_conv
    ON agent_conversation.messages(conversation_id, sequence_no);
CREATE INDEX IF NOT EXISTS idx_agent_conversation_messages_run
    ON agent_conversation.messages(run_id);

-- 3. agent_conversation.message_attachments
CREATE TABLE IF NOT EXISTS agent_conversation.message_attachments (
    attachment_id VARCHAR(64) PRIMARY KEY,
    message_id VARCHAR(64) NOT NULL REFERENCES agent_conversation.messages(message_id) ON DELETE CASCADE,
    object_ref TEXT NOT NULL,
    media_type VARCHAR(128) NOT NULL,
    file_name VARCHAR(256) NOT NULL,
    size BIGINT NOT NULL DEFAULT 0,
    checksum VARCHAR(128),
    knowledge_ingest_status VARCHAR(32) NOT NULL DEFAULT 'COMPLETED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_conversation_attachments_message
    ON agent_conversation.message_attachments(message_id);
