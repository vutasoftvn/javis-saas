-- SP-A: restore control_plane.document_ingestion* dropped by the 001 cosa squash.
-- Flattened from deleted 15_document_ingestions.up.sql (git ref 81461673^),
-- matching control-plane-schema.ts. Expand-only, idempotent. Audit id is
-- GENERATED IDENTITY (Drizzle) not BIGSERIAL (old migration).
CREATE SCHEMA IF NOT EXISTS control_plane;

CREATE TABLE IF NOT EXISTS control_plane.document_ingestions (
  id                    TEXT PRIMARY KEY,
  workspace_id          TEXT NOT NULL,
  created_by            TEXT NOT NULL,
  original_filename     TEXT NOT NULL,
  declared_media_type   TEXT NOT NULL,
  detected_media_type   TEXT,
  size_bytes            BIGINT,
  source_sha256         TEXT,
  original_object_key   TEXT,
  state                 TEXT NOT NULL CHECK (state IN ('UPLOADING', 'QUARANTINED', 'QUEUED', 'VALIDATING', 'CONVERTING', 'REVIEW_PENDING', 'PUBLISHED', 'REJECTED', 'FAILED', 'EXPIRED')),
  idempotency_key       TEXT NOT NULL,
  knowledge_source_id   TEXT,
  converter_spec_id     TEXT,
  manifest_json         JSONB,
  failure_code          TEXT,
  claim_token           TEXT,
  created_at            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  UNIQUE (workspace_id, created_by, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_document_ingestions_workspace_state_created
  ON control_plane.document_ingestions (workspace_id, state, created_at DESC);

CREATE TABLE IF NOT EXISTS control_plane.document_ingestion_audit_events (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ingestion_id  TEXT NOT NULL REFERENCES control_plane.document_ingestions(id) ON DELETE CASCADE,
  actor_kind    TEXT NOT NULL CHECK (actor_kind IN ('user', 'worker', 'system')),
  actor_id      TEXT NOT NULL,
  old_state     TEXT,
  new_state     TEXT NOT NULL,
  reason        TEXT,
  failure_code  TEXT,
  created_at    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_document_ingestion_audit_events_ingestion_created
  ON control_plane.document_ingestion_audit_events (ingestion_id, created_at DESC);
