-- Backfill task_projects từ task -> initiative -> project chain
-- Chỉ copy link nếu tất cả ba bảng (task, initiative, project) đều cùng workspace
-- Nếu initiative_id hoặc project_id NULL thì skip

INSERT INTO operating.task_projects (workspace_id, task_id, project_id, created_at)
SELECT t.workspace_id, t.id, p.id, NOW()
FROM operating.tasks t
JOIN strategy.initiatives i ON i.id = t.initiative_id AND i.workspace_id = t.workspace_id
JOIN strategy.projects p ON p.id = i.project_id AND p.workspace_id = t.workspace_id
WHERE t.initiative_id IS NOT NULL AND i.project_id IS NOT NULL
ON CONFLICT (task_id, project_id) DO NOTHING;

-- Postcondition: đảm bảo không có cross-workspace links được tạo
DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM operating.task_projects tp
    JOIN operating.tasks t ON t.id = tp.task_id
    JOIN strategy.projects p ON p.id = tp.project_id
    WHERE tp.workspace_id <> t.workspace_id OR tp.workspace_id <> p.workspace_id
  ) THEN
    RAISE EXCEPTION 'Postcondition failed: task_projects contains cross-workspace links';
  END IF;
END $$;
