-- Rollback 013_eval_suite_run_fingerprints.sql
ALTER TABLE agent_evals.skill_mutations
    DROP COLUMN IF EXISTS eval_run_id;

ALTER TABLE agent_evals.runs
    DROP COLUMN IF EXISTS suite_definition_hash,
    DROP COLUMN IF EXISTS suite_version;

ALTER TABLE agent_evals.suites
    DROP COLUMN IF EXISTS content,
    DROP COLUMN IF EXISTS definition_hash,
    DROP COLUMN IF EXISTS version;
