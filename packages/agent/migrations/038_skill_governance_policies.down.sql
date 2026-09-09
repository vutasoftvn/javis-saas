-- Down migration 038.
DROP TABLE IF EXISTS agent.outcome_analysis_policy_events;
DROP TABLE IF EXISTS agent.outcome_analysis_policy_versions;
DROP INDEX IF EXISTS agent.idx_outcome_analysis_policy_drafts_ws;
DROP TABLE IF EXISTS agent.outcome_analysis_policy_drafts;
