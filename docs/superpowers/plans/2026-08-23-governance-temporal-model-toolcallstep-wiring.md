# Governance Temporal Model — ToolCallStep Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the monotonic accumulator from Plan 1 (`combine_decisions`/`InvocationGovernanceState`) into `agentos/workflows/tool_step.py::ToolCallStep`, closing a **confirmed, concrete vulnerability**: `ToolCallStep.run()` currently calls `evaluate_access()` fresh on every invocation attempt (including on workflow resume) and branches on that single fresh result alone — so if policy relaxes between the moment a step pauses at `REQUIRE_APPROVAL` and the moment the workflow resumes, the second `evaluate_access()` call can return `ALLOW`, which skips the entire approval-check branch (`agentos/workflows/tool_step.py:112-142`) and invokes the tool directly, with the pending approval never consulted.

**Architecture:** `ToolCallStep` gains an injected `governance_store: GovernanceStateStore` (defaulting to a new `InMemoryGovernanceStateStore`, or a `PostgresGovernanceStateStore` from Plan 2 in production). Every `evaluate_access()` result is wrapped as a minimal `PolicyDecision(outcome=...)` (from `packages/agent_core/governance/contracts.py`, Plan 1) and folded via `combine_decisions` into the invocation's accumulated state, keyed by `f"{run_id}:{tool_name}"` — matching the exact key `ApprovalService.find_by_run_and_action` already uses. `ToolCallStep` branches on the **accumulated** outcome, not the fresh one.

**Tech Stack:** Python 3.11, Pydantic v2, pytest + pytest-asyncio — same as Plans 1/2. No new dependencies.

## Global Constraints

- **Requirement predicates stay out of scope.** `PolicyDecision.requirement` is left `None` throughout this plan. Building `RoleApproval`/`Quorum` predicates would require a "which role must approve this tool" field that does not exist anywhere in `ToolSpecV2` (`agentos/tools/spec.py`) or any of the 17 registered tools today — inventing that mapping now would be exactly the kind of business decision `agentos/core/policy.py:144-150`'s own docstring already warns against fabricating. The outcome lattice alone (`ALLOW`/`DENY`/`REQUIRE_APPROVAL`) is sufficient to close the confirmed vulnerability described above and is the only thing this plan wires up.
- **`agentos/workflows/approval_step.py::ApprovalGateStep` is deliberately excluded from this plan.** It only receives a bare `PermissionClass`, not `role`/`tool_risk_level`/`agent_permission_level` — migrating it to `evaluate_access()` (needed to get a real per-call accumulator observation) requires business input this plan does not have. It keeps calling the legacy `PolicyEngine.evaluate(PermissionClass)` unchanged.
- **`agentos/core/runtime.py`/`executor.py` are out of scope** — V4 froze them as reference/test-only; do not add new integration points there.
- Match existing test conventions exactly: `tests/agentos/workflows/test_workflow_governance.py` already covers `ToolCallStep` end-to-end through `ToolRegistry`/`PolicyEngine`/`ApprovalService`/`ToolSpecV2` (not the older bare `ToolSpec` dataclass) — new tests follow that same fixture style.
- Every existing test in `tests/agentos/workflows/` must still pass unchanged after this plan.
- New/changed code comments explaining *why* go in Vietnamese; identifiers and error messages stay in English (CLAUDE.md rule 19).

---

### Task 1: `InMemoryGovernanceStateStore`

**Files:**
- Create: `packages/agent_core/governance/providers/in_memory.py`
- Create: `tests/agent_core/governance/providers/test_in_memory_store.py`

**Interfaces:**
- Consumes: `GovernanceStateStore` (Plan 2 Task 4), `PinnedSpecIdentity`/`SpecResolutionManifest`/`InvocationGovernanceState`/`PolicyDecision`/`ApprovalEvidence` (Plan 1).
- Produces: `agent_core.governance.providers.in_memory.InMemoryGovernanceStateStore()` — same six-method surface as `PostgresGovernanceStateStore` (Plan 2), structurally satisfying `GovernanceStateStore`. Consumed by Task 2 as `ToolCallStep`'s default.

> If `packages/agent_core/governance/store.py` (Plan 2 Task 4) isn't present yet in the working tree when this task starts, implement it first exactly as specified in `docs/superpowers/plans/2026-08-23-governance-temporal-model-durable-persistence.md` Task 4 before continuing — this task's `isinstance(..., GovernanceStateStore)` check depends on it.

- [ ] **Step 1: Create the directory (if Plan 2 hasn't run yet) and write the failing tests**

```bash
mkdir -p packages/agent_core/governance/providers tests/agent_core/governance/providers
touch packages/agent_core/governance/providers/__init__.py tests/agent_core/governance/providers/__init__.py
```

Create `tests/agent_core/governance/providers/test_in_memory_store.py`:

```python
from __future__ import annotations

import pytest

from agent_core.governance.accumulator import InvocationGovernanceState
from agent_core.governance.contracts import (
    ApprovalEvidence,
    PinnedSpecIdentity,
    PolicyDecision,
    PolicyOutcome,
    RoleApproval,
)
from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent_core.governance.store import GovernanceStateStore


def test_in_memory_store_satisfies_the_governance_state_store_protocol():
    assert isinstance(InMemoryGovernanceStateStore(), GovernanceStateStore)


@pytest.mark.asyncio
async def test_load_manifest_returns_empty_manifest_when_nothing_saved():
    store = InMemoryGovernanceStateStore()

    manifest = await store.load_manifest("run-1")

    assert manifest.entries == ()


@pytest.mark.asyncio
async def test_save_manifest_entry_then_load_returns_it():
    store = InMemoryGovernanceStateStore()
    entry = PinnedSpecIdentity(spec_kind="agent", spec_id="cofounder", spec_version="3", definition_hash="a" * 64)

    await store.save_manifest_entry("run-1", entry)
    manifest = await store.load_manifest("run-1")

    assert manifest.entries == (entry,)


@pytest.mark.asyncio
async def test_load_governance_state_returns_none_when_nothing_saved():
    store = InMemoryGovernanceStateStore()

    result = await store.load_governance_state("run-1", "call-1")

    assert result is None


@pytest.mark.asyncio
async def test_save_and_load_governance_state_roundtrips():
    store = InMemoryGovernanceStateStore()
    decision = PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL, requirement=RoleApproval(role="founder"))
    state = InvocationGovernanceState.start(run_id="run-1", tool_call_id="call-1", initial=decision)

    await store.save_governance_state(state, observation=decision, source="historical")
    loaded = await store.load_governance_state("run-1", "call-1")

    assert loaded is not None
    assert loaded.accumulated == decision


@pytest.mark.asyncio
async def test_list_evidence_returns_empty_list_when_nothing_saved():
    store = InMemoryGovernanceStateStore()

    results = await store.list_evidence("call-1")

    assert results == []


@pytest.mark.asyncio
async def test_save_and_list_evidence_roundtrips_scoped_by_invocation():
    store = InMemoryGovernanceStateStore()
    evidence = ApprovalEvidence(approver="founder-1", scope="call-1", decided_at="2026-08-23T10:00:00Z")

    await store.save_evidence(evidence)
    results = await store.list_evidence("call-1")

    assert results == [evidence]
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/agent_core/governance/providers/test_in_memory_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_core.governance.providers.in_memory'`

- [ ] **Step 3: Implement**

Create `packages/agent_core/governance/providers/in_memory.py`:

```python
from __future__ import annotations

from typing import Optional

from agent_core.governance.contracts import (
    ApprovalEvidence,
    InvocationGovernanceState,
    PinnedSpecIdentity,
    PolicyDecision,
    SpecResolutionManifest,
)


class InMemoryGovernanceStateStore:
    """Cài đặt GovernanceStateStore không cần Postgres — default cho
    ToolCallStep khi không truyền governance_store, và cho unit test không
    cần DB thật. Cùng 6 method với PostgresGovernanceStateStore
    (packages/agent_core/governance/providers/postgres.py) để 2 cài đặt
    hoán đổi được cho nhau qua Protocol GovernanceStateStore."""

    def __init__(self) -> None:
        self._manifests: dict[str, SpecResolutionManifest] = {}
        self._states: dict[tuple[str, str], InvocationGovernanceState] = {}
        self._evidence: dict[str, list[ApprovalEvidence]] = {}

    async def save_manifest_entry(self, run_id: str, entry: PinnedSpecIdentity) -> None:
        manifest = self._manifests.get(run_id, SpecResolutionManifest())
        self._manifests[run_id] = manifest.with_entry(entry)

    async def load_manifest(self, run_id: str) -> SpecResolutionManifest:
        return self._manifests.get(run_id, SpecResolutionManifest())

    async def save_governance_state(
        self, state: InvocationGovernanceState, *, observation: PolicyDecision, source: str
    ) -> None:
        self._states[(state.run_id, state.tool_call_id)] = state

    async def load_governance_state(
        self, run_id: str, tool_call_id: str
    ) -> Optional[InvocationGovernanceState]:
        return self._states.get((run_id, tool_call_id))

    async def save_evidence(self, evidence: ApprovalEvidence) -> None:
        self._evidence.setdefault(evidence.scope, []).append(evidence)

    async def list_evidence(self, scope: str) -> list[ApprovalEvidence]:
        return list(self._evidence.get(scope, []))
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/agent_core/governance/providers/test_in_memory_store.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add packages/agent_core/governance/providers/in_memory.py tests/agent_core/governance/providers/test_in_memory_store.py
git commit -m "feat(agent-core): add InMemoryGovernanceStateStore"
```

---

### Task 2: Wire the accumulator into `ToolCallStep`

**Files:**
- Modify: `agentos/workflows/tool_step.py`
- Modify: `tests/agentos/workflows/test_workflow_governance.py`

**Interfaces:**
- Consumes: `InMemoryGovernanceStateStore` (Task 1), `InvocationGovernanceState`/`PolicyDecision`/`PolicyOutcome` (Plan 1), `GovernanceStateStore` (Plan 2).
- Produces: `ToolCallStep(..., governance_store: Optional[GovernanceStateStore] = None)` — the constructor gains one new optional parameter; `run()`'s external behavior (return type, `StepOutcome` shapes, existing DENY/ALLOW/REQUIRE_APPROVAL cases) is unchanged for every case that doesn't involve a policy change between two `run()` calls on the same invocation.

- [ ] **Step 1: Write the failing regression test proving the confirmed vulnerability**

Append to `tests/agentos/workflows/test_workflow_governance.py`:

```python
from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore


@pytest.mark.asyncio
async def test_tool_call_step_does_not_silently_allow_after_policy_relaxes_mid_pause():
    """Regression test cho lỗ hổng đã xác nhận: ToolCallStep.run() gọi lại
    evaluate_access() mỗi lần resume; nếu chỉ dùng kết quả 'hiện tại' một
    mình, policy nới lỏng giữa lúc pause và lúc resume khiến nhánh
    REQUIRE_APPROVAL/kiểm tra approval bị bỏ qua hoàn toàn, tool chạy thẳng
    không qua approval — xem
    COSA_AGENT_CORE_GOVERNANCE_TEMPORAL_MODEL_2026-08-23.md Case B."""

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

    policy_engine = PolicyEngine()
    approval_svc = ApprovalService()
    governance_store = InMemoryGovernanceStateStore()
    step = ToolCallStep(
        name="step_deploy",
        tool_name="ops.deploy.prod",
        tool_registry=registry,
        policy_engine=policy_engine,
        approval_service=approval_svc,
        governance_store=governance_store,
        role="founder",
        agent_permission_level=PermissionLevel.L3_EXECUTE,
    )

    # 1) approval_policy="always" -> REQUIRE_APPROVAL, tạo pending approval, pause.
    first = await step.run({"workspace_id": "ws1", "run_id": "run-1"})
    assert first.status.value == "WAITING_APPROVAL"
    approval_id = first.approval_id

    # 2) Chưa approve — mô phỏng admin nới lỏng policy trước khi resume.
    registry.get("ops.deploy.prod").approval_policy = "never"

    # 3) Resume gọi lại run(): evaluate_access() mới trả ALLOW ("never"), nhưng
    #    accumulator vẫn giữ REQUIRE_APPROVAL từ lần đầu -> vẫn phải qua approval,
    #    KHÔNG được invoke thẳng handler.
    second = await step.run({"workspace_id": "ws1", "run_id": "run-1"})
    assert second.status.value == "WAITING_APPROVAL"
    assert second.approval_id == approval_id

    # 4) Approve, resume lần 3 -> tool được invoke đúng 1 lần, đúng lúc.
    approval_svc.decide(approval_id, reviewer="founder-1", approved=True)
    third = await step.run({"workspace_id": "ws1", "run_id": "run-1"})
    assert third.status.value == "COMPLETED"
    assert third.updates == {"step_deploy": {"deployed": True}}


@pytest.mark.asyncio
async def test_tool_call_step_without_a_run_id_skips_accumulation_and_behaves_as_before():
    # run_id=None: không có key để accumulate theo — giữ hành vi cũ (chỉ
    # dùng evaluate_access() hiện tại), không raise, không đổi behavior.
    async def read_handler(args):
        return {"ok": True}

    registry = ToolRegistry()
    registry.register(
        ToolSpecV2(
            name="reports.read",
            description="Read report",
            handler=read_handler,
            risk_level=ToolRiskLevel.LOW,
            tool_permission=ToolPermission.READ_ONLY,
        )
    )

    step = ToolCallStep(
        name="step_read",
        tool_name="reports.read",
        tool_registry=registry,
        policy_engine=PolicyEngine(),
        role="founder",
        agent_permission_level=PermissionLevel.L3_EXECUTE,
    )

    outcome = await step.run({"workspace_id": "ws1"})  # không có run_id/workflow_id trong state

    assert outcome.status.value == "COMPLETED"
    assert outcome.updates == {"step_read": {"ok": True}}
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/agentos/workflows/test_workflow_governance.py -v`
Expected: FAIL — `TypeError: ToolCallStep.__init__() got an unexpected keyword argument 'governance_store'`

- [ ] **Step 3: Rewrite `agentos/workflows/tool_step.py`**

Replace the entire contents of `agentos/workflows/tool_step.py` with:

```python
from __future__ import annotations

import string
from typing import Any, Callable, Optional, Union

from agent_core.governance.accumulator import InvocationGovernanceState
from agent_core.governance.contracts import PolicyDecision as GovernancePolicyDecision, PolicyOutcome
from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent_core.governance.store import GovernanceStateStore
from agentos.core.approval import ApprovalService, ApprovalStatus
from agentos.core.policy import (
    ExecutionMode,
    PermissionClass,
    PermissionLevel,
    PolicyDecision as LegacyPolicyDecision,
    PolicyEngine,
    ToolPermission,
    ToolRiskLevel,
)
from agentos.tools.registry import ToolRegistry
from agentos.workflows.models import StepOutcome, StepStatus


class ToolCallStep:
    """A workflow step executing a registered tool via ToolRegistry with
    strict PolicyEngine governance (roadmap §8b.4: mọi step type: tool_call
    đi qua đúng evaluate_access() như tool call bình thường — workflow không
    phải đường tắt bỏ qua governance).

    Mỗi lần run() được gọi (kể cả khi WorkflowEngine gọi lại step này lúc
    resume một workflow đang WAITING_APPROVAL), evaluate_access() được gọi
    lại — governance_store fold kết quả mới vào InvocationGovernanceState đã
    tích luỹ trước đó cho đúng invocation này (key: f"{run_id}:{tool_name}",
    khớp với key ApprovalService.find_by_run_and_action đã dùng), và step
    branch theo outcome ĐÃ TÍCH LUỸ, không phải outcome "hiện tại" một mình
    — nếu không, policy nới lỏng giữa lúc pause và lúc resume sẽ âm thầm bỏ
    qua nhánh REQUIRE_APPROVAL. Xem
    COSA_AGENT_CORE_GOVERNANCE_TEMPORAL_MODEL_2026-08-23.md Case B.
    """

    def __init__(
        self,
        name: str,
        tool_name: str,
        *,
        tool_registry: ToolRegistry,
        policy_engine: Optional[PolicyEngine] = None,
        approval_service: Optional[ApprovalService] = None,
        governance_store: Optional[GovernanceStateStore] = None,
        inputs: Optional[Union[dict[str, Any], Callable[[dict[str, Any]], dict[str, Any]]]] = None,
        output_key: Optional[str] = None,
        role: str = "founder",
        agent_permission_level: PermissionLevel = PermissionLevel.L3_EXECUTE,
        requester: str = "workflow_engine",
        workspace_key: str = "workspace_id",
        correlation_key: str = "correlation_id",
    ) -> None:
        self.name = name
        self.tool_name = tool_name
        self._tool_registry = tool_registry
        self._policy_engine = policy_engine or PolicyEngine()
        self._approval_service = approval_service or ApprovalService()
        self._governance_store = governance_store or InMemoryGovernanceStateStore()
        self._inputs = inputs or {}
        self._output_key = output_key or name
        self._role = role
        self._agent_permission_level = agent_permission_level
        self._requester = requester
        self._workspace_key = workspace_key
        self._correlation_key = correlation_key

    def _resolve_inputs(self, state: dict[str, Any]) -> dict[str, Any]:
        if callable(self._inputs):
            return self._inputs(state)

        resolved = {}
        for k, v in self._inputs.items():
            if isinstance(v, str) and v.startswith("$"):
                # Reference from state, e.g. "$evidence_items" -> state["evidence_items"]
                var_name = v[1:]
                resolved[k] = state.get(var_name)
            elif isinstance(v, str) and "{" in v and "}" in v:
                # String template substitution
                try:
                    resolved[k] = string.Template(v).safe_substitute(state)
                except Exception:
                    resolved[k] = v
            else:
                resolved[k] = v
        return resolved

    async def _accumulate_governance_decision(
        self, run_id: Any, legacy_decision: LegacyPolicyDecision
    ) -> LegacyPolicyDecision:
        if not run_id:
            return legacy_decision

        tool_call_id = f"{run_id}:{self.tool_name}"
        observation = GovernancePolicyDecision(outcome=PolicyOutcome(legacy_decision.value))

        existing = await self._governance_store.load_governance_state(str(run_id), tool_call_id)
        if existing is None:
            state = InvocationGovernanceState.start(
                run_id=str(run_id), tool_call_id=tool_call_id, initial=observation
            )
        else:
            state = existing.accumulate(observation)

        await self._governance_store.save_governance_state(state, observation=observation, source="historical")
        return LegacyPolicyDecision(state.accumulated.outcome.value)

    async def run(self, state: dict[str, Any]) -> StepOutcome:
        spec = self._tool_registry.get(self.tool_name)
        arguments = self._resolve_inputs(state)

        workspace_id = state.get(self._workspace_key)
        correlation_id = state.get(self._correlation_key)
        run_id = state.get("run_id") or state.get("workflow_id")
        tenant_policy = state.get("tenant_policy")
        data_scope = state.get("data_scope")

        permission_enum = (
            PermissionClass(spec.permission_class) if spec.permission_class else None
        )
        approval_policy = getattr(spec, "approval_policy", "conditional")

        legacy_decision = self._policy_engine.evaluate_access(
            role=self._role,
            agent_permission_level=self._agent_permission_level,
            tool_risk_level=spec.risk_level,
            tool_permission=spec.tool_permission,
            tenant_policy=tenant_policy,
            execution_mode=ExecutionMode.APPROVED_WORKFLOW,
            data_scope=data_scope,
            permission_class=permission_enum,
            approval_policy=approval_policy,
            run_id=run_id,
            correlation_id=correlation_id,
            workspace_id=str(workspace_id) if workspace_id else None,
        )

        decision = await self._accumulate_governance_decision(run_id, legacy_decision)

        if decision == LegacyPolicyDecision.DENY:
            return StepOutcome(
                status=StepStatus.FAILED,
                error=f"Tool '{self.tool_name}' denied by policy for permission {spec.permission_class or 'DENY'}",
            )

        if decision == LegacyPolicyDecision.REQUIRE_APPROVAL:
            existing = self._approval_service.find_by_run_and_action(
                str(run_id), self.tool_name
            ) if run_id else None

            if existing is not None:
                if existing.status == ApprovalStatus.APPROVED:
                    pass  # Approved, proceed to execute
                elif existing.status == ApprovalStatus.DENIED:
                    return StepOutcome(
                        status=StepStatus.FAILED,
                        error=f"Approval for tool '{self.tool_name}' was denied: {existing.reason}",
                    )
                else:
                    return StepOutcome(
                        status=StepStatus.WAITING_APPROVAL,
                        approval_id=existing.id,
                    )
            else:
                approval = self._approval_service.request_approval(
                    action=self.tool_name,
                    subject=str(arguments),
                    requester=self._requester,
                    run_id=str(run_id) if run_id else None,
                    tool_name=self.tool_name,
                    correlation_id=correlation_id,
                )
                return StepOutcome(
                    status=StepStatus.WAITING_APPROVAL,
                    approval_id=approval.id,
                )

        try:
            result = await self._tool_registry.invoke(self.tool_name, arguments)
            return StepOutcome(
                status=StepStatus.COMPLETED,
                updates={self._output_key: result},
            )
        except Exception as exc:
            return StepOutcome(
                status=StepStatus.FAILED,
                error=f"Tool '{self.tool_name}' execution failed: {exc}",
            )
```

- [ ] **Step 4: Run the new tests to verify they pass**

Run: `.venv/bin/pytest tests/agentos/workflows/test_workflow_governance.py -v`
Expected: all pass, including the two new tests from Step 1

- [ ] **Step 5: Commit**

```bash
git add agentos/workflows/tool_step.py tests/agentos/workflows/test_workflow_governance.py
git commit -m "fix(agentos): accumulate governance decisions across ToolCallStep resumes to prevent silent policy-relaxation bypass"
```

---

### Task 3: Full regression pass

**Files:** none (verification only)

- [ ] **Step 1: Run the complete `agentos/workflows` suite**

Run: `.venv/bin/pytest tests/agentos/workflows -v`
Expected: all pass, 0 failed — every test that existed before Task 2 (DAG execution, YAML loading, compensation, checkpoint resume, definition registry, approval gate, engine, models, steps, full workflow integration) is unaffected; only `test_workflow_governance.py` gained the two new tests from Task 2.

- [ ] **Step 2: Run the complete `agent_core` suite**

Run: `make agent-core-test`
Expected: all pass (Plan 1 + Plan 2's tests, plus this plan's Task 1 tests, all still green)

- [ ] **Step 3: Run both Makefile targets together, matching CI**

Run: `make agentos-test && make agent-core-test`
Expected: both exit 0

- [ ] **Step 4: Commit (only if Steps 1-3 required no code changes — this task is verification-only; skip the commit if nothing changed)**

If any regression was found and fixed during Steps 1-3, commit that fix separately with a message describing exactly what regressed and why. Otherwise there is nothing to commit for this task.

---

## Self-review notes

- **Spec coverage**: the confirmed vulnerability (fresh `evaluate_access()` on resume bypasses the approval branch when policy relaxes) is directly reproduced and fixed — Task 2's Step 1 regression test is the executable proof. `PinnedSpecIdentity`/`SpecResolutionManifest` wiring (resolving `agent_permission_level`/`execution_mode` from a real manifest instead of the constructor's static params) and the full `ApprovalRequirement` predicate model are **not** covered here — both require data (per-tool approver roles, and a real caller passing a `SpecResolutionManifest`) that doesn't exist in the codebase yet, and are called out explicitly in Global Constraints as deliberately deferred rather than silently dropped.
- **Type consistency**: `ToolCallStep._accumulate_governance_decision` returns `LegacyPolicyDecision` (the `agentos.core.policy` enum) so every existing `if decision == LegacyPolicyDecision.X:` branch below it needs no further changes — verified by re-reading the full rewritten `run()` body against the original.
- **No placeholders**: every step has literal code and an exact pytest command with an expected result.

## Deliberately out of scope (not "next plans" — these need a business decision, not just more engineering)

- **`ApprovalGateStep` ADR-014 cutover** — needs someone to decide what `role`/`tool_risk_level` applies to each existing `ApprovalGateStep` call site; this plan does not invent that data.
- **Per-tool `ApprovalRequirement` predicates** (`RoleApproval`/`Quorum`) — needs a business decision about which role(s) must approve each of the 17 registered tools; `satisfies()` (evidence-vs-predicate matching) has no honest caller until that data exists.
- **`SpecResolutionManifest` wiring into `AgentStep`/kernel resume** — depends on the OpenAI Agents kernel integration (V4 Bước 5) existing first, which is unrelated to `ToolCallStep`.
