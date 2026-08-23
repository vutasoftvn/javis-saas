-- Migration: 001_agent_memory_and_knowledge.sql
-- Description: Sets up schemas for Agent Memory (schema agent_memory) and Company Knowledge (schema knowledge)
-- Storage ownership: agent_memory owned by agentos/memory; knowledge owned by agentos/knowledge.

-- Enable pgvector extension (idempotent)
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- SCHEMA: agent_memory (Owned by agentos/memory)
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS agent_memory;

CREATE TABLE IF NOT EXISTS agent_memory.agent_memories (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    agent_key TEXT NOT NULL,
    kind TEXT NOT NULL, -- WORKING, EPISODIC, SEMANTIC, PROCEDURAL, ORGANIZATIONAL
    content TEXT NOT NULL,
    importance DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_memories_workspace_agent ON agent_memory.agent_memories(workspace_id, agent_key);
CREATE INDEX IF NOT EXISTS idx_agent_memories_workspace_kind ON agent_memory.agent_memories(workspace_id, kind);
CREATE INDEX IF NOT EXISTS idx_agent_memories_created_at ON agent_memory.agent_memories(created_at DESC);

-- ============================================================================
-- SCHEMA: knowledge (Owned by agentos/knowledge)
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS knowledge;

CREATE TABLE IF NOT EXISTS knowledge.knowledge_sources (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    title TEXT NOT NULL,
    source_type TEXT NOT NULL, -- DOC, WIKI, POLICY, MANUAL, SPEC, WEB_PAGE, FILE
    uri TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_knowledge_sources_workspace_id ON knowledge.knowledge_sources(workspace_id);

CREATE TABLE IF NOT EXISTS knowledge.knowledge_chunks (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES knowledge.knowledge_sources(id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector, -- pgvector arbitrary dimension or typed vector
    embedding_model TEXT,
    embedding_dimensions INTEGER,
    embedding_version TEXT,
    content_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_workspace_id ON knowledge.knowledge_chunks(workspace_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_source_id ON knowledge.knowledge_chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_content_hash ON knowledge.knowledge_chunks(content_hash);
