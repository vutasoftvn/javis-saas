-- 038_okr_unification_expand.down.sql
DROP TRIGGER IF EXISTS trg_okr_objective_alignment ON strategy.okr_objectives;
DROP FUNCTION IF EXISTS strategy.fn_okr_objective_alignment();
DROP INDEX IF EXISTS strategy.idx_okr_objectives_parent;
DROP INDEX IF EXISTS strategy.idx_okr_objectives_cycle;
DROP INDEX IF EXISTS strategy.idx_okr_objectives_goal;
ALTER TABLE strategy.okr_objectives
    DROP CONSTRAINT IF EXISTS fk_okr_objective_parent_ws,
    DROP CONSTRAINT IF EXISTS fk_okr_objective_cycle_ws,
    DROP CONSTRAINT IF EXISTS fk_okr_objective_goal_ws,
    DROP CONSTRAINT IF EXISTS chk_okr_objectives_scope_shape,
    DROP CONSTRAINT IF EXISTS chk_okr_objectives_scope;
DELETE FROM strategy.okr_objectives WHERE scope = 'company';
ALTER TABLE strategy.okr_objectives
    DROP COLUMN IF EXISTS parent_objective_id,
    DROP COLUMN IF EXISTS cycle_id,
    DROP COLUMN IF EXISTS goal_id,
    DROP COLUMN IF EXISTS scope;
ALTER TABLE strategy.okr_objectives ALTER COLUMN project_id SET NOT NULL;
ALTER TABLE strategy.okr_cycles DROP CONSTRAINT IF EXISTS uix_okr_cycles_id_workspace;
ALTER TABLE strategy.goals      DROP CONSTRAINT IF EXISTS uix_goals_id_workspace;
