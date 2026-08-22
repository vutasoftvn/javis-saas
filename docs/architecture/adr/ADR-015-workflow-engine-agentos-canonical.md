# ADR-015: `agentos/workflows/` is the canonical workflow engine; port version-history from `legacy/backend`

## Status

Accepted (2026-08-22), user-confirmed.

## Context

Two workflow engines exist (`docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md` Part A7, confirmed by `docs/architecture/AI_AGENT_OS_AUDIT_NOTES.md` §0.1):

| Feature | `agentos/workflows/engine.py` | `legacy/backend/integrations/workflows` |
|---|---|---|
| Deterministic/Agent/Approval steps | ✅ (`DeterministicStep`, `AgentStep`, `ApprovalGateStep`) | ✅ (`WorkflowApproval` model) |
| Retry | ❌ | ❌ |
| Compensation/rollback | ❌ | ❌ |
| Parallel branch/fork-join | ❌ | ❌ |
| Version history | ❌ | ✅ (`WorkflowVersion`, `version_no`, `current_version_id`) |

Neither engine has retry/compensation/parallel — this is a shared gap, not a reason to prefer one over the other. `legacy/backend` is frozen-in-place per ADR-012 (not actively developed, kept only as an integration reference for LLM Gateway/OAuth/n8n/Sandbox) — building new workflow capability on top of it would contradict ADR-012 and ADR-013's direction.

## Decision

**`agentos/workflows/` is the canonical workflow engine**, consistent with ADR-013's direction (`agentos/` as target architecture). `legacy/backend/integrations/workflows`'s only feature `agentos/workflows/` lacks — **version history** (`WorkflowVersion` model) — is ported into `agentos/workflows/` as a required gap-closing task, not left behind as a reason to keep two engines alive.

Scope for the port (executed as a Giai đoạn 3 task in the gap-analysis roadmap, not by this ADR itself):
1. Add a `WorkflowVersion`-equivalent concept to `agentos/workflows/models.py` — each `Workflow` definition gets `version_no` + immutable prior versions, following the same shape as `legacy/backend/integrations/workflows/models.py:54-69`.
2. Retry, compensation, and parallel-branch support (already tracked in the gap analysis Giai đoạn 3 tasks 3.1–3.3) are built directly in `agentos/workflows/`, not ported from `legacy/backend` since neither side has them today.
3. `frontend/lib/modules/workflows` (the canonical workflow frontend per `COSA_CANONICAL_OWNERSHIP_MAP.md`) currently talks to `legacy/backend/integrations/workflows`'s router/API shape — this ADR does not decide the frontend cutover; that is a separate, later decision gated on `agentos/workflows/` exposing an equivalent HTTP API (it currently doesn't have one at all — `agentos/workflows/` is Python-internal only).

## Cập nhật thực thi (2026-08-22)

Bước 1 (version history) đã hoàn thành: `agentos/workflows/definition_registry.py` (`WorkflowDefinitionRegistry`, `WorkflowDefinition`) theo dõi version theo tên, bất biến (đăng ký version mới không sửa version cũ), `current_version()`/`get_version()`/`history()`. Vì `WorkflowStep` là Python object/callable chứ không phải data khai báo kiểu `graph_jsonb` như bên `legacy/backend`, registry lưu 1 `steps_factory` function cho mỗi version thay vì serialize chính step — khác biệt kiến trúc thật, không phải rút gọn tùy tiện. Test: `tests/agentos/workflows/test_definition_registry.py` (9 test, bao gồm 1 test chạy hết qua `WorkflowEngine.start()` thật). Không đổi API hiện có của `WorkflowEngine` — registry là lớp bổ sung, opt-in.

Bước 2/3 (retry/compensation/parallel) đã hoàn thành ở Giai đoạn 3.1–3.3 (xem gap analysis).

## Consequences

- `legacy/backend/integrations/workflows` stays running unchanged (frozen per ADR-012) — it is not modified to add version history or other features; all new workflow-engine work goes into `agentos/workflows/`.
- Do not build a workflow-visible HTTP API for `agentos/workflows/` speculatively — per the gap analysis Giai đoạn 2 priority (get `services/` a real consumer first), workflow-API-for-frontend is later work, not blocking.
- `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`'s row "Workflow persistence/API" (currently pointing at `legacy/backend/integrations/workflows` as canonical) should be updated to note "target: superseded by `agentos/workflows/`, see ADR-015" once the version-history port lands — not before, to avoid the ownership map claiming a state that isn't true yet (per ADR-012's explicit lesson: "documentation... is a reliable record of intent... not... current working state").
