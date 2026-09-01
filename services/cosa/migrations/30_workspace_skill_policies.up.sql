-- Migration 30: Workspace Skill Policies (Task 4 — Truthful MVP Hardening)
-- Lưu policy skill theo workspace tại COSA Control Plane — nguồn sự thật duy
-- nhất cho enabled/config của 1 skill trong 1 workspace. apps/cosa (Agent
-- Platform composition layer) KHÔNG tự lưu policy này — chỉ validate skillKey
-- với registry riêng của nó rồi gọi control plane để đọc/ghi qua
-- WorkspaceSettingsClient.
CREATE TABLE IF NOT EXISTS control_plane.workspace_skill_policies (
    workspace_id BIGINT NOT NULL,
    skill_key TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT true,
    config JSONB NOT NULL DEFAULT '{}',
    revision INTEGER NOT NULL DEFAULT 1,
    updated_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (workspace_id, skill_key)
);

CREATE INDEX IF NOT EXISTS idx_workspace_skill_policies_ws_updated
    ON control_plane.workspace_skill_policies (workspace_id, updated_at DESC);
