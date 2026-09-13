-- Migration 010: Founder Asset Provenance for Skill Observations & Improvement
--
-- Adds nullable forward-compatible project_id and manifest_hash columns to
-- skill observation, aggregate, request, outbox, and feedback records.

ALTER TABLE agent.skill_usage_observations
    ADD COLUMN IF NOT EXISTS project_id varchar(64),
    ADD COLUMN IF NOT EXISTS manifest_hash varchar(128);

ALTER TABLE agent.skill_feedback_aggregates
    ADD COLUMN IF NOT EXISTS project_id varchar(64),
    ADD COLUMN IF NOT EXISTS manifest_hash varchar(128);

ALTER TABLE agent.skill_improvement_requests
    ADD COLUMN IF NOT EXISTS project_id varchar(64),
    ADD COLUMN IF NOT EXISTS manifest_hash varchar(128);

ALTER TABLE agent.skill_improvement_outbox
    ADD COLUMN IF NOT EXISTS project_id varchar(64),
    ADD COLUMN IF NOT EXISTS manifest_hash varchar(128);

ALTER TABLE agent.agent_skill_feedback
    ADD COLUMN IF NOT EXISTS project_id varchar(64),
    ADD COLUMN IF NOT EXISTS manifest_hash varchar(128);

CREATE INDEX IF NOT EXISTS idx_skill_usage_observations_proj_run
    ON agent.skill_usage_observations (workspace_id, project_id, run_id);
