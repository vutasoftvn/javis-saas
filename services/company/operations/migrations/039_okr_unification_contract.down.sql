-- 039_okr_unification_contract.down.sql
-- Up không xóa bảng họ cũ nên down không dựng lại bảng; chỉ hoàn tác FK/trigger/comment.
-- View v_goal_tree (đã bị DROP ở up, không được dùng trong mã) không được dựng lại.
DROP TRIGGER IF EXISTS trg_project_objective_alignment ON strategy.projects;
DROP FUNCTION IF EXISTS strategy.fn_project_objective_alignment();
ALTER TABLE strategy.projects DROP CONSTRAINT IF EXISTS fk_projects_objective;
UPDATE strategy.projects SET objective_id = NULL, link_status = 'pending_review' WHERE objective_id IS NOT NULL;

COMMENT ON TABLE strategy.objectives IS NULL;
COMMENT ON TABLE strategy.cosa_key_results IS NULL;

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
