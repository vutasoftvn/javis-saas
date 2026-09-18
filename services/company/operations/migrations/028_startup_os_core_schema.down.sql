-- Rollback migration 028: Startup OS Core Schema (COSA v1.0)

DROP FUNCTION IF EXISTS strategy.fn_suggest_dimension_review(BIGINT);
DROP FUNCTION IF EXISTS strategy.fn_goals_needing_review(BIGINT);

DROP VIEW IF EXISTS strategy.v_goal_tree;
DROP VIEW IF EXISTS strategy.v_current_company_context;

DROP TRIGGER IF EXISTS trg_goal_snapshot ON strategy.goals;
DROP FUNCTION IF EXISTS strategy.fn_link_goal_to_snapshot();

DROP TRIGGER IF EXISTS trg_snapshot_current   ON strategy.onboard_snapshots;
DROP TRIGGER IF EXISTS trg_ambition_current   ON strategy.onboard_goals_ambition;
DROP TRIGGER IF EXISTS trg_challenges_current ON strategy.onboard_challenges;
DROP TRIGGER IF EXISTS trg_market_current     ON strategy.onboard_market;
DROP TRIGGER IF EXISTS trg_team_current       ON strategy.onboard_team_culture;
DROP TRIGGER IF EXISTS trg_stage_current      ON strategy.onboard_stage_scale;
DROP TRIGGER IF EXISTS trg_identity_current   ON strategy.onboard_identity;
DROP FUNCTION IF EXISTS strategy.fn_demote_current();

ALTER TABLE strategy.projects DROP CONSTRAINT IF EXISTS fk_projects_objective;
DROP TABLE IF EXISTS strategy.cosa_key_results;
DROP TABLE IF EXISTS strategy.objectives;
DROP TABLE IF EXISTS strategy.goals;

DROP TABLE IF EXISTS strategy.onboard_review_cadence;
DROP TABLE IF EXISTS strategy.onboard_goals_ambition;
DROP TABLE IF EXISTS strategy.onboard_challenges;
DROP TABLE IF EXISTS strategy.onboard_competitors;
DROP TABLE IF EXISTS strategy.onboard_market;
DROP TABLE IF EXISTS strategy.onboard_team_culture;
DROP TABLE IF EXISTS strategy.onboard_founders;
DROP TABLE IF EXISTS strategy.onboard_stage_scale;
DROP TABLE IF EXISTS strategy.onboard_values;
DROP TABLE IF EXISTS strategy.onboard_identity;
DROP TABLE IF EXISTS strategy.onboard_snapshots;
DROP TABLE IF EXISTS strategy.conversation_turns;
DROP TABLE IF EXISTS strategy.onboard_sessions;

ALTER TABLE strategy.projects DROP COLUMN IF EXISTS link_status;
ALTER TABLE strategy.projects DROP COLUMN IF EXISTS origin;
ALTER TABLE strategy.projects DROP COLUMN IF EXISTS objective_id;
