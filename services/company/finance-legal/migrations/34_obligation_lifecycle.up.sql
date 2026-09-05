-- Migration 34: Obligation lifecycle transitions, evidence tracking and period idempotency
ALTER TABLE legal.legal_obligation_instances
  ADD COLUMN IF NOT EXISTS period_key TEXT,
  ADD COLUMN IF NOT EXISTS evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb;

-- Idempotency index: prevent duplicate obligation instances for the same template, period, and legal entity
CREATE UNIQUE INDEX IF NOT EXISTS uq_legal_obligation_period_entity
  ON legal.legal_obligation_instances (workspace_id, template_id, period_key, COALESCE(legal_entity_profile_id, 0))
  WHERE template_id IS NOT NULL AND period_key IS NOT NULL;

-- Audit trail table for obligation state transitions and evidence verification
CREATE TABLE IF NOT EXISTS legal.obligation_transitions (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  obligation_instance_id BIGINT NOT NULL REFERENCES legal.legal_obligation_instances(id) ON DELETE CASCADE,
  from_status TEXT NOT NULL,
  to_status TEXT NOT NULL,
  evidence_artifact_id BIGINT,
  evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  actor_member_id BIGINT,
  rationale TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_obligation_transitions_instance
  ON legal.obligation_transitions (obligation_instance_id, created_at DESC);
