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
| Version history | `agentos/workflows/definition_registry.py` (`WorkflowDefinitionRegistry`, port từ `WorkflowVersion` theo ADR-015) |
| Engine | `agentos/workflows/engine.py` |

`agentos/workflows/` nay đã có mọi tính năng mà `legacy/backend/integrations/workflows` từng hơn (version history) — ADR-015 hoàn thành đầy đủ.

### Event naming (`entity.action`)

Chuẩn hóa đúng ở cả `services/shared/events.ts` (Encore Topic, at-least-once) và `agentos/core/events.py` (`EventEnvelope` + `InMemoryEventBus` — chỉ single-process, chưa production-durable, tự ghi rõ "Phase 8 scope" trong code).

## Còn thiếu

- `agentos/workflows/` chưa có HTTP API — hoàn toàn Python-internal, không phải lý do chặn (ưu tiên thấp theo ADR-015, chưa cần cho `frontend/`).
- `InMemoryEventBus` chưa production-durable — cross-process event bus vẫn là Phase 8 scope.

Chi tiết đầy đủ: `docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md` Phần A7, `docs/architecture/adr/ADR-015-workflow-engine-agentos-canonical.md`.
