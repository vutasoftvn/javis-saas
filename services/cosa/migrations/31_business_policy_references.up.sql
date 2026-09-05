-- Migration 31: Business policy references in COSA Control Plane

CREATE TABLE IF NOT EXISTS cosa.workspace_business_policy_references (
  platform_workspace_id  BIGINT PRIMARY KEY REFERENCES cosa.workspaces(id) ON DELETE CASCADE,
  business_workspace_id  TEXT NOT NULL,
  version                INTEGER NOT NULL,
  policy_hash            TEXT NOT NULL,
  synced_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
