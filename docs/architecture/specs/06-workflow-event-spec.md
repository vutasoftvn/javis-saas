# 06 — Workflow & Event Spec

**Blueprint gốc:** §46–§47 của `markdown/AI_Agent_OS_Master_Architecture.md`.
**Áp dụng cho:** `agentos/workflows/` (canonical theo ADR-015) cho workflow engine; event naming `entity.action` áp dụng cho cả `agentos/` và `services/`.

## Trạng thái hiện tại

### Workflow Engine (`agentos/workflows/`)

| Thành phần | File |
|---|---|
| Workflow/Step models | `agentos/workflows/models.py` (state machine PENDING→RUNNING→WAITING_APPROVAL→COMPLETED/FAILED/CANCELLED) |
| Deterministic/Agent step | `agentos/workflows/steps.py` |
| Approval gate step | `agentos/workflows/approval_step.py` |
| Parallel fan-out step | `agentos/workflows/steps.py` (`ParallelStep`, Giai đoạn 3.1) |
| Retry | `agentos/workflows/steps.py` (`RetryStep`, Giai đoạn 3.2 — không bọc được `ApprovalGateStep`) |
| Compensation/rollback | `agentos/workflows/steps.py` (`CompensatingStep`) + `agentos/workflows/engine.py` (`_run_compensations`, Giai đoạn 3.3) |
| Engine | `agentos/workflows/engine.py` |

`legacy/backend/integrations/workflows` (canonical production theo ownership map) vẫn có 1 tính năng `agentos/workflows/` chưa có: **version history** (`WorkflowVersion`, `version_no`) — port này là việc còn lại của ADR-015, chưa thực hiện.

### Event naming (`entity.action`)

Chuẩn hóa đúng ở cả `services/shared/events.ts` (Encore Topic, at-least-once) và `agentos/core/events.py` (`EventEnvelope` + `InMemoryEventBus` — chỉ single-process, chưa production-durable, tự ghi rõ "Phase 8 scope" trong code).

## Còn thiếu

- Version history cho `Workflow` trong `agentos/workflows/models.py` (ADR-015, chưa làm).
- `agentos/workflows/` chưa có HTTP API — hoàn toàn Python-internal, không phải lý do chặn (ưu tiên thấp theo ADR-015, chưa cần cho `frontend/`).
- `InMemoryEventBus` chưa production-durable — cross-process event bus vẫn là Phase 8 scope.

Chi tiết đầy đủ: `docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md` Phần A7, `docs/architecture/adr/ADR-015-workflow-engine-agentos-canonical.md`.
