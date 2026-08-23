# Governance Temporal Model — Promotion Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close a gap Plan 3 left open — `WorkflowEngine.execute_spec()` rebuilds a brand-new `ToolCallStep` (with a brand-new, empty `InMemoryGovernanceStateStore`) on every call, including resume, so the accumulator Plan 3 wired in never actually survives a resume when driven through the real `WorkflowEngine` path, only when a single `ToolCallStep` object is reused directly (as Plan 3's own test happened to do). This plan (a) threads one shared `governance_store` through `WorkflowEngine`, (b) proves the fix holds at the `execute_spec()` level, (c) proves the governance accumulator survives a real Postgres-backed process restart, and (d) proves workflow-version pinning (Plan 1) holds through a full pause/approve/resume cycle — the "promotion gate" tests V4 Bước 9 calls for, scoped to what this codebase can actually support today.

**Architecture:** No new packages. `agentos/workflows/engine.py::WorkflowEngine` gains a `governance_store` constructor param (default `InMemoryGovernanceStateStore`) and threads it into every `ToolCallStep` it builds. New tests live in `tests/agentos/workflows/test_workflow_governance.py` (in-memory, engine-level) and a new `tests/agentos/workflows/test_governance_durability_integration.py` (real Postgres, `AGENTOS_TEST_DATABASE_URL`-gated, mirroring Plan 2's integration test pattern).

**Tech Stack:** Python 3.11, Pydantic v2, pytest + pytest-asyncio, PostgreSQL via `docker-compose.yml`'s `postgres` service. No new dependencies.

## Global Constraints

- **This plan requires Plan 3 to have landed first** (`ToolCallStep.__init__` must already accept `governance_store`) — verify with `grep -n governance_store agentos/workflows/tool_step.py` before starting; if empty, implement `docs/superpowers/plans/2026-08-23-governance-temporal-model-toolcallstep-wiring.md` first.
- **`AgentSpec`/`ExecutionKernel` do not exist anywhere in this codebase yet** (confirmed: `grep -rln "class AgentSpec" agentos packages` returns nothing) — the "AgentSpec widen/narrow" promotion test from the original governance temporal model doc's Bước 9 list is **not** in this plan. Writing it now would mean inventing the very contract it's supposed to test against. It becomes a real task once V4 Bước 3/5 ship an actual `AgentSpec`/kernel-resume path.
- **No tenant-suspension/workspace-status concept exists anywhere in `agentos/`** (confirmed: `grep -rln "suspended\|tenant_status\|workspace_status" agentos` returns nothing) — the "Run-level ambient suspend/resume" promotion test is **also not** in this plan for the same reason: there is no real `RunLevelCurrentGate` data source to test against yet. This needs its own feature plan (a tenant/workspace status mechanism) before it can be tested honestly.
- **`agentos/core/approval.py::ApprovalService` is still in-memory** (Plan 2 and Plan 3 both deliberately left it that way). Task 3 below tests only what is actually durable — the accumulated `PolicyDecision` via `GovernanceStateStore` — not the full approval lifecycle. Do not write a test that pretends `ApprovalService` survives a restart; it doesn't yet.
- Every existing test must still pass unchanged.
- New/changed code comments explaining *why* go in Vietnamese; identifiers and error messages stay in English (CLAUDE.md rule 19).

---

### Task 1: Thread `governance_store` through `WorkflowEngine`

**Files:**
- Modify: `agentos/workflows/engine.py`
- Modify: `tests/agentos/workflows/test_workflow_governance.py`

**Interfaces:**
- Consumes: `GovernanceStateStore` (Plan 2), `InMemoryGovernanceStateStore` (Plan 3 Task 1).
- Produces: `WorkflowEngine(..., governance_store: Optional[GovernanceStateStore] = None)` — every `ToolCallStep` the engine builds (via `_build_executable_step`/`build_steps_from_spec`) now shares the same `governance_store` instance across calls on the same engine, including resume.

- [x] **Step 1: Write the failing test — same engine instance, two `execute_spec` calls, must share accumulator state**

Append to `tests/agentos/workflows/test_workflow_governance.py`:

```python
@pytest.mark.asyncio
async def test_workflow_engine_shares_governance_state_across_execute_spec_calls_on_the_same_engine():
    """Bug bị Plan 3 bỏ sót: _build_executable_step tạo ToolCallStep mới mỗi
    lần execute_spec() được gọi (kể cả lúc resume), nên nếu WorkflowEngine
    không tự giữ 1 governance_store dùng chung, mỗi ToolCallStep mới nhận
    1 InMemoryGovernanceStateStore rỗng riêng — accumulator không thực sự
    sống sót qua resume ở tầng WorkflowEngine, dù ToolCallStep tự nó đã
    đúng. Test này xác nhận WorkflowEngine tự thread governance_store qua
    các lần build step."""
    async def deploy_handler(args):
        return {"deployed": True}

    registry = ToolRegistry()
    registry.register(
        ToolSpecV2(
            name="ops.deploy.prod",
            description="Deploy prod",
            handler=deploy_handler,
            risk_level=ToolRiskLevel.HIGH,
            tool_permission=ToolPermission.ADMIN_WRITE,
            approval_policy="always",
        )
    )

    approval_svc = ApprovalService()
    engine = WorkflowEngine(tool_registry=registry, policy_engine=PolicyEngine(), approval_service=approval_svc)

    spec = WorkflowSpec(id="deploy-flow", steps=[WorkflowStepSpec(id="deploy", type=StepType.TOOL_CALL, tool="ops.deploy.prod")])

    workflow = await engine.execute_spec(spec, initial_state={"workspace_id": "ws1", "workflow_id": "wf-1"})
    assert workflow.status == WorkflowStatus.WAITING_APPROVAL
    approval_id = workflow.pending_approval_id

    # Policy nới lỏng trước khi resume.
    registry.get("ops.deploy.prod").approval_policy = "never"

    # Resume qua execute_spec (rebuild ToolCallStep mới bên trong) — PHẢI vẫn
    # thấy WAITING_APPROVAL với đúng approval_id cũ, không được bỏ qua.
    resumed_before_approve = await engine.execute_spec(spec, initial_state={}, workflow=workflow)
    assert resumed_before_approve.status == WorkflowStatus.WAITING_APPROVAL
    assert resumed_before_approve.pending_approval_id == approval_id

    approval_svc.decide(approval_id, reviewer="founder-1", approved=True)
    final = await engine.execute_spec(spec, initial_state={}, workflow=resumed_before_approve)
    assert final.status == WorkflowStatus.COMPLETED
    assert final.state == {"deploy": {"deployed": True}}
```

- [x] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/agentos/workflows/test_workflow_governance.py -v -k shares_governance_state`
Expected: FAIL — `resumed_before_approve.status` is `COMPLETED` instead of `WAITING_APPROVAL` (the bug: a fresh `ToolCallStep` with a fresh empty `InMemoryGovernanceStateStore` sees only the relaxed "never" policy and invokes the tool immediately, skipping approval entirely)

- [x] **Step 3: Add `governance_store` to `WorkflowEngine`**

In `agentos/workflows/engine.py`, add these two imports to the existing import block at the top of the file:

```python
from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent_core.governance.store import GovernanceStateStore
```

Change the `__init__` method from:

```python
    def __init__(
        self,
        *,
        tool_registry: Optional[ToolRegistry] = None,
        policy_engine: Optional[PolicyEngine] = None,
        approval_service: Optional[ApprovalService] = None,
    ) -> None:
        self._tool_registry = tool_registry or ToolRegistry()
        self._policy_engine = policy_engine or PolicyEngine()
        self._approval_service = approval_service or ApprovalService()
```

to:

```python
    def __init__(
        self,
        *,
        tool_registry: Optional[ToolRegistry] = None,
        policy_engine: Optional[PolicyEngine] = None,
        approval_service: Optional[ApprovalService] = None,
        governance_store: Optional[GovernanceStateStore] = None,
    ) -> None:
        self._tool_registry = tool_registry or ToolRegistry()
        self._policy_engine = policy_engine or PolicyEngine()
        self._approval_service = approval_service or ApprovalService()
        self._governance_store = governance_store or InMemoryGovernanceStateStore()
```

Then, inside `_build_executable_step`, change the `ToolCallStep(...)` construction from:

```python
            return ToolCallStep(
                name=step_spec.id,
                tool_name=step_spec.tool,
                tool_registry=self._tool_registry,
                policy_engine=self._policy_engine,
                approval_service=self._approval_service,
                inputs=step_spec.inputs,
                output_key=step_spec.output_key or step_spec.id,
                **step_kwargs,
            )
```

to:

```python
            return ToolCallStep(
                name=step_spec.id,
                tool_name=step_spec.tool,
                tool_registry=self._tool_registry,
                policy_engine=self._policy_engine,
                approval_service=self._approval_service,
                governance_store=self._governance_store,
                inputs=step_spec.inputs,
                output_key=step_spec.output_key or step_spec.id,
                **step_kwargs,
            )
```

- [x] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/agentos/workflows/test_workflow_governance.py -v -k shares_governance_state`
Expected: 1 passed

- [x] **Step 5: Run the full governance test file to confirm no regression from Plan 3**

Run: `.venv/bin/pytest tests/agentos/workflows/test_workflow_governance.py -v`
Expected: all pass, including Plan 3's two tests

- [x] **Step 6: Commit**

```bash
git add agentos/workflows/engine.py tests/agentos/workflows/test_workflow_governance.py
git commit -m "fix(agentos): share one governance_store across WorkflowEngine's rebuilt ToolCallSteps so the accumulator survives resume"
```

---

### Task 2: Full end-to-end workflow-version-drift test through `WorkflowEngine`

**Files:**
- Modify: `tests/agentos/workflows/test_definition_registry.py`

**Interfaces:**
- Consumes: `WorkflowDefinitionRegistry` (Plan 1 Task 6), `WorkflowEngine` (Task 1 of this plan).

- [x] **Step 1: Write the failing test**

Append to `tests/agentos/workflows/test_definition_registry.py` (add `ApprovalService`, `PolicyEngine`, `ToolPermission`, `ToolRiskLevel`, `ToolRegistry`, `ToolSpecV2` to its imports first — see Step 2):

```python
@pytest.mark.asyncio
async def test_resume_completes_the_pinned_version_end_to_end_even_after_a_newer_version_is_registered():
    """Bản đầy đủ qua WorkflowEngine.execute_spec thật (Plan 1 Task 6 chỉ
    test registry.build_steps() trực tiếp) — pause tại 1 approval gate thật,
    publish v2 giữa chừng, resume: workflow phải hoàn tất đúng theo v1, bước
    thêm của v2 (notify) không được lẫn vào completed_steps."""

    async def deploy_handler(args):
        return {"deployed": True}

    async def notify_handler(args):
        return {"notified": True}

    registry = ToolRegistry()
    registry.register(
        ToolSpecV2(
            name="ops.deploy.prod",
            description="Deploy",
            handler=deploy_handler,
            risk_level=ToolRiskLevel.HIGH,
            tool_permission=ToolPermission.ADMIN_WRITE,
            approval_policy="always",
        )
    )
    registry.register(
        ToolSpecV2(
            name="ops.notify",
            description="Notify",
            handler=notify_handler,
            risk_level=ToolRiskLevel.LOW,
            tool_permission=ToolPermission.READ_ONLY,
        )
    )

    definitions = WorkflowDefinitionRegistry()
    spec_v1 = WorkflowSpec(
        id="deploy-flow", steps=[WorkflowStepSpec(id="deploy", type=StepType.TOOL_CALL, tool="ops.deploy.prod")]
    )
    definitions.register_version(spec_v1)

    approval_svc = ApprovalService()
    engine = WorkflowEngine(tool_registry=registry, policy_engine=PolicyEngine(), approval_service=approval_svc)

    workflow = await engine.execute_spec(spec_v1, initial_state={"workspace_id": "ws1", "workflow_id": "wf-drift"})
    assert workflow.status == WorkflowStatus.WAITING_APPROVAL
    approval_id = workflow.pending_approval_id

    # Publish v2 "giữa chừng" — workflow đang pause không được biết tới nó.
    spec_v2 = WorkflowSpec(
        id="deploy-flow",
        steps=[
            WorkflowStepSpec(id="deploy", type=StepType.TOOL_CALL, tool="ops.deploy.prod"),
            WorkflowStepSpec(id="notify", type=StepType.TOOL_CALL, tool="ops.notify"),
        ],
    )
    definitions.register_version(spec_v2)

    approval_svc.decide(approval_id, reviewer="founder-1", approved=True)

    # Resume dùng đúng spec_v1 đã pin — KHÔNG gọi definitions.current_version(),
    # giờ đã trỏ v2.
    resumed = await engine.execute_spec(spec_v1, initial_state={}, workflow=workflow)

    assert resumed.status == WorkflowStatus.COMPLETED
    assert resumed.state == {"deploy": {"deployed": True}}
    assert "notify" not in resumed.completed_steps
```

- [x] **Step 2: Add the required imports to the top of `tests/agentos/workflows/test_definition_registry.py`**

Change the import block from:

```python
import pytest

from agentos.workflows.definition_registry import (
    WorkflowDefinitionNotFoundError,
    WorkflowDefinitionRegistry,
    WorkflowVersionNotFoundError,
)
from agentos.workflows.engine import WorkflowEngine
from agentos.workflows.models import WorkflowStatus
from agentos.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec
from agentos.workflows.steps import DeterministicStep
```

to:

```python
import pytest

from agentos.core.approval import ApprovalService
from agentos.core.policy import PolicyEngine, ToolPermission, ToolRiskLevel
from agentos.tools.registry import ToolRegistry
from agentos.tools.spec import ToolSpecV2
from agentos.workflows.definition_registry import (
    WorkflowDefinitionNotFoundError,
    WorkflowDefinitionRegistry,
    WorkflowVersionNotFoundError,
)
from agentos.workflows.engine import WorkflowEngine
from agentos.workflows.models import WorkflowStatus
from agentos.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec
from agentos.workflows.steps import DeterministicStep
```

- [x] **Step 3: Run to verify it passes**

Run: `.venv/bin/pytest tests/agentos/workflows/test_definition_registry.py -v`
Expected: all pass (12 from Plan 1 + this new one = 13 passed)

- [x] **Step 4: Commit**

```bash
git add tests/agentos/workflows/test_definition_registry.py
git commit -m "test(agentos): prove workflow-version pinning end to end through WorkflowEngine.execute_spec"
```

---

### Task 3: Governance state durability across a real, simulated process restart

**Files:**
- Create: `tests/agentos/workflows/test_governance_durability_integration.py`

**Interfaces:**
- Consumes: `PostgresGovernanceStateStore` (Plan 2), the `agent_core_governance` schema (Plan 2's migration `agentos/migrations/002_governance_temporal_model.sql`).

- [x] **Step 1: Write the integration test, gated exactly like Plan 2 Task 8's**

Create `tests/agentos/workflows/test_governance_durability_integration.py`:

```python
"""Integration test: InvocationGovernanceState (đã tích luỹ tại request-time)
sống sót qua 1 lần 'restart process' mô phỏng — 2 PostgresGovernanceStateStore
instance riêng biệt (không share object Python nào), chỉ cùng trỏ 1 Postgres.

ApprovalService vẫn in-memory (chưa nằm trong scope các plan này) nên test
này KHÔNG cố chứng minh toàn bộ approval lifecycle durable — chỉ đúng phần
đã thật sự durable: accumulated PolicyDecision qua GovernanceStateStore.

Yêu cầu env var `AGENTOS_TEST_DATABASE_URL` trỏ tới 1 Postgres đã chạy
migration `agentos/migrations/002_governance_temporal_model.sql`. Bỏ qua
(skip) nếu biến này không được set.
"""
from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio

pytest.importorskip("asyncpg")

TEST_DATABASE_URL = os.environ.get("AGENTOS_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="AGENTOS_TEST_DATABASE_URL not set — skipping real-Postgres integration test",
)


@pytest_asyncio.fixture
async def session_factory():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_accumulated_governance_state_survives_a_simulated_process_restart(session_factory):
    from agent_core.governance.accumulator import InvocationGovernanceState
    from agent_core.governance.contracts import PolicyDecision, PolicyOutcome, RoleApproval
    from agent_core.governance.providers.postgres import PostgresGovernanceStateStore

    run_id = f"run-{uuid.uuid4().hex[:8]}"
    tool_call_id = "ops.deploy.prod"

    # "Process 1": request-time decision — risk cao -> REQUIRE_APPROVAL, persist.
    store_process_1 = PostgresGovernanceStateStore(db_session_factory=session_factory)
    request_time = PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL, requirement=RoleApproval(role="founder"))
    state = InvocationGovernanceState.start(run_id=run_id, tool_call_id=tool_call_id, initial=request_time)
    await store_process_1.save_governance_state(state, observation=request_time, source="historical")
    del store_process_1  # mô phỏng process 1 kết thúc — không object nào còn sống

    # "Process 2": store instance HOÀN TOÀN mới, chỉ cùng trỏ Postgres đó.
    store_process_2 = PostgresGovernanceStateStore(db_session_factory=session_factory)
    loaded = await store_process_2.load_governance_state(run_id, tool_call_id)
    assert loaded is not None
    assert loaded.accumulated == request_time

    # Policy đã nới lỏng (ALLOW) trước khi resume — constraint cũ không được xoá.
    resume_time = PolicyDecision(outcome=PolicyOutcome.ALLOW)
    combined = loaded.accumulate(resume_time)
    await store_process_2.save_governance_state(combined, observation=resume_time, source="historical")

    final = await store_process_2.load_governance_state(run_id, tool_call_id)
    assert final is not None
    assert final.accumulated.outcome == PolicyOutcome.REQUIRE_APPROVAL
    assert final.accumulated.requirement == RoleApproval(role="founder")
```

- [x] **Step 2: Run without a database configured — confirm it skips cleanly**

Run: `.venv/bin/pytest tests/agentos/workflows/test_governance_durability_integration.py -v`
Expected: 1 skipped

- [x] **Step 3: Run against a real local Postgres**

Run:
```bash
docker compose up -d postgres
until docker compose exec -T postgres pg_isready -U ${POSTGRES_USER:-javis}; do sleep 1; done
psql "${DATABASE_URL:-postgresql://javis_app:change-me-javis-app@localhost:5432/javis}" -f agentos/migrations/002_governance_temporal_model.sql
AGENTOS_TEST_DATABASE_URL="postgresql+asyncpg://javis_app:change-me-javis-app@localhost:5432/javis" \
  .venv/bin/pytest tests/agentos/workflows/test_governance_durability_integration.py -v
```
Expected: 1 passed

- [x] **Step 4: Commit**

```bash
git add tests/agentos/workflows/test_governance_durability_integration.py
git commit -m "test(agentos): prove accumulated governance state survives a simulated process restart via Postgres"
```

---

### Task 4: Full regression pass

**Files:** none (verification only)

- [x] **Step 1: Run the complete `agentos/workflows` suite**

Run: `.venv/bin/pytest tests/agentos/workflows -v`
Expected: all pass, 0 failed

- [x] **Step 2: Run the complete `agent_core` suite**

Run: `make agent-core-test`
Expected: all pass

- [x] **Step 3: Run both Makefile targets together**

Run: `make agentos-test && make agent-core-test`
Expected: both exit 0

- [x] **Step 4: Run the durability integration test against real Postgres one more time as the final gate**

Run:
```bash
AGENTOS_TEST_DATABASE_URL="postgresql+asyncpg://javis_app:change-me-javis-app@localhost:5432/javis" \
  .venv/bin/pytest tests/agentos/workflows/test_governance_durability_integration.py tests/agent_core/governance/providers/test_postgres_store_integration.py -v
```
Expected: all pass

- [x] **Step 5: Commit (only if a regression was found and fixed in Steps 1-4)**

If everything passed with no code changes needed, there is nothing to commit for this task.

---

## Self-review notes

- **Spec coverage**: of the 5 promotion-test groups in the original governance temporal model doc's Bước 9, this plan delivers 2 fully ("workflow-version-drift" as Task 2, and durable governance-state resume as Task 3, plus the risk-drift scenarios already covered by Plan 3's regression test now proven durable at the engine level by Task 1's fix), and explicitly declines the other 2 (AgentSpec widen/narrow, Run-level ambient suspend/resume) with the concrete reason each requires a contract or data source that does not exist in this codebase yet — see Global Constraints. Declining with a reason is the correct outcome here, not a gap to paper over with a speculative test.
- **The most valuable finding in this plan is Task 1**, not a new feature — it's a real bug in how Plan 3's fix composes with `WorkflowEngine`, caught by tracing the actual `_build_executable_step` call path rather than assuming the unit-level fix generalizes. This is exactly what a promotion gate is for.
- **Type consistency**: `WorkflowEngine.__init__`'s new `governance_store` parameter and `_build_executable_step`'s `ToolCallStep(..., governance_store=self._governance_store)` call use the same `GovernanceStateStore` type Plan 2/3 already defined — no new type introduced.
- **No placeholders**: every step has literal code and an exact command with an expected result.

## What's left after this plan (genuinely blocked on other work, not on more test-writing)

- **AgentSpec widen/narrow promotion test** — blocked on V4 Bước 3/4/5 shipping a real `AgentSpec` + kernel-resume path.
- **Run-level ambient suspend/resume promotion test** — blocked on a tenant/workspace status feature that doesn't exist yet; that feature needs its own plan with real product requirements, not a fabricated schema invented to make a test pass.
- **Durable `ApprovalService`** — still in-memory; a full "kill process, resume, approval survives" test (as opposed to this plan's "governance decision survives") needs that rewrite first.
- **`ApprovalGateStep` ADR-014 cutover and per-tool `ApprovalRequirement` predicates** — as noted in Plan 3, both need a business decision this plan cannot make.
