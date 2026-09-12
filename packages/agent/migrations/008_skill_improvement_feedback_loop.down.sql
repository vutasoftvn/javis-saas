-- Down migration 008: Governed Skill Improvement Feedback Loop
--
-- Refuses to run if any observation, aggregate, request, outbox, evaluation,
-- mutation, or extended feedback evidence exists.

DO $$
DECLARE
    obs_count bigint := 0;
    agg_count bigint := 0;
    req_count bigint := 0;
    outbox_count bigint := 0;
    eval_count bigint := 0;
    mut_count bigint := 0;
    extended_feedback_count bigint := 0;
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'agent' AND table_name = 'skill_usage_observations'
    ) THEN
        SELECT count(*) INTO obs_count FROM agent.skill_usage_observations;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'agent' AND table_name = 'skill_feedback_aggregates'
    ) THEN
        SELECT count(*) INTO agg_count FROM agent.skill_feedback_aggregates;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'agent' AND table_name = 'skill_improvement_requests'
    ) THEN
        SELECT count(*) INTO req_count FROM agent.skill_improvement_requests;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'agent' AND table_name = 'skill_improvement_outbox'
    ) THEN
        SELECT count(*) INTO outbox_count FROM agent.skill_improvement_outbox;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'agent' AND table_name = 'skill_improvement_evaluations'
    ) THEN
        SELECT count(*) INTO eval_count FROM agent.skill_improvement_evaluations;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'agent' AND table_name = 'skill_improvement_mutations'
    ) THEN
        SELECT count(*) INTO mut_count FROM agent.skill_improvement_mutations;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'agent' AND table_name = 'agent_skill_feedback' AND column_name = 'idempotency_key'
    ) THEN
        SELECT count(*) INTO extended_feedback_count
        FROM agent.agent_skill_feedback
        WHERE idempotency_key IS NOT NULL OR definition_hash IS NOT NULL;
    END IF;

    IF obs_count > 0 OR agg_count > 0 OR req_count > 0 OR outbox_count > 0 OR eval_count > 0 OR mut_count > 0 OR extended_feedback_count > 0 THEN
        RAISE EXCEPTION
            'migration 008 down refused: skill improvement feedback evidence present '
            '(obs=%, agg=%, req=%, outbox=%, eval=%, mut=%, extended_feedback=%) — rolling back would destroy audit or improvement evidence',
            obs_count, agg_count, req_count, outbox_count, eval_count, mut_count, extended_feedback_count;
    END IF;
END $$;

DROP TABLE IF EXISTS agent.skill_improvement_mutations;
DROP TABLE IF EXISTS agent.skill_improvement_evaluations;
DROP TABLE IF EXISTS agent.skill_improvement_outbox;
DROP TABLE IF EXISTS agent.skill_improvement_requests;
DROP TABLE IF EXISTS agent.skill_feedback_aggregates;
DROP TABLE IF EXISTS agent.skill_usage_observations;

DROP INDEX IF EXISTS agent.ux_agent_skill_feedback_ws_idempotency;

ALTER TABLE agent.agent_skill_feedback
    DROP COLUMN IF EXISTS idempotency_key,
    DROP COLUMN IF EXISTS source_kind,
    DROP COLUMN IF EXISTS run_id,
    DROP COLUMN IF EXISTS definition_hash,
    DROP COLUMN IF EXISTS skill_version;
