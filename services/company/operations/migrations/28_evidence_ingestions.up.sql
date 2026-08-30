-- services/company/operations/migrations/28_evidence_ingestions.up.sql
-- Evidence Kernel: idempotent source ingestions receipt & provenance

CREATE TABLE IF NOT EXISTS strategy.evidence_ingestions (
  id                    BIGINT PRIMARY KEY,
  workspace_id          BIGINT NOT NULL,
  project_id            BIGINT NOT NULL,
  source_system         VARCHAR(50) NOT NULL,
  source_record_id      TEXT NOT NULL,
  source_payload_hash   TEXT NOT NULL,
  artifact_ref          TEXT,
  source_url            TEXT,
  observed_at           TIMESTAMPTZ NOT NULL,
  ingested_by_member_id BIGINT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT evidence_ingestions_source_system_chk
    CHECK (source_system IN ('interview', 'crm', 'telemetry', 'payment'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_evidence_ingestions_source_hash
  ON strategy.evidence_ingestions(workspace_id, source_system, source_record_id, source_payload_hash);

CREATE INDEX IF NOT EXISTS idx_evidence_ingestions_ws_proj
  ON strategy.evidence_ingestions(workspace_id, project_id);

ALTER TABLE strategy.evidence
  ADD COLUMN IF NOT EXISTS evidence_ingestion_id BIGINT REFERENCES strategy.evidence_ingestions(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS artifact_ref          TEXT,
  ADD COLUMN IF NOT EXISTS source_url            TEXT,
  ADD COLUMN IF NOT EXISTS source_system         VARCHAR(50),
  ADD COLUMN IF NOT EXISTS fact_or_inference     VARCHAR(30) NOT NULL DEFAULT 'inference',
  ADD COLUMN IF NOT EXISTS observed_at           TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS fresh_until           TIMESTAMPTZ;
