-- Down Migration 010: Rollback Founder Asset Provenance
-- Abort if any table contains non-null provenance columns.

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM agent.skill_usage_observations WHERE project_id IS NOT NULL OR manifest_hash IS NOT NULL LIMIT 1) THEN
    RAISE EXCEPTION 'Cannot rollback migration 010: observations contain provenance data.';
  END IF;
END $$;

DROP INDEX IF EXISTS agent.idx_skill_usage_observations_proj_run;

ALTER TABLE agent.agent_skill_feedback
    DROP COLUMN IF EXISTS project_id,
    DROP COLUMN IF EXISTS manifest_hash;

ALTER TABLE agent.skill_improvement_outbox
    DROP COLUMN IF EXISTS project_id,
    DROP COLUMN IF EXISTS manifest_hash;

ALTER TABLE agent.skill_improvement_requests
    DROP COLUMN IF EXISTS project_id,
    DROP COLUMN IF EXISTS manifest_hash;

ALTER TABLE agent.skill_feedback_aggregates
    DROP COLUMN IF EXISTS project_id,
    DROP COLUMN IF EXISTS manifest_hash;

ALTER TABLE agent.skill_usage_observations
    DROP COLUMN IF EXISTS project_id,
    DROP COLUMN IF EXISTS manifest_hash;
