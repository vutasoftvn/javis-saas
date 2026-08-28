# ADR-AGENT-REG-001: 3 seed agent cho launch, registration API là post-launch

## Status
ACCEPTED 2026-08-28 (Lưu ý: ACCEPTED ≠ IMPLEMENTED ≠ WIRED ≠ VERIFIED ≠ PRODUCTION).

## Context

Verify bằng code (2026-08-28):
- 3 AgentSpec hard-code trong `apps/cosa/agents/specs.py`, seed vào spec
  registry lúc startup (`apps/cosa/agents/seed.py`, gọi từ
  `apps/cosa/api/app.py` lifespan).
- **Không có endpoint** publish AgentSpec runtime. Thêm agent mới = sửa code
  + redeploy.
- Hạ tầng cho registration API đã tồn tại: `PostgresSpecRegistryRepository`
  (immutability qua `definition_hash`), invariant INV-A3 (spec phải tham
  chiếu `prompt_ref` + `model_policy_ref` đã publish).

Đây không phải blocker go-live (3 agent đủ MVP), nhưng phải có quyết định
chính thức để tránh "self-report Wave hoàn thành" mà thực chất còn thiếu
(CLAUDE.md §29.1).

## Decision

**Launch với 3 seed agent.** Runtime agent registration API là feature
post-launch.

- `apps/cosa/agents/specs.py` + `seed.py` giữ nguyên là nguồn AgentSpec cho
  launch.
- Không thêm endpoint `POST /agents/specs` trong nhánh này.
- Thay đổi agent trước go-live vẫn qua code review + redeploy (chấp nhận —
  tần suất thấp, cần review kỹ nội dung prompt/policy).

## Điều kiện re-open

Bất kỳ điều nào:
- Cần > 5 agent hoặc thay đổi AgentSpec > 1 lần/tuần → chi phí redeploy thành
  gánh nặng.
- Có yêu cầu cho phép khách hàng / ops tự định nghĩa agent.

## Follow-up

`docs/tickets/POST-LAUNCH-AGENT-REG-001-registration-api.md` — scope:
- Endpoint `POST /agents/specs` trong `apps/cosa/api`, `auth: true`, chỉ role
  admin/platform.
- Validate `prompt_ref` + `model_policy_ref` tồn tại trong registry
  (invariant INV-A3) → reject nếu thiếu.
- Ghi spec qua `PostgresSpecRegistryRepository`; immutability qua
  `definition_hash` (không cho overwrite hash đã tồn tại).
- Test: publish spec hợp lệ; reject spec thiếu prompt_ref; reject overwrite
  cùng hash; tenant scoping.

## Relates
- Part 2F. Ghi vào master `2026-08-28-test-prod-readiness.md` (bảng deferred).
- Invariant INV-A3, `PostgresSpecRegistryRepository`.
