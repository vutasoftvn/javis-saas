# POST-LAUNCH-AGENT-REG-001 — Runtime agent registration API

**Loại:** follow-up (post-launch)
**Owner:** _(chưa gán)_
**Quyết định gốc:** [`ADR-AGENT-REG-001`](../architecture/adr/ADR-AGENT-REG-001-seed-agents-for-launch.md)
**Điều kiện re-open:** cần > 5 agent, hoặc đổi AgentSpec > 1 lần/tuần, hoặc yêu cầu khách hàng/ops tự định nghĩa agent.

## Vấn đề

3 AgentSpec hard-code (`apps/cosa/agents/specs.py`), seed lúc startup. Thêm /
đổi agent = sửa code + redeploy.

## Scope

1. Endpoint `POST /agents/specs` trong `apps/cosa/api`, `auth: true`, chỉ
   role admin/platform (tenant-scoped theo `workspace_id`).
2. Validate `prompt_ref` + `model_policy_ref` tồn tại trong registry
   (invariant **INV-A3**) → `422` nếu thiếu.
3. Ghi spec qua `PostgresSpecRegistryRepository`. Immutability: `definition_hash`
   đã tồn tại → `409`, không overwrite.
4. `GET /agents/specs` liệt kê spec theo workspace; `GET /agents/specs/{id}`.
5. Seed hiện tại (`seed.py`) chuyển thành "publish nếu chưa có" — không xung
   đột với spec do API tạo.

## Test / DoD

- [ ] Publish spec hợp lệ → `201`, đọc lại được.
- [ ] Spec thiếu `prompt_ref` → `422`.
- [ ] Publish trùng `definition_hash` → `409`.
- [ ] Tenant A không thấy/sửa spec tenant B.
- [ ] Seed idempotent khi chạy cùng lúc với spec API.
- [ ] `make verify` xanh.
