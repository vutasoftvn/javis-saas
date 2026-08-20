# COSA Tool Invocation Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create one governed, event-emitting invocation path for registered COSA tools, suitable for chat, native runtime, and the DeepSeek Harness adapter.

**Architecture:** Add runtime-neutral invocation contracts and a `ToolInvocationPipeline` beside the current registry. The pipeline creates server-derived execution context, delegates policy to `GovernanceKernel`, executes only allowed calls through `execute_tool_spec`, and emits durable events. No legacy path is removed in this slice.

**Tech Stack:** Python, FastAPI packages, SQLAlchemy, Pydantic, pytest/pytest-asyncio, SQLite EventStore.

**Spec:** `docs/architecture/COSA_DEEPSEEK_HARNESS_REFERENCE_ALIGNMENT_AND_RUNTIME_COMPOSITION.md`

## Global Constraints

- Business-domain services must not import DeepSeek Harness or provider-specific types.
- Model-supplied `workspace_id`, `user_id`, `company_id`, `run_id`, and approval IDs are ignored; scope comes from `AgentRunRequest`.
- `GovernanceKernel` is the pre-execution authority. `DENY` and `REQUIRE_APPROVAL` execute no tool body.
- Only model name, description, and input parameters are model-visible. Policy, callbacks, timeout, output internals, and credentials stay server-only.
- Results/events must be JSON-safe and must not contain chain-of-thought or secrets.
- Use TDD; do not introduce plugin lifecycle, dynamic plugins, or a DeepSeek Harness dependency in this slice.

---

## File structure

| File | Responsibility |
|---|---|
| `backend/agent_runtime/tools/__init__.py` | Public runtime-neutral tool exports |
| `backend/agent_runtime/tools/models.py` | Invocation, execution context, result and status contracts |
| `backend/agent_runtime/tools/pipeline.py` | Governance-gated dispatch and durable event emission |
| `backend/app/core/tool_dispatch.py` | Existing safe parameter injection plus JSON-safe output boundary |
| `backend/app/tests/agent_runtime/test_tool_invocation_pipeline.py` | Allow, deny, approval, event and tenant-isolation tests |
| `docs/architecture/COSA_DEEPSEEK_HARNESS_REFERENCE_ALIGNMENT_AND_RUNTIME_COMPOSITION.md` | Record completion of this Phase-1 slice |

The existing `backend/tools/dispatcher.py` is a separate phase-runtime dispatcher and is not replaced by this plan.

## Public interfaces

```python
class ToolInvocationStatus(str, Enum):
    COMPLETED = "completed"
    DENIED = "denied"
    PENDING_APPROVAL = "pending_approval"
    FAILED = "failed"

class ToolExecutionContext(BaseModel):
    workspace_id: int
    user_id: int | None
    company_id: int | None
    agent_key: str
    session_id: str | None
    run_id: int | None
    correlation_id: str

class ToolInvocation(BaseModel):
    tool_flat_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)

class ToolInvocationResult(BaseModel):
    status: ToolInvocationStatus
    tool_name: str | None
    correlation_id: str
    data: Any | None = None
    error_code: str | None = None
    message: str | None = None
    approval_id: str | None = None
```

```python
class ToolInvocationPipeline:
    def __init__(self, event_store: EventStoreInterface | None = None) -> None: ...

    async def invoke(
        self, db: Session, request: AgentRunRequest, invocation: ToolInvocation,
        *, session_id: str | None = None, run_id: int | None = None,
        correlation_id: str | None = None,
    ) -> ToolInvocationResult: ...
```

## Task 1: Define runtime-neutral contracts

**Files:**
- Create: `backend/agent_runtime/tools/__init__.py`
- Create: `backend/agent_runtime/tools/models.py`
- Test: `backend/app/tests/agent_runtime/test_tool_invocation_pipeline.py`

**Consumes:** Pydantic and standard library only.  
**Produces:** the models above.

- [ ] **Step 1: Write the failing test**

```python
from agent_runtime.tools.models import ToolInvocation, ToolInvocationResult, ToolInvocationStatus

def test_invocation_result_has_normalized_status_and_correlation_id():
    result = ToolInvocationResult(
        status=ToolInvocationStatus.COMPLETED,
        tool_name="finance_summary",
        correlation_id="corr-1",
        data={"revenue": 42},
    )
    assert result.status == ToolInvocationStatus.COMPLETED
    assert ToolInvocation(tool_flat_name="finance_summary").arguments == {}
```

- [ ] **Step 2: Verify RED**

Run: `cd backend && pytest app/tests/agent_runtime/test_tool_invocation_pipeline.py::test_invocation_result_has_normalized_status_and_correlation_id -q`  
Expected: `ModuleNotFoundError: No module named 'agent_runtime.tools'`.

- [ ] **Step 3: Implement minimum contracts**

Create the exact public models above; re-export them from `__init__.py`.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && pytest app/tests/agent_runtime/test_tool_invocation_pipeline.py::test_invocation_result_has_normalized_status_and_correlation_id -q`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/agent_runtime/tools backend/app/tests/agent_runtime/test_tool_invocation_pipeline.py
git commit -m "feat(runtime): add tool invocation contracts"
```

## Task 2: Gate every invocation through governance

**Files:**
- Create: `backend/agent_runtime/tools/pipeline.py`
- Modify: `backend/agent_runtime/tools/__init__.py`
- Modify: `backend/app/tests/agent_runtime/test_tool_invocation_pipeline.py`

**Consumes:** Task-1 models, `GovernanceKernel.evaluate_and_audit_tool_call`, `AgentRunRequest`.  
**Produces:** `ToolInvocationPipeline.invoke` returning a deterministic normalized result.

- [ ] **Step 1: Write failing deny and approval tests**

Register a test `ToolSpec` whose callable increments `calls`.

```python
@pytest.mark.asyncio
async def test_denied_invocation_never_executes_tool_body(db_session):
    calls = 0
    pipeline = ToolInvocationPipeline()
    result = await pipeline.invoke(db_session, denied_request, ToolInvocation(tool_flat_name="test_denied"))
    assert result.status == ToolInvocationStatus.DENIED
    assert calls == 0

@pytest.mark.asyncio
async def test_approval_required_invocation_never_executes_tool_body(db_session):
    result = await ToolInvocationPipeline().invoke(
        db_session, approval_request, ToolInvocation(tool_flat_name="test_approval")
    )
    assert result.status == ToolInvocationStatus.PENDING_APPROVAL
    assert result.approval_id is not None
```

- [ ] **Step 2: Verify RED**

Run: `cd backend && pytest app/tests/agent_runtime/test_tool_invocation_pipeline.py -k 'denied or approval_required' -q`  
Expected: FAIL because `ToolInvocationPipeline` does not exist.

- [ ] **Step 3: Implement gate**

Call the kernel exactly once:

```python
decision = GovernanceKernel.evaluate_and_audit_tool_call(
    db=db, request=request, tool_flat_name=invocation.tool_flat_name,
    args=invocation.arguments, run_id=run_id,
)
```

Map `DENY` to `DENIED`; map `REQUIRE_APPROVAL` to `PENDING_APPROVAL` with `str(decision.approval.id)`. Return before dispatch in both cases. Map a missing `tool_spec` on an allow decision to `FAILED/TOOL_RESOLUTION_FAILED`.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && pytest app/tests/agent_runtime/test_tool_invocation_pipeline.py -k 'denied or approval_required' -q`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/agent_runtime/tools backend/app/tests/agent_runtime/test_tool_invocation_pipeline.py
git commit -m "feat(runtime): gate tool invocations through governance"
```

## Task 3: Safely dispatch and emit durable events

**Files:**
- Modify: `backend/agent_runtime/tools/pipeline.py`
- Modify: `backend/app/tests/agent_runtime/test_tool_invocation_pipeline.py`

**Consumes:** Task-2 pipeline, `execute_tool_spec`, `AgentEvent`, and `EventStoreInterface`.  
**Produces:** `TOOL_REQUESTED` then `TOOL_COMPLETED` for allowed calls.

- [ ] **Step 1: Write the failing allow/event test**

```python
@pytest.mark.asyncio
async def test_allowed_invocation_uses_server_context_and_emits_events(db_session, event_store):
    seen = {}
    result = await ToolInvocationPipeline(event_store).invoke(
        db_session, request_for_workspace_7,
        ToolInvocation(
            tool_flat_name="test_capture_context",
            arguments={"workspace_id": 999, "user_id": 888, "value": "ok"},
        ),
        session_id="session-1", correlation_id="corr-1",
    )
    assert result.status == ToolInvocationStatus.COMPLETED
    assert seen == {"workspace_id": 7, "user_id": 3, "agent_key": "research"}
    assert [event.type for event in await event_store.get_events_by_session("session-1")] == [
        EventType.TOOL_REQUESTED, EventType.TOOL_COMPLETED,
    ]
```

- [ ] **Step 2: Verify RED**

Run: `cd backend && pytest app/tests/agent_runtime/test_tool_invocation_pipeline.py::test_allowed_invocation_uses_server_context_and_emits_events -q`  
Expected: FAIL because allowed dispatch/event emission is missing.

- [ ] **Step 3: Implement dispatch and event emission**

For allowed decisions append `TOOL_REQUESTED` before dispatch when `event_store` and `session_id` are present. Call only:

```python
data = await execute_tool_spec(
    decision.tool_spec, db=db, workspace_id=int(request.workspace_id),
    user_id=int(request.user_id) if request.user_id else None,
    chat_session_id=None, agent_key=request.agent_key, agent_run_id=run_id,
    arguments=decision.sanitized_args or invocation.arguments,
)
```

A dictionary containing `error` maps to `FAILED/TOOL_EXECUTION_FAILED`; otherwise map to `COMPLETED`. In either path append `TOOL_COMPLETED` with tool name, status, correlation ID and safe result/error projection.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && pytest app/tests/agent_runtime/test_tool_invocation_pipeline.py -q`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/agent_runtime/tools/pipeline.py backend/app/tests/agent_runtime/test_tool_invocation_pipeline.py
git commit -m "feat(runtime): dispatch governed tools with runtime events"
```

## Task 4: Add JSON-safe output boundary

**Files:**
- Modify: `backend/app/core/tool_dispatch.py`
- Modify: `backend/agent_runtime/tools/pipeline.py`
- Modify: `backend/app/tests/test_tool_registry.py`
- Modify: `backend/app/tests/agent_runtime/test_tool_invocation_pipeline.py`

**Consumes:** Task-3 implementation.  
**Produces:** no non-JSON-safe result can enter a runtime event/result.

- [ ] **Step 1: Write the failing test**

Add a registered callable returning `object()`, then assert the pipeline returns:

```python
assert result.status == ToolInvocationStatus.FAILED
assert result.error_code == "TOOL_RESULT_NOT_JSON_SAFE"
```

Also assert existing injection safety:

```python
result = await execute_tool_spec(
    spec, db, workspace_id=7, user_id=3, agent_key="research",
    arguments={"workspace_id": 999, "user_id": 888, "agent_key": "attacker"},
)
assert result == {"workspace_id": 7, "user_id": 3, "agent_key": "research"}
```

- [ ] **Step 2: Verify RED**

Run: `cd backend && pytest app/tests/test_tool_registry.py app/tests/agent_runtime/test_tool_invocation_pipeline.py -k 'json_safe or injected' -q`  
Expected: the non-JSON-safe result assertion fails.

- [ ] **Step 3: Implement smallest boundary**

In `tool_dispatch.py`, add:

```python
def ensure_json_safe_tool_result(value: Any) -> Any:
    json.dumps(value, ensure_ascii=False)
    return value
```

Call it after the callable resolves. On `TypeError` or `ValueError`, return:

```python
{"error": "Tool returned a non-JSON-safe result", "error_code": "TOOL_RESULT_NOT_JSON_SAFE"}
```

Preserve the existing error behavior for all other failures. Map that known code in the pipeline.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && pytest app/tests/test_tool_registry.py app/tests/agent_runtime/test_tool_invocation_pipeline.py -k 'json_safe or injected' -q`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/tool_dispatch.py backend/agent_runtime/tools backend/app/tests/test_tool_registry.py backend/app/tests/agent_runtime/test_tool_invocation_pipeline.py
git commit -m "feat(tools): normalize unsafe tool results"
```

## Task 5: Document and verify the slice

**Files:**
- Modify: `docs/architecture/COSA_DEEPSEEK_HARNESS_REFERENCE_ALIGNMENT_AND_RUNTIME_COMPOSITION.md`

**Consumes:** Tasks 1–4.  
**Produces:** documented Phase-1 completion evidence.

- [ ] **Step 1: Record completed scope**

Under Phase 1, add a dated note naming `ToolInvocationPipeline` and state explicitly that legacy entrypoints remain until separately migrated.

- [ ] **Step 2: Run focused regression suite**

```bash
cd backend && pytest \
  app/tests/agent_runtime/test_tool_invocation_pipeline.py \
  app/tests/test_tool_registry.py \
  app/tests/agents/test_governance_policy_approval.py \
  app/tests/agents/test_deepseek_harness_tool_bridge.py -q
```

Expected: PASS. Stop and report any unrelated baseline failure rather than modifying unrelated behavior.

- [ ] **Step 3: Commit**

```bash
git add docs/architecture/COSA_DEEPSEEK_HARNESS_REFERENCE_ALIGNMENT_AND_RUNTIME_COMPOSITION.md
git commit -m "docs: record governed tool pipeline slice"
```

## Coverage and follow-up

- Spec §4.3 and §6 are covered by Tasks 1–4.
- Spec §4.2 and §5.3 are covered by Task 3.
- Spec §8 is intentionally not implemented yet; this slice is the required adapter-safe prerequisite.
- Extension lifecycle is intentionally excluded.

Next plans, in dependency order:

1. Native runtime turn driver using this pipeline.
2. Version-pinned DeepSeek Harness adapter using this pipeline and OpenSandbox boundaries.
3. Profile/skill/workflow composition validation.
4. Reviewed extension package lifecycle and UI projections.

