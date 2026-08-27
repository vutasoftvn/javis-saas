-- Preflight kiểm tra dữ liệu mồ côi TRƯỚC khi thêm composite uniqueness /
-- foreign key. Chạy: psql "$COMPANY_DATABASE_URL" -f này. Kỳ vọng: 0 row ở
-- mọi truy vấn. Nếu có row -> phải làm sạch dữ liệu trước khi migrate.

-- 1. project trỏ tới portfolio khác workspace
SELECT p.id AS project_id, p.workspace_id AS project_ws, pf.workspace_id AS portfolio_ws
FROM strategy.projects p
JOIN strategy.portfolios pf ON pf.id = p.portfolio_id
WHERE pf.workspace_id <> p.workspace_id;

-- 2. portfolio_projects trỏ chéo workspace
SELECT pp.id, pp.workspace_id, p.workspace_id AS project_ws, pf.workspace_id AS portfolio_ws
FROM strategy.portfolio_projects pp
JOIN strategy.projects p ON p.id = pp.project_id
JOIN strategy.portfolios pf ON pf.id = pp.portfolio_id
WHERE pp.workspace_id <> p.workspace_id OR pp.workspace_id <> pf.workspace_id;

-- 3. task.initiative_id trỏ tới initiative khác workspace
SELECT t.id AS task_id, t.workspace_id AS task_ws, i.workspace_id AS initiative_ws
FROM operating.tasks t
JOIN strategy.initiatives i ON i.id = t.initiative_id
WHERE i.workspace_id <> t.workspace_id;

-- 4. initiative.project_id trỏ tới project khác workspace
SELECT i.id AS initiative_id, i.workspace_id AS initiative_ws, p.workspace_id AS project_ws
FROM strategy.initiatives i
JOIN strategy.projects p ON p.id = i.project_id
WHERE p.workspace_id <> i.workspace_id;

-- 5. NULL workspace_id ở các bảng target
SELECT 'projects' AS tbl, count(*) FROM strategy.projects WHERE workspace_id IS NULL
UNION ALL SELECT 'portfolios', count(*) FROM strategy.portfolios WHERE workspace_id IS NULL
UNION ALL SELECT 'okr_objectives', count(*) FROM strategy.okr_objectives WHERE workspace_id IS NULL
UNION ALL SELECT 'tasks', count(*) FROM operating.tasks WHERE workspace_id IS NULL;
