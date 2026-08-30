-- services/company/identity/migrations/6_add_cosa_delegation_replay.up.sql
-- Task 3 (AI compliance production hardening) — chống replay cho scoped
-- COSA -> Company delegation JWT (apps/cosa/auth/jwt.py::mint_company_delegation).
-- Trước Task 3, "delegation" giữa 2 phía chỉ re-sign lại {sub, aud?, exp} —
-- không có workspace/run/capability scope, và không có gì chặn 1 delegation
-- token hợp lệ bị dùng lại (replay) cho cùng side effect nhiều lần nếu payload
-- bị lộ hoặc bị gọi lại do retry ở tầng khác.
--
-- Bảng này chỉ dùng cho EXTERNAL call / mutation (side effect thật) — verify
-- Company (cosa-delegation.service.ts::consumeCosaDelegation) INSERT ... ON
-- CONFLICT DO NOTHING theo PK jti; nếu không insert được (đã tồn tại) coi là
-- replay và từ chối. READ-only snapshot resolution KHÔNG ghi bảng này.
CREATE TABLE core.cosa_delegation_replays (
  jti TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  capability_id TEXT NOT NULL,
  consumed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX cosa_delegation_replays_workspace_run_idx
  ON core.cosa_delegation_replays (workspace_id, run_id);
