-- 002_restore_knowledge_artifact_automation.sql
--
-- Startup Core Task-2 reconciliation (agent plane). The clean-slate 001 baseline
-- squash dropped three subsystems that packages/agent runtime code + tests still
-- depend on:
--
--   * agent_artifact.workspace_artifacts   (packages/agent/artifacts/postgres.py)
--   * knowledge.*                          (packages/agent/knowledge/*)
--   * agent.automation_run_manifests +
--     agent.approvals.manifest_hash        (packages/agent/capabilities/approval_service.py,
--                                            runs/repository.py — from the deleted
--                                            003_cosa_automation_mvp migration)
--
-- Flat post-017 (workspace-only tenancy) shape, taken from the historical
-- migrations 003/010/015/016/027 + 003_cosa_automation_mvp. The
-- knowledge_sources -> vault.document_versions FK is intentionally NOT restored
-- (vault schema is out of this slice); vault_document_id / vault_version_id stay
-- as bare columns. Expand-only, idempotent.

CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- agent.approvals.manifest_hash + agent.automation_run_manifests
-- (from the deleted 003_cosa_automation_mvp)
-- ============================================================================
ALTER TABLE agent.approvals ADD COLUMN IF NOT EXISTS manifest_hash TEXT;

CREATE TABLE IF NOT EXISTS agent.automation_run_manifests (
  run_id        TEXT PRIMARY KEY REFERENCES agent.runs(run_id) ON DELETE CASCADE,
  manifest_hash TEXT NOT NULL,
  manifest_json JSONB NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_automation_run_manifests_hash
  ON agent.automation_run_manifests (manifest_hash);

-- ============================================================================
-- agent_artifact.workspace_artifacts  (016 + 017 delta)
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS agent_artifact;

CREATE TABLE IF NOT EXISTS agent_artifact.workspace_artifacts (
    artifact_id        character varying(64) PRIMARY KEY,
    workspace_id       character varying(64) NOT NULL,
    conversation_id    character varying(64) NOT NULL,
    run_id             character varying(64),
    source_message_id  character varying(64),
    artifact_kind      character varying(32) NOT NULL,
    display_name       character varying(255) NOT NULL,
    media_type         character varying(128) NOT NULL,
    object_ref         character varying(512) NOT NULL,
    checksum           character varying(128),
    size_bytes         bigint DEFAULT 0 NOT NULL,
    status             character varying(32) DEFAULT 'available'::character varying NOT NULL,
    input_artifact_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    created_at         timestamp with time zone DEFAULT now() NOT NULL,
    archived_at        timestamp with time zone,
    CONSTRAINT chk_workspace_artifact_kind CHECK (((artifact_kind)::text = ANY ((ARRAY['assistant_output'::character varying, 'report'::character varying, 'table'::character varying, 'file_export'::character varying])::text[]))),
    CONSTRAINT chk_workspace_artifact_status CHECK (((status)::text = ANY ((ARRAY['available'::character varying, 'failed'::character varying, 'archived'::character varying])::text[])))
);
CREATE INDEX IF NOT EXISTS idx_workspace_artifacts_lookup
    ON agent_artifact.workspace_artifacts (workspace_id, conversation_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_workspace_artifacts_run
    ON agent_artifact.workspace_artifacts (run_id);

-- ============================================================================
-- knowledge.*  (003 base + 010 versioning/embeddings + 015 snapshots + 027 RLS)
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS knowledge;

CREATE TABLE IF NOT EXISTS knowledge.knowledge_sources (
    id                    text PRIMARY KEY,
    workspace_id          text NOT NULL,
    title                 text NOT NULL,
    source_type           text NOT NULL,
    uri                   text,
    created_at            timestamp with time zone DEFAULT now() NOT NULL,
    metadata              jsonb DEFAULT '{}'::jsonb NOT NULL,
    application_id        character varying(64),
    tenant_id             character varying(64),
    scope_type            character varying(32),
    scope_id              character varying(64),
    authority_class       character varying(32) DEFAULT 'REFERENCE'::character varying NOT NULL,
    status                character varying(32) DEFAULT 'active'::character varying NOT NULL,
    vault_document_id     uuid,
    vault_version_id      uuid,
    access_policy_version integer
);
CREATE INDEX IF NOT EXISTS idx_knowledge_sources_workspace_id ON knowledge.knowledge_sources (workspace_id);

CREATE TABLE IF NOT EXISTS knowledge.source_versions (
    id               text PRIMARY KEY,
    source_id        text NOT NULL REFERENCES knowledge.knowledge_sources(id) ON DELETE CASCADE,
    version          integer NOT NULL,
    content_hash     character varying(64) NOT NULL,
    ingestion_run_id character varying(64),
    parser_name      character varying(128),
    parser_version   character varying(32),
    created_at       timestamp with time zone DEFAULT now() NOT NULL,
    workspace_id     text NOT NULL,
    CONSTRAINT uq_knowledge_source_versions_source_version UNIQUE (source_id, version)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_source_versions_source ON knowledge.source_versions (source_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_source_versions_workspace ON knowledge.source_versions (workspace_id);

CREATE TABLE IF NOT EXISTS knowledge.knowledge_chunks (
    id                   text PRIMARY KEY,
    source_id            text NOT NULL REFERENCES knowledge.knowledge_sources(id) ON DELETE CASCADE,
    workspace_id         text NOT NULL,
    chunk_index          integer NOT NULL,
    content              text NOT NULL,
    embedding            public.vector,
    embedding_model      text,
    embedding_dimensions integer,
    embedding_version    text,
    content_hash         text,
    created_at           timestamp with time zone DEFAULT now() NOT NULL,
    metadata             jsonb DEFAULT '{}'::jsonb NOT NULL,
    source_version_id    text REFERENCES knowledge.source_versions(id),
    chunker_name         character varying(128),
    chunker_version      character varying(32)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_workspace_id ON knowledge.knowledge_chunks (workspace_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_source_id ON knowledge.knowledge_chunks (source_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_content_hash ON knowledge.knowledge_chunks (content_hash);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_source_version ON knowledge.knowledge_chunks (source_version_id);

CREATE TABLE IF NOT EXISTS knowledge.chunk_embeddings (
    chunk_id          text NOT NULL REFERENCES knowledge.knowledge_chunks(id) ON DELETE CASCADE,
    embedding_model   character varying(128) NOT NULL,
    embedding_version character varying(32) NOT NULL,
    dimensions        integer NOT NULL,
    embedding         public.vector NOT NULL,
    created_at        timestamp with time zone DEFAULT now() NOT NULL,
    workspace_id      text NOT NULL,
    PRIMARY KEY (chunk_id, embedding_model, embedding_version)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunk_embeddings_workspace ON knowledge.chunk_embeddings (workspace_id);

CREATE TABLE IF NOT EXISTS knowledge.snapshots (
    snapshot_id     character varying(64) NOT NULL,
    version         character varying(32) NOT NULL,
    workspace_id    character varying(64) NOT NULL,
    definition_hash character varying(64) NOT NULL,
    content         jsonb NOT NULL,
    created_at      timestamp with time zone DEFAULT now() NOT NULL,
    PRIMARY KEY (snapshot_id, version),
    CONSTRAINT uq_knowledge_snapshots_hash UNIQUE (snapshot_id, version, definition_hash)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_snapshots_workspace ON knowledge.snapshots (workspace_id);

-- RLS (from 027) — enforced when the runtime connects as agent_app and sets
-- cosa.workspace_id; the migrator/superuser bypasses it.
ALTER TABLE knowledge.knowledge_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge.knowledge_sources FORCE ROW LEVEL SECURITY;
CREATE POLICY knowledge_sources_workspace_isolation ON knowledge.knowledge_sources
  USING ((workspace_id = current_setting('cosa.workspace_id'::text, true)))
  WITH CHECK ((workspace_id = current_setting('cosa.workspace_id'::text, true)));

ALTER TABLE knowledge.source_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge.source_versions FORCE ROW LEVEL SECURITY;
CREATE POLICY knowledge_source_versions_workspace_isolation ON knowledge.source_versions
  USING ((workspace_id = current_setting('cosa.workspace_id'::text, true)))
  WITH CHECK ((workspace_id = current_setting('cosa.workspace_id'::text, true)));

ALTER TABLE knowledge.knowledge_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge.knowledge_chunks FORCE ROW LEVEL SECURITY;
CREATE POLICY knowledge_chunks_workspace_isolation ON knowledge.knowledge_chunks
  USING ((workspace_id = current_setting('cosa.workspace_id'::text, true)))
  WITH CHECK ((workspace_id = current_setting('cosa.workspace_id'::text, true)));

ALTER TABLE knowledge.chunk_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge.chunk_embeddings FORCE ROW LEVEL SECURITY;
CREATE POLICY knowledge_chunk_embeddings_workspace_isolation ON knowledge.chunk_embeddings
  USING ((workspace_id = current_setting('cosa.workspace_id'::text, true)))
  WITH CHECK ((workspace_id = current_setting('cosa.workspace_id'::text, true)));
