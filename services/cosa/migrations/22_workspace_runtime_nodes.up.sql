-- services/cosa/migrations/22_workspace_runtime_nodes.up.sql
-- M5 §1 — Runtime node registration + device key + heartbeat (control-plane).
-- Local Workspace Runtime Node đăng ký lúc khởi động (device key fingerprint từ
-- OS Keychain — reuse cơ chế M3 §6), gửi heartbeat. Node chưa đăng ký / device
-- key không khớp ⇒ KHÔNG được nhận command (assert ở service).
-- presence "computed": ONLINE nếu last_heartbeat_at còn tươi; DEGRADED nếu chớm
-- cũ; OFFLINE nếu quá hạn hoặc chưa từng heartbeat (logic ở service — now() không
-- IMMUTABLE nên không dùng được trong index/generated column).

CREATE TABLE IF NOT EXISTS control_plane.workspace_runtime_nodes (
  node_id                BIGINT PRIMARY KEY,           -- SpineId Snowflake do control-plane sinh
  workspace_id           BIGINT NOT NULL,
  device_key_fingerprint TEXT NOT NULL,
  runtime_role           TEXT NOT NULL
                           CHECK (runtime_role IN ('local_workspace_runtime', 'cloud_workspace_runtime')),
  presence_status        TEXT NOT NULL DEFAULT 'OFFLINE'
                           CHECK (presence_status IN ('ONLINE', 'OFFLINE', 'DEGRADED')),
  agent_version          TEXT,
  last_heartbeat_at      TIMESTAMPTZ,
  registered_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at             TIMESTAMPTZ,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Một (workspace, device fingerprint) đang hoạt động = một node ⇒ register idempotent.
CREATE UNIQUE INDEX IF NOT EXISTS uq_workspace_runtime_nodes_ws_fingerprint
  ON control_plane.workspace_runtime_nodes (workspace_id, device_key_fingerprint)
  WHERE revoked_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_workspace_runtime_nodes_ws_presence
  ON control_plane.workspace_runtime_nodes (workspace_id, presence_status);
