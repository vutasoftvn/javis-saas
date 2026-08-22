# 05 — Business OS / Encore Spec

**Blueprint gốc:** §38–§45 của `markdown/AI_Agent_OS_Master_Architecture.md`.
**Áp dụng cho:** `services/` (Encore, target theo blueprint §39) — `legacy/backend` frozen-in-place (ADR-012), không nhận thêm business logic mới.

## Trạng thái hiện tại

`services/` có 4 cluster khớp gần 1:1 danh sách domain blueprint §38:

| Cluster | Domain |
|---|---|
| `identity` | auth, org, workspace, token |
| `operations` | task, okr, twelve-week-year, project, initiative |
| `commercial` | lead, opportunity, account, contact, customer, billing, marketing |
| `finance-legal` | accounting-period/profile/regime, financial-transaction, legal-* |

**Pilot thật (Giai đoạn 2, 2026-08-22):** `task_create`/`task_list`/`task_update_status` đã verify qua real HTTP (không mock) từ `agentos/tools/encore_client.py` — xem `tests/agentos/test_services_pilot_e2e.py`. Khi wiring pilot, phát hiện + sửa 1 gap thật: `task.created` event đã định nghĩa ở `shared/events.ts` nhưng chưa từng publish — nay `createTask` publish đúng 1 lần cho insert thật (dùng Postgres `xmax = 0` để không publish lại khi idempotency-key retry).

## Còn thiếu

- Chỉ `operations.tasks` (+ `finance.financial_transactions` per ADR-012) có pilot HTTP thật — `commercial`, phần lớn `finance-legal`, và `identity` ngoài workspace-create **chưa được verify sống tương tự**. Không tự nhận "Phase 1 parity" cho các cluster đó là đã kiểm chứng thật.
- `legacy/agent_runtime`, `frontend/`, `realtime_agent` vẫn chưa gọi `services/` — pilot chỉ chứng minh khả năng kỹ thuật, chưa phải production traffic thật.
- Idempotency key còn thiếu ở nhiều bảng khác (`commercial.leads/opportunities/accounts/contacts`, `finance.accounting_periods/legal_*`) — theo ADR-012, migration đã stage cho vài bảng nhưng `.ts` endpoint chưa wire.

Chi tiết đầy đủ: `docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md` Phần A6, `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` mục "agentos/ + services/ migration status".
