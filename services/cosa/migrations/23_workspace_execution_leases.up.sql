-- services/cosa/migrations/23_workspace_execution_leases.up.sql
-- M6 §2 — WorkspaceExecutionLease + fencing: mỗi workspace CHỈ MỘT write-authoritative
-- runtime tại một thời điểm. Mọi durable write kèm fencing_token; store từ chối
-- write với token cũ (split-brain protection). Local quay lại phải acquire epoch mới.
-- fencing_token đơn điệu toàn cục qua sequence.

CREATE SEQUENCE IF NOT EXISTS control_plane.workspace_execution_fencing_seq;

CREATE TABLE IF NOT EXISTS control_plane.workspace_execution_leases (
  workspace_id           BIGINT PRIMARY KEY,
  active_runtime_node_id  BIGINT NOT NULL,
  active_runtime_role     TEXT NOT NULL
                            CHECK (active_runtime_role IN ('local_workspace_runtime', 'cloud_workspace_runtime')),
  lease_epoch             BIGINT NOT NULL DEFAULT 1,
  fencing_token           BIGINT NOT NULL,
  lease_expires_at        TIMESTAMPTZ NOT NULL,
  last_heartbeat_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_sync_cursor        TEXT,
  -- AUTO: cloud được promote tự động khi local lease hết + sync freshness đạt.
  -- MANUAL: finance/legal — promote phải do người quyết định.
  failover_policy         TEXT NOT NULL DEFAULT 'AUTO'
                            CHECK (failover_policy IN ('AUTO', 'MANUAL')),
  created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_workspace_execution_leases_node
  ON control_plane.workspace_execution_leases (active_runtime_node_id);
