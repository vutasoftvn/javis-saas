-- 039_okr_unification_contract.up.sql
-- Dự án A0 (contract). Dữ liệu họ cũ chỉ là dữ liệu thử (đã xác nhận 2026-10-05).
-- KHÔNG dùng TRUNCATE ... CASCADE: strategy.projects có FK vào strategy.objectives.

-- 1. Gỡ liên kết cũ: project phải được người dùng link lại vào objective công ty.
UPDATE strategy.projects
   SET objective_id = NULL,
       link_status  = 'pending_review'
 WHERE objective_id IS NOT NULL;

ALTER TABLE strategy.projects DROP CONSTRAINT IF EXISTS fk_projects_objective;

-- 2. Xóa họ cũ và view phụ thuộc.
DROP VIEW IF EXISTS strategy.v_goal_tree;
DROP TABLE IF EXISTS strategy.cosa_key_results;
DROP TABLE IF EXISTS strategy.objectives;

-- 3. FK mới: project phục vụ một objective cấp công ty.
ALTER TABLE strategy.projects
    ADD CONSTRAINT fk_projects_objective
    FOREIGN KEY (objective_id, workspace_id) REFERENCES strategy.okr_objectives (id, workspace_id)
    ON DELETE SET NULL (objective_id);

-- 4. Căn chỉnh liên bảng.
CREATE OR REPLACE FUNCTION strategy.fn_okr_objective_alignment() RETURNS trigger AS $$
DECLARE
    parent_scope text;
    project_objective bigint;
BEGIN
    IF NEW.parent_objective_id IS NOT NULL THEN
        SELECT scope INTO parent_scope
          FROM strategy.okr_objectives
         WHERE id = NEW.parent_objective_id AND workspace_id = NEW.workspace_id;
        IF parent_scope IS DISTINCT FROM 'company' THEN
            RAISE EXCEPTION 'parent_objective_id must reference a company-scope objective in the same workspace'
                USING ERRCODE = '23514';
        END IF;

        IF NEW.scope = 'project' AND NEW.project_id IS NOT NULL THEN
            SELECT objective_id INTO project_objective
              FROM strategy.projects
             WHERE id = NEW.project_id AND workspace_id = NEW.workspace_id;
            IF project_objective IS NOT NULL AND project_objective <> NEW.parent_objective_id THEN
                RAISE EXCEPTION 'parent_objective_id must equal the project objective_id'
                    USING ERRCODE = '23514';
            END IF;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION strategy.fn_project_objective_alignment() RETURNS trigger AS $$
DECLARE
    obj_scope text;
BEGIN
    IF NEW.objective_id IS NULL THEN
        RETURN NEW;
    END IF;
    SELECT scope INTO obj_scope
      FROM strategy.okr_objectives
     WHERE id = NEW.objective_id AND workspace_id = NEW.workspace_id;
    IF obj_scope IS DISTINCT FROM 'company' THEN
        RAISE EXCEPTION 'projects.objective_id must reference a company-scope objective'
            USING ERRCODE = '23514';
    END IF;
    IF EXISTS (
        SELECT 1 FROM strategy.okr_objectives o
         WHERE o.project_id = NEW.id
           AND o.workspace_id = NEW.workspace_id
           AND o.parent_objective_id IS NOT NULL
           AND o.parent_objective_id <> NEW.objective_id
    ) THEN
        RAISE EXCEPTION 'project has objectives aligned to a different parent objective'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_project_objective_alignment ON strategy.projects;
CREATE TRIGGER trg_project_objective_alignment
    BEFORE INSERT OR UPDATE OF objective_id ON strategy.projects
    FOR EACH ROW EXECUTE FUNCTION strategy.fn_project_objective_alignment();
