-- 043_okr_legacy_drop.down.sql
-- Không thể khôi phục dữ liệu đã DROP từ migration này. Dựng lại cấu trúc rỗng; dữ liệu (nếu có)
-- nằm ở strategy.legacy_*_archive và phải nạp lại thủ công từ bản sao lưu trong file evidence.
-- Cấu trúc lấy nguyên văn từ 028_startup_os_core_schema.up.sql (bảng objectives, cosa_key_results,
-- hàm fn_goals_needing_review). Không dựng lại FK từ strategy.projects (đã do 039 down xử lý).

CREATE TABLE IF NOT EXISTS strategy.objectives (
    id                  BIGINT PRIMARY KEY,
    goal_id             BIGINT NOT NULL REFERENCES strategy.goals(id) ON DELETE CASCADE,
    workspace_id        BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
    title               TEXT NOT NULL,
    description         TEXT,
    owner_user_id       BIGINT,
    weight              NUMERIC(4,2) DEFAULT 1.0,
    display_order       INT DEFAULT 0,
    status              TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'abandoned')),
    progress_pct        NUMERIC(5,2) DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_objectives_goal      ON strategy.objectives(goal_id, display_order);
CREATE INDEX IF NOT EXISTS idx_objectives_workspace ON strategy.objectives(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_objectives_owner     ON strategy.objectives(owner_user_id) WHERE owner_user_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS strategy.cosa_key_results (
    id              BIGINT PRIMARY KEY,
    objective_id    BIGINT NOT NULL REFERENCES strategy.objectives(id) ON DELETE CASCADE,
    metric_name     TEXT NOT NULL,
    baseline        NUMERIC,
    target          NUMERIC NOT NULL,
    current_value   NUMERIC DEFAULT 0,
    unit            TEXT,
    status          TEXT DEFAULT 'active' CHECK (status IN ('active', 'achieved', 'missed', 'archived')),
    display_order   INT DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_cosa_kr_objective ON strategy.cosa_key_results(objective_id, display_order);

CREATE OR REPLACE FUNCTION strategy.fn_goals_needing_review(p_workspace_id BIGINT)
RETURNS TABLE (
    goal_id             BIGINT,
    goal_title          TEXT,
    goal_type           TEXT,
    snapshot_age_days   INT,
    urgency             TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        g.id,
        g.title,
        g.goal_type,
        EXTRACT(DAY FROM now() - os.captured_at)::INT,
        CASE
            WHEN g.goal_type IN ('sprint','tactical') 
                 AND os.captured_at < now() - INTERVAL '14 days' THEN 'high'
            WHEN g.goal_type = 'strategic' 
                 AND os.captured_at < now() - INTERVAL '60 days' THEN 'medium'
            ELSE 'low'
        END AS urgency
    FROM strategy.goals g
    JOIN strategy.onboard_snapshots os ON os.id = g.onboard_snapshot_id
    WHERE g.workspace_id = p_workspace_id
      AND g.status = 'active'
      AND os.id != (SELECT id FROM strategy.onboard_snapshots 
                    WHERE workspace_id = p_workspace_id AND is_current)
    ORDER BY urgency;
END;
$$ LANGUAGE plpgsql;
