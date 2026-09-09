-- Migration 035: Outcome Analysis binding (Task 4A).
--
-- Ánh xạ tường minh (workspace, analysis_kind) -> analyst employee + exact
-- assignment + policy + pinned skill ref. Router server dùng bảng này chọn
-- employee, KHÔNG dựa vào so khớp chuỗi / fallback ngầm (spec §9.1).
-- Expand-only + có down.

CREATE TABLE IF NOT EXISTS agent.outcome_analysis_bindings (
    workspace_id          TEXT NOT NULL,
    analysis_kind         TEXT NOT NULL,   -- TASK_OUTCOME | PROJECT_OUTCOME_SYNTHESIS
    analyst_employee_id   UUID NOT NULL,
    analyst_assignment_id UUID NOT NULL,
    policy                TEXT NOT NULL DEFAULT 'AUTO_ALL_TASKS',
                            -- AUTO_ALL_TASKS | AUTO_BY_RULE | MANUAL
    skill_id              TEXT NOT NULL,
    skill_version         TEXT NOT NULL,
    definition_hash       TEXT NOT NULL,
    version               INTEGER NOT NULL DEFAULT 1,
    updated_by            TEXT NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, analysis_kind)
);

CREATE INDEX IF NOT EXISTS idx_outcome_analysis_bindings_employee
    ON agent.outcome_analysis_bindings (workspace_id, analyst_employee_id);
