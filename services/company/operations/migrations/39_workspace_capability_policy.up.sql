-- WGA #3 — override per-workspace lớp quyền hạn cho từng capability. Founder đặt
-- ALLOW/REQUIRE_APPROVAL/DENY; classifier lúc tạo Execution Plan đọc bảng này
-- làm `tenant_policy_decision` (đè lên default theo risk). FORBIDDEN_RE vẫn thắng
-- ALLOW (không lật được). Company-side vì task nền không mint được control-plane
-- delegation để đọc workspace_agent_policy của services/cosa.
CREATE TABLE operating.workspace_capability_policy (
  workspace_id   BIGINT NOT NULL,
  capability_id  TEXT NOT NULL,
  decision       TEXT NOT NULL,  -- 'ALLOW' | 'REQUIRE_APPROVAL' | 'DENY'
  updated_by     BIGINT,
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, capability_id)
);
