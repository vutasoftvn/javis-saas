-- Migration 35: Workspace capability manifest — operator surface overrides
--
-- `WorkspaceCapabilityManifest` (spec 2026-09-09-founder-trial-domain-agent-mvp
-- §7.1) là overlay per-workspace trên static released-surface policy
-- (`services/cosa/services/surface-policy.ts`) + entitlement (module configs
-- migration 33) + connector status (workspace_connector_installations).
--
-- Bảng này CHỈ lưu operator override — không lưu bản sao toàn bộ manifest.
-- Ràng buộc quan trọng: override KHÔNG bao giờ nâng lên 'AVAILABLE'. Operator
-- chỉ được hạ cấp hoặc bật 'PILOT' per-workspace; server là authority, user
-- preference/route cache không thể tự nâng một surface 'PLANNED' thành live.

CREATE TABLE IF NOT EXISTS cosa.workspace_surface_overrides (
  workspace_id     BIGINT NOT NULL REFERENCES cosa.workspaces(id) ON DELETE CASCADE,
  surface_key      TEXT NOT NULL,
  status_override  TEXT NOT NULL CHECK (status_override IN ('PILOT', 'PLANNED', 'CONFIGURATION_REQUIRED', 'UNAVAILABLE')),
  reason           TEXT,
  updated_by       TEXT NOT NULL,
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (workspace_id, surface_key)
);

CREATE INDEX IF NOT EXISTS idx_workspace_surface_overrides_workspace
  ON cosa.workspace_surface_overrides (workspace_id);
