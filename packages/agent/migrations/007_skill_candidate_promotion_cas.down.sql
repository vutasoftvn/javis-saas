-- Down migration 007: Skill Candidate Promotion CAS Baseline
--
-- Refuses to run if any published candidates, promotion approvals or feedback exist.

DO $$
DECLARE
    promoted_candidates bigint := 0;
    feedback_count bigint := 0;
    promoted_approvals bigint := 0;
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'agent' AND table_name = 'agent_skill_candidates'
    ) THEN
        SELECT count(*) INTO promoted_candidates
        FROM agent.agent_skill_candidates
        WHERE status = 'PUBLISHED' OR promotion_approval_id IS NOT NULL;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'agent' AND table_name = 'agent_skill_feedback'
    ) THEN
        SELECT count(*) INTO feedback_count
        FROM agent.agent_skill_feedback;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'agent' AND table_name = 'approvals'
    ) THEN
        SELECT count(*) INTO promoted_approvals
        FROM agent.approvals
        WHERE action = 'promote_skill_candidate' AND status = 'approved';
    END IF;

    IF promoted_candidates > 0 OR feedback_count > 0 OR promoted_approvals > 0 THEN
        RAISE EXCEPTION
            'migration 007 down refused: published candidates, promotion approvals or feedback evidence present '
            '(promoted_candidates=%, feedback=%, promoted_approvals=%) — rolling back would destroy audit or promotion evidence',
            promoted_candidates, feedback_count, promoted_approvals;
    END IF;
END $$;

DROP TABLE IF EXISTS agent.agent_skill_feedback;
DROP TABLE IF EXISTS agent.agent_skill_candidates;
