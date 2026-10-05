-- 038_okr_unification_expand.up.sql
-- Dự án A0 (expand): một họ OKR duy nhất. Chỉ CỘNG THÊM; họ cũ bị xóa ở 039.

-- Khóa ghép để FK ghép (id, workspace_id) theo chuẩn tenancy.
ALTER TABLE strategy.goals       ADD CONSTRAINT uix_goals_id_workspace       UNIQUE (id, workspace_id);
ALTER TABLE strategy.okr_cycles  ADD CONSTRAINT uix_okr_cycles_id_workspace  UNIQUE (id, workspace_id);

ALTER TABLE strategy.okr_objectives
    ADD COLUMN scope               text   NOT NULL DEFAULT 'project',
    ADD COLUMN goal_id             bigint,
    ADD COLUMN cycle_id            bigint,
    ADD COLUMN parent_objective_id bigint;

ALTER TABLE strategy.okr_objectives ALTER COLUMN project_id DROP NOT NULL;

ALTER TABLE strategy.okr_objectives
    ADD CONSTRAINT chk_okr_objectives_scope CHECK (scope IN ('company', 'project')),
    ADD CONSTRAINT chk_okr_objectives_scope_shape CHECK (
        (scope = 'company' AND project_id IS NULL AND parent_objective_id IS NULL AND goal_id IS NOT NULL)
        OR (scope = 'project' AND project_id IS NOT NULL)
    ),
    ADD CONSTRAINT fk_okr_objective_goal_ws
        FOREIGN KEY (goal_id, workspace_id) REFERENCES strategy.goals (id, workspace_id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_okr_objective_cycle_ws
        FOREIGN KEY (cycle_id, workspace_id) REFERENCES strategy.okr_cycles (id, workspace_id)
        ON DELETE SET NULL (cycle_id),
    ADD CONSTRAINT fk_okr_objective_parent_ws
        FOREIGN KEY (parent_objective_id, workspace_id) REFERENCES strategy.okr_objectives (id, workspace_id)
        ON DELETE SET NULL (parent_objective_id);

CREATE INDEX IF NOT EXISTS idx_okr_objectives_goal   ON strategy.okr_objectives (workspace_id, goal_id)   WHERE goal_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_okr_objectives_cycle  ON strategy.okr_objectives (workspace_id, cycle_id)  WHERE cycle_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_okr_objectives_parent ON strategy.okr_objectives (parent_objective_id)     WHERE parent_objective_id IS NOT NULL;

-- Phần căn chỉnh cùng bảng. Phần so với projects.objective_id thêm ở 039.
CREATE OR REPLACE FUNCTION strategy.fn_okr_objective_alignment() RETURNS trigger AS $$
DECLARE
    parent_scope text;
BEGIN
    IF NEW.parent_objective_id IS NULL THEN
        RETURN NEW;
    END IF;
    SELECT scope INTO parent_scope
      FROM strategy.okr_objectives
     WHERE id = NEW.parent_objective_id AND workspace_id = NEW.workspace_id;
    IF parent_scope IS DISTINCT FROM 'company' THEN
        RAISE EXCEPTION 'parent_objective_id must reference a company-scope objective in the same workspace'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_okr_objective_alignment ON strategy.okr_objectives;
CREATE TRIGGER trg_okr_objective_alignment
    BEFORE INSERT OR UPDATE OF parent_objective_id, scope, workspace_id ON strategy.okr_objectives
    FOR EACH ROW EXECUTE FUNCTION strategy.fn_okr_objective_alignment();
