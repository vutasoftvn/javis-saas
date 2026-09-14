-- Migration 025: Executive Board activation chuyển cấp Workspace (thay
-- project_executive_role_activations cho TOÀN BỘ 13 role — 1 công ty chỉ có
-- 1 CFO/CRO/COO thật dù chạy nhiều Project song song ở stage khác nhau).
-- Bảng project-scoped cũ KHÔNG bị xoá (Expand-only) — chỉ ngừng dùng trong code.
CREATE TABLE operating.workspace_executive_role_activations (
  id bigint PRIMARY KEY,
  workspace_id bigint NOT NULL,
  role_key varchar(64) NOT NULL,
  state varchar(32) NOT NULL, -- 'ACTIVE' | 'DISABLED'
  version integer NOT NULL DEFAULT 1,
  actor_id bigint NOT NULL,
  disabled_reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uix_workspace_executive_role_activations_ws_role UNIQUE (workspace_id, role_key)
);

CREATE INDEX idx_workspace_executive_role_activations_ws ON operating.workspace_executive_role_activations(workspace_id);

CREATE TABLE operating.workspace_executive_role_activation_events (
  id bigint PRIMARY KEY,
  workspace_id bigint NOT NULL,
  role_key varchar(64) NOT NULL,
  activation_id bigint NOT NULL REFERENCES operating.workspace_executive_role_activations(id) ON DELETE CASCADE,
  from_state varchar(32),
  to_state varchar(32) NOT NULL,
  actor_id bigint NOT NULL,
  version integer NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}',
  occurred_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_workspace_exec_role_act_events_act ON operating.workspace_executive_role_activation_events(activation_id, occurred_at);
