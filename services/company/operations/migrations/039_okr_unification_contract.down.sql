-- 039_okr_unification_contract.down.sql
-- Không khôi phục dữ liệu họ cũ (đã bị xóa). Chỉ dựng lại cấu trúc để down không hỏng chuỗi migration.
DROP TRIGGER IF EXISTS trg_project_objective_alignment ON strategy.projects;
DROP FUNCTION IF EXISTS strategy.fn_project_objective_alignment();
ALTER TABLE strategy.projects DROP CONSTRAINT IF EXISTS fk_projects_objective;
UPDATE strategy.projects SET objective_id = NULL WHERE objective_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS strategy.objectives (
    id BIGINT PRIMARY KEY,
    goal_id BIGINT NOT NULL REFERENCES strategy.goals(id) ON DELETE CASCADE,
    workspace_id BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
    title TEXT NOT NULL, description TEXT, owner_user_id BIGINT,
    weight NUMERIC(4,2) DEFAULT 1.0, display_order INT DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','completed','abandoned')),
    progress_pct NUMERIC(5,2) DEFAULT 0, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS strategy.cosa_key_results (
    id BIGINT PRIMARY KEY,
    objective_id BIGINT NOT NULL REFERENCES strategy.objectives(id) ON DELETE CASCADE,
    metric_name TEXT NOT NULL, baseline NUMERIC, target NUMERIC NOT NULL,
    current_value NUMERIC DEFAULT 0, unit TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active','achieved','missed','archived')),
    display_order INT DEFAULT 0
);
ALTER TABLE strategy.projects
    ADD CONSTRAINT fk_projects_objective FOREIGN KEY (objective_id) REFERENCES strategy.objectives(id) ON DELETE SET NULL;

-- Trả hàm căn chỉnh objective về phiên bản 038 (chỉ kiểm tra cùng bảng).
CREATE OR REPLACE FUNCTION strategy.fn_okr_objective_alignment() RETURNS trigger AS $$
DECLARE parent_scope text;
BEGIN
    IF NEW.parent_objective_id IS NULL THEN RETURN NEW; END IF;
    SELECT scope INTO parent_scope FROM strategy.okr_objectives
     WHERE id = NEW.parent_objective_id AND workspace_id = NEW.workspace_id;
    IF parent_scope IS DISTINCT FROM 'company' THEN
        RAISE EXCEPTION 'parent_objective_id must reference a company-scope objective in the same workspace'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
