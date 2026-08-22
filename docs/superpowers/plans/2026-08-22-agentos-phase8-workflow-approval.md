# AgentOS Phase 8 — Workflow & Approval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic `PolicyEngine` (blueprint §30/§50: ALLOW/DENY/REQUIRE_APPROVAL over a closed set of permission classes), an `Approval` object + `ApprovalService` (blueprint §49), and a `WorkflowEngine` that runs the blueprint's own worked example (§47: Start → Agent Research → Human Approval → Business Write → Notify → End) — mixing deterministic business steps, agent-reasoning steps, and a pausable/resumable approval gate in one linear pipeline. Per Phase 8 of the roadmap in `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §4.

**Architecture:** `PolicyEngine` and `ApprovalService` land in `backend/agentos/core/` — the blueprint's own `AgentRuntime` component breakdown (§5.3) lists `PolicyEngine` as a core runtime component, and `Approval` is the tightly-coupled object a `REQUIRE_APPROVAL` policy decision produces. `PolicyEngine.evaluate(permission)` is a plain dict lookup against a default table matching the blueprint's §86 MVP autonomy defaults (read/analysis auto-allow, `ACCESS_SECRET` denied outright, external communication/delete/finance/deploy/business-data-writes require approval) — no LLM call, ever (CLAUDE.md §11 / blueprint §11: permissions are enforced by deterministic code). `ApprovalService` is an in-memory store of `Approval` objects (id/action/subject/requester/reviewer/status/reason, per §49), each created `PENDING` and decided exactly once. A new `backend/agentos/workflows/` subpackage (matching the blueprint's own top-level `agentos/` layout, §2) holds `Workflow`/`WorkflowStatus` (a state machine following the exact `AgentRun.transition()` pattern from Phase 0 — `PENDING → RUNNING → {WAITING_APPROVAL, COMPLETED, FAILED, CANCELLED}`, with `WAITING_APPROVAL → RUNNING` the resume path), a `WorkflowStep` protocol with three implementations — `DeterministicStep` (a plain callable, for business logic that must never be an LLM judgment call per §45), `AgentStep` (wraps any Phase 1 `Agent`), and `ApprovalGateStep` (consults `PolicyEngine`; on `REQUIRE_APPROVAL` it creates a pending `Approval` and returns a "pause here" outcome) — and a `WorkflowEngine` that runs a list of steps, halting the whole `Workflow` at `WAITING_APPROVAL` and resuming it later once the pending `Approval` is decided. The final task assembles the blueprint's exact example workflow using a real `AgentStep` backed by a real Phase 1 `AgentRuntime`, proving both the approved and denied paths end-to-end.

**Tech Stack:** Python 3.11, pydantic 2.13, pytest + pytest-asyncio — same as prior `agentos` phases, no new dependencies.

## Global Constraints

- New files only: `backend/agentos/core/policy.py`, `backend/agentos/core/approval.py` (new files inside the already-established `core/` package — do not modify any existing file in `core/`), and the entire new `backend/agentos/workflows/` subpackage.
- **Prerequisite:** this plan assumes Phase 1's `Agent` protocol, `TaskContext`, `AgentResult`, `AgentRunStatus`, `AgentRuntime`, `StubModelProvider`, and `ToolRegistry` already exist (Task 7 exercises them directly).
- `Workflow.transition()` follows exactly the pattern established by `AgentRun.transition()` in Phase 0 (`_ALLOWED_TRANSITIONS` dict keyed by current status, a typed exception on an illegal transition) — reuse that shape, don't invent a different state-machine style.
- `PolicyEngine`'s default table is a plain Python dict, constructible with an override table for tests — never add a rule that requires a network call or LLM judgment to evaluate.
- `ApprovalService` and its `Approval` objects are in-memory only (same MVP tradeoff as `InMemoryMemoryStore` in Phase 3 and `SkillRegistry` in Phase 4) — persistence and any real notification transport (email/Slack) are later hardening, not this plan.
- A paused `Workflow` only remembers `pending_approval_id` and `current_step_index` — `WorkflowEngine.resume()` requires the caller to pass the same `steps` list used in `start()`; the engine does not serialize/reconstruct step objects.
- Every async test needs `@pytest.mark.asyncio` (`backend/pytest.ini` has `asyncio_mode = strict`).
- Run tests via: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/core/<file> -v` and `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/workflows/<file> -v`.
- Source spec: `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §3.7 (Governance), §30 (Permission Model), §45 (Business vs Agent Workflow), §47 (Workflow Engine), §49 (Approval Model), §50 (Policy Engine), §86 (MVP autonomy defaults), §4 (Phase 8 scope).

---

## File Structure

```text
backend/agentos/core/
├── policy.py           # PermissionClass, PolicyDecision, DEFAULT_POLICY_TABLE, PolicyEngine
└── approval.py            # Approval, ApprovalStatus, ApprovalService, ApprovalNotFoundError, ApprovalAlreadyDecidedError

backend/agentos/workflows/
├── __init__.py
├── models.py             # WorkflowStatus, Workflow, InvalidWorkflowTransition, StepStatus, StepOutcome
├── steps.py                # WorkflowStep protocol, DeterministicStep, AgentStep
├── approval_step.py           # ApprovalGateStep
└── engine.py                     # WorkflowEngine

backend/tests/agentos/core/
├── test_policy.py
└── test_approval.py

backend/tests/agentos/workflows/
├── __init__.py
├── test_models.py
├── test_steps.py
├── test_approval_step.py
├── test_engine.py
└── test_full_workflow_integration.py
```

---

### Task 1: `PermissionClass` + `PolicyDecision` + `PolicyEngine`

**Files:**
- Create: `backend/agentos/core/policy.py`
- Test: `backend/tests/agentos/core/test_policy.py`

**Interfaces:**
- Produces: `PermissionClass` (str enum: `READ_LOCAL`, `WRITE_WORKSPACE`, `READ_NETWORK`, `EXTERNAL_WRITE`, `SEND_MESSAGE`, `MODIFY_BUSINESS_DATA`, `DEPLOY`, `EXECUTE_CODE`, `ACCESS_SECRET`, `DELETE_DATA`, `FINANCIAL_ACTION`); `PolicyDecision` (str enum: `ALLOW`, `DENY`, `REQUIRE_APPROVAL`); `DEFAULT_POLICY_TABLE: dict[PermissionClass, PolicyDecision]`; `PolicyEngine(table: dict[PermissionClass, PolicyDecision] | None = None)` with `.evaluate(permission: PermissionClass) -> PolicyDecision`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/core/test_policy.py
from agentos.core.policy import PermissionClass, PolicyDecision, PolicyEngine


def test_read_local_is_allowed_by_default():
    engine = PolicyEngine()
    assert engine.evaluate(PermissionClass.READ_LOCAL) == PolicyDecision.ALLOW


def test_access_secret_is_denied_by_default():
    engine = PolicyEngine()
    assert engine.evaluate(PermissionClass.ACCESS_SECRET) == PolicyDecision.DENY


def test_financial_action_requires_approval_by_default():
    engine = PolicyEngine()
    assert engine.evaluate(PermissionClass.FINANCIAL_ACTION) == PolicyDecision.REQUIRE_APPROVAL


def test_custom_table_overrides_default():
    engine = PolicyEngine({PermissionClass.SEND_MESSAGE: PolicyDecision.ALLOW})
    assert engine.evaluate(PermissionClass.SEND_MESSAGE) == PolicyDecision.ALLOW
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/core/test_policy.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.core.policy'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/core/policy.py
from __future__ import annotations

import enum


class PermissionClass(str, enum.Enum):
    READ_LOCAL = "READ_LOCAL"
    WRITE_WORKSPACE = "WRITE_WORKSPACE"
    READ_NETWORK = "READ_NETWORK"
    EXTERNAL_WRITE = "EXTERNAL_WRITE"
    SEND_MESSAGE = "SEND_MESSAGE"
    MODIFY_BUSINESS_DATA = "MODIFY_BUSINESS_DATA"
    DEPLOY = "DEPLOY"
    EXECUTE_CODE = "EXECUTE_CODE"
    ACCESS_SECRET = "ACCESS_SECRET"
    DELETE_DATA = "DELETE_DATA"
    FINANCIAL_ACTION = "FINANCIAL_ACTION"


class PolicyDecision(str, enum.Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


DEFAULT_POLICY_TABLE: dict[PermissionClass, PolicyDecision] = {
    PermissionClass.READ_LOCAL: PolicyDecision.ALLOW,
    PermissionClass.WRITE_WORKSPACE: PolicyDecision.ALLOW,
    PermissionClass.READ_NETWORK: PolicyDecision.ALLOW,
    PermissionClass.EXTERNAL_WRITE: PolicyDecision.REQUIRE_APPROVAL,
    PermissionClass.SEND_MESSAGE: PolicyDecision.REQUIRE_APPROVAL,
    PermissionClass.MODIFY_BUSINESS_DATA: PolicyDecision.REQUIRE_APPROVAL,
    PermissionClass.DEPLOY: PolicyDecision.REQUIRE_APPROVAL,
    PermissionClass.EXECUTE_CODE: PolicyDecision.REQUIRE_APPROVAL,
    PermissionClass.ACCESS_SECRET: PolicyDecision.DENY,
    PermissionClass.DELETE_DATA: PolicyDecision.REQUIRE_APPROVAL,
    PermissionClass.FINANCIAL_ACTION: PolicyDecision.REQUIRE_APPROVAL,
}


class PolicyEngine:
    """Deterministic ALLOW/DENY/REQUIRE_APPROVAL gate (blueprint §50) — a
    policy decision is code, never an LLM judgment call (CLAUDE.md §11 /
    blueprint §11). The default table follows the blueprint §86 MVP
    autonomy defaults: read/analysis auto-allow; external communication,
    business-data writes, delete, finance, deploy, and code execution
    require approval; secret access is denied outright.
    """

    def __init__(self, table: dict[PermissionClass, PolicyDecision] | None = None) -> None:
        self._table = dict(table) if table is not None else dict(DEFAULT_POLICY_TABLE)

    def evaluate(self, permission: PermissionClass) -> PolicyDecision:
        return self._table.get(permission, PolicyDecision.REQUIRE_APPROVAL)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/core/test_policy.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/core/policy.py backend/tests/agentos/core/test_policy.py
git commit -m "feat(agentos): add PermissionClass and PolicyEngine"
```

---

### Task 2: `Approval` + `ApprovalService`

**Files:**
- Create: `backend/agentos/core/approval.py`
- Test: `backend/tests/agentos/core/test_approval.py`

**Interfaces:**
- Produces: `ApprovalStatus` (str enum: `PENDING`, `APPROVED`, `DENIED`); `Approval(id: str, action: str, subject: str, requester: str, status: ApprovalStatus = PENDING, reviewer: str | None, reason: str | None, created_at: datetime, decided_at: datetime | None)`; `ApprovalNotFoundError(approval_id: str)`; `ApprovalAlreadyDecidedError(approval_id: str, status: ApprovalStatus)`; `ApprovalService` with `.request_approval(*, action: str, subject: str, requester: str) -> Approval`, `.get(approval_id: str) -> Approval`, `.decide(approval_id: str, *, reviewer: str, approved: bool, reason: str | None = None) -> Approval`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/core/test_approval.py
import pytest

from agentos.core.approval import (
    ApprovalAlreadyDecidedError,
    ApprovalNotFoundError,
    ApprovalService,
    ApprovalStatus,
)


def test_request_approval_starts_pending():
    service = ApprovalService()
    approval = service.request_approval(action="send_email", subject="campaign-1", requester="sales_agent")
    assert approval.status == ApprovalStatus.PENDING
    assert approval.reviewer is None


def test_decide_approves():
    service = ApprovalService()
    approval = service.request_approval(action="send_email", subject="campaign-1", requester="sales_agent")

    decided = service.decide(approval.id, reviewer="founder", approved=True, reason="looks good")

    assert decided.status == ApprovalStatus.APPROVED
    assert decided.reviewer == "founder"
    assert decided.decided_at is not None


def test_decide_denies():
    service = ApprovalService()
    approval = service.request_approval(action="send_email", subject="campaign-1", requester="sales_agent")

    decided = service.decide(approval.id, reviewer="founder", approved=False, reason="not ready")

    assert decided.status == ApprovalStatus.DENIED


def test_get_missing_approval_raises():
    service = ApprovalService()
    with pytest.raises(ApprovalNotFoundError):
        service.get("missing")


def test_decide_twice_raises():
    service = ApprovalService()
    approval = service.request_approval(action="send_email", subject="campaign-1", requester="sales_agent")
    service.decide(approval.id, reviewer="founder", approved=True)

    with pytest.raises(ApprovalAlreadyDecidedError):
        service.decide(approval.id, reviewer="founder", approved=True)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/core/test_approval.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.core.approval'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/core/approval.py
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"


class Approval(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action: str
    subject: str
    requester: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    reviewer: str | None = None
    reason: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    decided_at: datetime | None = None


class ApprovalNotFoundError(Exception):
    def __init__(self, approval_id: str) -> None:
        super().__init__(f"Approval not found: {approval_id}")
        self.approval_id = approval_id


class ApprovalAlreadyDecidedError(Exception):
    def __init__(self, approval_id: str, status: ApprovalStatus) -> None:
        super().__init__(f"Approval {approval_id} was already decided (status={status.value})")
        self.approval_id = approval_id
        self.status = status


class ApprovalService:
    """In-memory Approval object store (blueprint §49). One approval per
    gated action — created PENDING, decided exactly once by a human
    reviewer. Persistence and notification transport (email, Slack, etc.)
    are later hardening.
    """

    def __init__(self) -> None:
        self._approvals: dict[str, Approval] = {}

    def request_approval(self, *, action: str, subject: str, requester: str) -> Approval:
        approval = Approval(action=action, subject=subject, requester=requester)
        self._approvals[approval.id] = approval
        return approval

    def get(self, approval_id: str) -> Approval:
        try:
            return self._approvals[approval_id]
        except KeyError:
            raise ApprovalNotFoundError(approval_id) from None

    def decide(self, approval_id: str, *, reviewer: str, approved: bool, reason: str | None = None) -> Approval:
        approval = self.get(approval_id)
        if approval.status != ApprovalStatus.PENDING:
            raise ApprovalAlreadyDecidedError(approval_id, approval.status)
        approval.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.DENIED
        approval.reviewer = reviewer
        approval.reason = reason
        approval.decided_at = datetime.now(timezone.utc)
        return approval
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/core/test_approval.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/core/approval.py backend/tests/agentos/core/test_approval.py
git commit -m "feat(agentos): add Approval object and ApprovalService"
```

---

### Task 3: Workflow models — `Workflow`, `WorkflowStatus`, `StepOutcome`

**Files:**
- Create: `backend/agentos/workflows/__init__.py`
- Create: `backend/agentos/workflows/models.py`
- Create: `backend/tests/agentos/workflows/__init__.py`
- Test: `backend/tests/agentos/workflows/test_models.py`

**Interfaces:**
- Produces: `WorkflowStatus` (str enum: `PENDING`, `RUNNING`, `WAITING_APPROVAL`, `COMPLETED`, `FAILED`, `CANCELLED`); `InvalidWorkflowTransition(current: WorkflowStatus, target: WorkflowStatus)`; `Workflow(id: str, name: str, status: WorkflowStatus = PENDING, current_step_index: int = 0, state: dict, pending_approval_id: str | None, error: str | None, created_at: datetime, updated_at: datetime)` with `.transition(target: WorkflowStatus) -> None` and `.is_terminal() -> bool`; `StepStatus` (str enum: `COMPLETED`, `WAITING_APPROVAL`, `FAILED`); `StepOutcome(status: StepStatus, updates: dict, error: str | None, approval_id: str | None)`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/workflows/test_models.py
import pytest

from agentos.workflows.models import InvalidWorkflowTransition, StepOutcome, StepStatus, Workflow, WorkflowStatus


def test_workflow_starts_pending():
    workflow = Workflow(name="onboarding")
    assert workflow.status == WorkflowStatus.PENDING
    assert workflow.is_terminal() is False


def test_workflow_valid_transition_to_running():
    workflow = Workflow(name="onboarding")
    workflow.transition(WorkflowStatus.RUNNING)
    assert workflow.status == WorkflowStatus.RUNNING


def test_workflow_invalid_transition_raises():
    workflow = Workflow(name="onboarding")
    with pytest.raises(InvalidWorkflowTransition):
        workflow.transition(WorkflowStatus.COMPLETED)


def test_workflow_completed_is_terminal():
    workflow = Workflow(name="onboarding")
    workflow.transition(WorkflowStatus.RUNNING)
    workflow.transition(WorkflowStatus.COMPLETED)
    assert workflow.is_terminal() is True


def test_workflow_can_resume_from_waiting_approval():
    workflow = Workflow(name="onboarding")
    workflow.transition(WorkflowStatus.RUNNING)
    workflow.transition(WorkflowStatus.WAITING_APPROVAL)
    workflow.transition(WorkflowStatus.RUNNING)
    assert workflow.status == WorkflowStatus.RUNNING


def test_step_outcome_defaults():
    outcome = StepOutcome(status=StepStatus.COMPLETED)
    assert outcome.updates == {}
    assert outcome.error is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/workflows/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.workflows'`

- [ ] **Step 3: Create package scaffolding and the implementation**

```python
# backend/agentos/workflows/__init__.py
```

```python
# backend/tests/agentos/workflows/__init__.py
```

```python
# backend/agentos/workflows/models.py
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class WorkflowStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


_TERMINAL_STATUSES = frozenset({WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED})

_ALLOWED_TRANSITIONS: dict[WorkflowStatus, frozenset[WorkflowStatus]] = {
    WorkflowStatus.PENDING: frozenset({WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED}),
    WorkflowStatus.RUNNING: frozenset(
        {
            WorkflowStatus.WAITING_APPROVAL,
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
        }
    ),
    WorkflowStatus.WAITING_APPROVAL: frozenset(
        {WorkflowStatus.RUNNING, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED}
    ),
    WorkflowStatus.COMPLETED: frozenset(),
    WorkflowStatus.FAILED: frozenset(),
    WorkflowStatus.CANCELLED: frozenset(),
}


class InvalidWorkflowTransition(Exception):
    def __init__(self, current: WorkflowStatus, target: WorkflowStatus) -> None:
        super().__init__(f"Cannot transition Workflow from {current.value} to {target.value}")
        self.current = current
        self.target = target


class Workflow(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step_index: int = 0
    state: dict[str, Any] = Field(default_factory=dict)
    pending_approval_id: str | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def transition(self, target: WorkflowStatus) -> None:
        allowed = _ALLOWED_TRANSITIONS[self.status]
        if target not in allowed:
            raise InvalidWorkflowTransition(self.status, target)
        self.status = target
        self.updated_at = datetime.now(timezone.utc)

    def is_terminal(self) -> bool:
        return self.status in _TERMINAL_STATUSES


class StepStatus(str, enum.Enum):
    COMPLETED = "COMPLETED"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    FAILED = "FAILED"


class StepOutcome(BaseModel):
    status: StepStatus
    updates: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    approval_id: str | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/workflows/test_models.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/workflows/__init__.py backend/agentos/workflows/models.py backend/tests/agentos/workflows/__init__.py backend/tests/agentos/workflows/test_models.py
git commit -m "feat(agentos): add Workflow/WorkflowStatus state machine and StepOutcome"
```

---

### Task 4: `WorkflowStep` protocol + `DeterministicStep` + `AgentStep`

**Files:**
- Create: `backend/agentos/workflows/steps.py`
- Test: `backend/tests/agentos/workflows/test_steps.py`

**Interfaces:**
- Consumes: `Agent`, `AgentRunStatus`, `TaskContext` from `agentos.core` (Phase 1); `StepOutcome`, `StepStatus` from `agentos.workflows.models` (Task 3).
- Produces: `WorkflowStep` (runtime-checkable `Protocol`: `name: str`, `async def run(state: dict) -> StepOutcome`); `DeterministicStep(name: str, fn: Callable[[dict], Awaitable[dict]])`; `AgentStep(name: str, agent: Agent, *, goal_key: str, output_key: str, agent_key: str, workspace_key: str = "workspace_id")`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/workflows/test_steps.py
import pytest

from agentos.core.models import AgentResult, AgentRunStatus, TaskContext
from agentos.workflows.models import StepStatus
from agentos.workflows.steps import AgentStep, DeterministicStep, WorkflowStep


class _EchoAgent:
    async def run(self, task: TaskContext) -> AgentResult:
        return AgentResult(run_id="r", status=AgentRunStatus.COMPLETED, output=f"researched: {task.goal}")


class _FailingAgent:
    async def run(self, task: TaskContext) -> AgentResult:
        return AgentResult(run_id="r", status=AgentRunStatus.FAILED, error="model unavailable")


async def _write_record(state: dict) -> dict:
    return {"record_id": "rec-123"}


def test_deterministic_step_satisfies_protocol():
    assert isinstance(DeterministicStep("write", _write_record), WorkflowStep)


def test_agent_step_satisfies_protocol():
    step = AgentStep("research", _EchoAgent(), goal_key="goal", output_key="research", agent_key="researcher")
    assert isinstance(step, WorkflowStep)


@pytest.mark.asyncio
async def test_deterministic_step_merges_returned_updates():
    step = DeterministicStep("write", _write_record)

    outcome = await step.run({})

    assert outcome.status == StepStatus.COMPLETED
    assert outcome.updates == {"record_id": "rec-123"}


@pytest.mark.asyncio
async def test_agent_step_writes_output_to_output_key():
    step = AgentStep("research", _EchoAgent(), goal_key="goal", output_key="research_notes", agent_key="researcher")
    state = {"goal": "market size for widgets", "workspace_id": "ws1"}

    outcome = await step.run(state)

    assert outcome.status == StepStatus.COMPLETED
    assert outcome.updates == {"research_notes": "researched: market size for widgets"}


@pytest.mark.asyncio
async def test_agent_step_fails_when_agent_does_not_complete():
    step = AgentStep("research", _FailingAgent(), goal_key="goal", output_key="research_notes", agent_key="researcher")
    state = {"goal": "market size for widgets", "workspace_id": "ws1"}

    outcome = await step.run(state)

    assert outcome.status == StepStatus.FAILED
    assert outcome.error == "model unavailable"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/workflows/test_steps.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.workflows.steps'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/workflows/steps.py
from __future__ import annotations

from typing import Any, Awaitable, Callable, Protocol, runtime_checkable

from agentos.core.agent import Agent
from agentos.core.models import AgentRunStatus, TaskContext
from agentos.workflows.models import StepOutcome, StepStatus


@runtime_checkable
class WorkflowStep(Protocol):
    name: str

    async def run(self, state: dict[str, Any]) -> StepOutcome:
        ...


class DeterministicStep:
    """A plain deterministic business step (blueprint §45: business
    workflow logic must not be replaced by an LLM). `fn` receives the
    current workflow state and returns a dict of updates to merge in.
    """

    def __init__(self, name: str, fn: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]) -> None:
        self.name = name
        self._fn = fn

    async def run(self, state: dict[str, Any]) -> StepOutcome:
        updates = await self._fn(state)
        return StepOutcome(status=StepStatus.COMPLETED, updates=updates)


class AgentStep:
    """An agent-reasoning step (blueprint §45: agent workflow can be
    probabilistic). Reads `goal_key` from state as the agent's goal and
    writes the agent's output to `output_key`.
    """

    def __init__(
        self,
        name: str,
        agent: Agent,
        *,
        goal_key: str,
        output_key: str,
        agent_key: str,
        workspace_key: str = "workspace_id",
    ) -> None:
        self.name = name
        self._agent = agent
        self._goal_key = goal_key
        self._output_key = output_key
        self._agent_key = agent_key
        self._workspace_key = workspace_key

    async def run(self, state: dict[str, Any]) -> StepOutcome:
        task = TaskContext(
            goal=state[self._goal_key],
            agent_key=self._agent_key,
            workspace_id=state[self._workspace_key],
        )
        result = await self._agent.run(task)
        if result.status != AgentRunStatus.COMPLETED:
            return StepOutcome(status=StepStatus.FAILED, error=result.error or "agent step did not complete")
        return StepOutcome(status=StepStatus.COMPLETED, updates={self._output_key: result.output})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/workflows/test_steps.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/workflows/steps.py backend/tests/agentos/workflows/test_steps.py
git commit -m "feat(agentos): add DeterministicStep and AgentStep"
```

---

### Task 5: `ApprovalGateStep`

**Files:**
- Create: `backend/agentos/workflows/approval_step.py`
- Test: `backend/tests/agentos/workflows/test_approval_step.py`

**Interfaces:**
- Consumes: `ApprovalService`, `ApprovalStatus` from `agentos.core.approval` (Task 2); `PermissionClass`, `PolicyDecision`, `PolicyEngine` from `agentos.core.policy` (Task 1); `StepOutcome`, `StepStatus` from `agentos.workflows.models` (Task 3).
- Produces: `ApprovalGateStep(name: str, *, policy_engine: PolicyEngine, approval_service: ApprovalService, permission: PermissionClass, action: str, subject_key: str, requester: str)` with `.run(state: dict) -> StepOutcome` and `.check_pending(approval_id: str) -> StepOutcome`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/workflows/test_approval_step.py
import pytest

from agentos.core.approval import ApprovalService
from agentos.core.policy import PermissionClass, PolicyDecision, PolicyEngine
from agentos.workflows.approval_step import ApprovalGateStep
from agentos.workflows.models import StepStatus


@pytest.mark.asyncio
async def test_allow_permission_completes_immediately():
    step = ApprovalGateStep(
        "gate",
        policy_engine=PolicyEngine({PermissionClass.SEND_MESSAGE: PolicyDecision.ALLOW}),
        approval_service=ApprovalService(),
        permission=PermissionClass.SEND_MESSAGE,
        action="send_email",
        subject_key="campaign_id",
        requester="sales_agent",
    )

    outcome = await step.run({"campaign_id": "camp-1"})

    assert outcome.status == StepStatus.COMPLETED


@pytest.mark.asyncio
async def test_deny_permission_fails_the_step():
    step = ApprovalGateStep(
        "gate",
        policy_engine=PolicyEngine(),
        approval_service=ApprovalService(),
        permission=PermissionClass.ACCESS_SECRET,
        action="read_secret",
        subject_key="campaign_id",
        requester="sales_agent",
    )

    outcome = await step.run({"campaign_id": "camp-1"})

    assert outcome.status == StepStatus.FAILED


@pytest.mark.asyncio
async def test_require_approval_pauses_and_creates_a_pending_approval():
    approval_service = ApprovalService()
    step = ApprovalGateStep(
        "gate",
        policy_engine=PolicyEngine(),
        approval_service=approval_service,
        permission=PermissionClass.SEND_MESSAGE,
        action="send_email",
        subject_key="campaign_id",
        requester="sales_agent",
    )

    outcome = await step.run({"campaign_id": "camp-1"})

    assert outcome.status == StepStatus.WAITING_APPROVAL
    assert outcome.approval_id is not None
    assert approval_service.get(outcome.approval_id).status.value == "PENDING"


@pytest.mark.asyncio
async def test_check_pending_reflects_approval_after_it_is_decided():
    approval_service = ApprovalService()
    step = ApprovalGateStep(
        "gate",
        policy_engine=PolicyEngine(),
        approval_service=approval_service,
        permission=PermissionClass.SEND_MESSAGE,
        action="send_email",
        subject_key="campaign_id",
        requester="sales_agent",
    )
    outcome = await step.run({"campaign_id": "camp-1"})
    approval_service.decide(outcome.approval_id, reviewer="founder", approved=True)

    resumed_outcome = step.check_pending(outcome.approval_id)

    assert resumed_outcome.status == StepStatus.COMPLETED


@pytest.mark.asyncio
async def test_check_pending_fails_when_denied():
    approval_service = ApprovalService()
    step = ApprovalGateStep(
        "gate",
        policy_engine=PolicyEngine(),
        approval_service=approval_service,
        permission=PermissionClass.SEND_MESSAGE,
        action="send_email",
        subject_key="campaign_id",
        requester="sales_agent",
    )
    outcome = await step.run({"campaign_id": "camp-1"})
    approval_service.decide(outcome.approval_id, reviewer="founder", approved=False, reason="too risky")

    resumed_outcome = step.check_pending(outcome.approval_id)

    assert resumed_outcome.status == StepStatus.FAILED
    assert "too risky" in resumed_outcome.error
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/workflows/test_approval_step.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.workflows.approval_step'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/workflows/approval_step.py
from __future__ import annotations

from typing import Any

from agentos.core.approval import ApprovalService, ApprovalStatus
from agentos.core.policy import PermissionClass, PolicyDecision, PolicyEngine
from agentos.workflows.models import StepOutcome, StepStatus


class ApprovalGateStep:
    """Human approval node (blueprint §47 example: ...→Human Approval→...).
    Consults the PolicyEngine first: ALLOW passes straight through, DENY
    fails the step outright, REQUIRE_APPROVAL creates a pending Approval
    and pauses the workflow. Resuming a paused workflow re-checks the same
    approval via check_pending() rather than re-evaluating the policy —
    the decision to require approval, once made, doesn't get re-litigated.
    """

    def __init__(
        self,
        name: str,
        *,
        policy_engine: PolicyEngine,
        approval_service: ApprovalService,
        permission: PermissionClass,
        action: str,
        subject_key: str,
        requester: str,
    ) -> None:
        self.name = name
        self._policy_engine = policy_engine
        self._approval_service = approval_service
        self._permission = permission
        self._action = action
        self._subject_key = subject_key
        self._requester = requester

    async def run(self, state: dict[str, Any]) -> StepOutcome:
        decision = self._policy_engine.evaluate(self._permission)
        if decision == PolicyDecision.ALLOW:
            return StepOutcome(status=StepStatus.COMPLETED)
        if decision == PolicyDecision.DENY:
            return StepOutcome(status=StepStatus.FAILED, error=f"{self._permission.value} is denied by policy")

        approval = self._approval_service.request_approval(
            action=self._action, subject=state[self._subject_key], requester=self._requester
        )
        return StepOutcome(status=StepStatus.WAITING_APPROVAL, approval_id=approval.id)

    def check_pending(self, approval_id: str) -> StepOutcome:
        approval = self._approval_service.get(approval_id)
        if approval.status == ApprovalStatus.PENDING:
            return StepOutcome(status=StepStatus.WAITING_APPROVAL, approval_id=approval_id)
        if approval.status == ApprovalStatus.DENIED:
            return StepOutcome(
                status=StepStatus.FAILED, error=f"approval {approval_id} was denied: {approval.reason}"
            )
        return StepOutcome(status=StepStatus.COMPLETED)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/workflows/test_approval_step.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/workflows/approval_step.py backend/tests/agentos/workflows/test_approval_step.py
git commit -m "feat(agentos): add ApprovalGateStep"
```

---

### Task 6: `WorkflowEngine`

**Files:**
- Create: `backend/agentos/workflows/engine.py`
- Test: `backend/tests/agentos/workflows/test_engine.py`

**Interfaces:**
- Consumes: `ApprovalGateStep` (Task 5); `StepStatus`, `Workflow`, `WorkflowStatus` (Task 3); `WorkflowStep` (Task 4).
- Produces: `WorkflowEngine` with `async def start(name: str, steps: list[WorkflowStep], initial_state: dict) -> Workflow` and `async def resume(workflow: Workflow, steps: list[WorkflowStep]) -> Workflow` (no-op if `workflow.status != WAITING_APPROVAL`).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/workflows/test_engine.py
import pytest

from agentos.core.approval import ApprovalService
from agentos.core.policy import PermissionClass, PolicyEngine
from agentos.workflows.approval_step import ApprovalGateStep
from agentos.workflows.engine import WorkflowEngine
from agentos.workflows.models import WorkflowStatus
from agentos.workflows.steps import DeterministicStep


async def _write_record(state: dict) -> dict:
    return {"record_id": "rec-123"}


async def _notify(state: dict) -> dict:
    return {"notified": True}


async def _failing_step(state: dict) -> dict:
    raise RuntimeError("should not run")


@pytest.mark.asyncio
async def test_workflow_completes_when_all_deterministic_steps_succeed():
    engine = WorkflowEngine()
    steps = [DeterministicStep("write", _write_record), DeterministicStep("notify", _notify)]

    workflow = await engine.start("business-write-flow", steps, {})

    assert workflow.status == WorkflowStatus.COMPLETED
    assert workflow.state == {"record_id": "rec-123", "notified": True}


@pytest.mark.asyncio
async def test_workflow_pauses_at_approval_gate_and_resumes_when_approved():
    approval_service = ApprovalService()
    engine = WorkflowEngine()
    gate = ApprovalGateStep(
        "approve-send",
        policy_engine=PolicyEngine(),
        approval_service=approval_service,
        permission=PermissionClass.SEND_MESSAGE,
        action="send_email",
        subject_key="campaign_id",
        requester="sales_agent",
    )
    steps = [DeterministicStep("write", _write_record), gate, DeterministicStep("notify", _notify)]

    workflow = await engine.start("send-flow", steps, {"campaign_id": "camp-1"})
    assert workflow.status == WorkflowStatus.WAITING_APPROVAL
    assert workflow.pending_approval_id is not None

    approval_service.decide(workflow.pending_approval_id, reviewer="founder", approved=True)
    resumed = await engine.resume(workflow, steps)

    assert resumed.status == WorkflowStatus.COMPLETED
    assert resumed.state["notified"] is True


@pytest.mark.asyncio
async def test_workflow_fails_when_resumed_approval_is_denied():
    approval_service = ApprovalService()
    engine = WorkflowEngine()
    gate = ApprovalGateStep(
        "approve-send",
        policy_engine=PolicyEngine(),
        approval_service=approval_service,
        permission=PermissionClass.SEND_MESSAGE,
        action="send_email",
        subject_key="campaign_id",
        requester="sales_agent",
    )
    steps = [gate, DeterministicStep("notify", _failing_step)]

    workflow = await engine.start("send-flow", steps, {"campaign_id": "camp-1"})
    approval_service.decide(workflow.pending_approval_id, reviewer="founder", approved=False, reason="not ready")
    resumed = await engine.resume(workflow, steps)

    assert resumed.status == WorkflowStatus.FAILED
    assert "not ready" in resumed.error


@pytest.mark.asyncio
async def test_resume_is_a_noop_when_not_waiting_approval():
    engine = WorkflowEngine()
    steps = [DeterministicStep("write", _write_record)]
    workflow = await engine.start("flow", steps, {})

    resumed = await engine.resume(workflow, steps)

    assert resumed is workflow
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/workflows/test_engine.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.workflows.engine'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/workflows/engine.py
from __future__ import annotations

from agentos.workflows.approval_step import ApprovalGateStep
from agentos.workflows.models import StepStatus, Workflow, WorkflowStatus
from agentos.workflows.steps import WorkflowStep


class WorkflowEngine:
    """Runs a linear list of WorkflowStep (blueprint §47 example: Start →
    Agent Research → Human Approval → Business Write → Notify → End).
    Steps can mix deterministic, agent-reasoning, and approval-gate kinds
    freely — the engine only reacts to StepOutcome, not which kind it is.
    """

    async def start(self, name: str, steps: list[WorkflowStep], initial_state: dict) -> Workflow:
        workflow = Workflow(name=name, state=dict(initial_state))
        workflow.transition(WorkflowStatus.RUNNING)
        return await self._run_from(workflow, steps)

    async def resume(self, workflow: Workflow, steps: list[WorkflowStep]) -> Workflow:
        if workflow.status != WorkflowStatus.WAITING_APPROVAL:
            return workflow
        step = steps[workflow.current_step_index]
        if not isinstance(step, ApprovalGateStep):
            raise TypeError(f"Cannot resume: step {step.name!r} at the paused index is not an ApprovalGateStep")
        outcome = step.check_pending(workflow.pending_approval_id)
        if outcome.status == StepStatus.WAITING_APPROVAL:
            return workflow
        workflow.transition(WorkflowStatus.RUNNING)
        workflow.pending_approval_id = None
        if outcome.status == StepStatus.FAILED:
            workflow.error = outcome.error
            workflow.transition(WorkflowStatus.FAILED)
            return workflow
        workflow.state.update(outcome.updates)
        workflow.current_step_index += 1
        return await self._run_from(workflow, steps)

    async def _run_from(self, workflow: Workflow, steps: list[WorkflowStep]) -> Workflow:
        while workflow.current_step_index < len(steps):
            step = steps[workflow.current_step_index]
            outcome = await step.run(workflow.state)

            if outcome.status == StepStatus.WAITING_APPROVAL:
                workflow.pending_approval_id = outcome.approval_id
                workflow.transition(WorkflowStatus.WAITING_APPROVAL)
                return workflow

            if outcome.status == StepStatus.FAILED:
                workflow.error = outcome.error
                workflow.transition(WorkflowStatus.FAILED)
                return workflow

            workflow.state.update(outcome.updates)
            workflow.current_step_index += 1

        workflow.transition(WorkflowStatus.COMPLETED)
        return workflow
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/workflows/test_engine.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/workflows/engine.py backend/tests/agentos/workflows/test_engine.py
git commit -m "feat(agentos): add WorkflowEngine"
```

---

### Task 7: Integration — the blueprint's exact example workflow, end to end

**Files:**
- Test: `backend/tests/agentos/workflows/test_full_workflow_integration.py`

**Interfaces:** None new — assembles Tasks 1–6 plus Phase 1's real `AgentRuntime` into the blueprint §47 example: Start → Agent Research → Human Approval → Business Write → Notify → End.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/workflows/test_full_workflow_integration.py
import pytest

from agentos.core.model_provider import ModelResponse, StubModelProvider
from agentos.core.approval import ApprovalService
from agentos.core.policy import PermissionClass, PolicyEngine
from agentos.core.runtime import AgentRuntime
from agentos.tools.registry import ToolRegistry
from agentos.workflows.approval_step import ApprovalGateStep
from agentos.workflows.engine import WorkflowEngine
from agentos.workflows.models import WorkflowStatus
from agentos.workflows.steps import AgentStep, DeterministicStep


async def _business_write(state: dict) -> dict:
    return {"crm_record_id": "crm-42"}


async def _notify(state: dict) -> dict:
    return {"notified": True}


def _build_steps(approval_service: ApprovalService) -> list:
    researcher = AgentRuntime(
        StubModelProvider([ModelResponse(text="Acme Corp is a mid-market SaaS company, 50 employees.")]),
        ToolRegistry(),
    )
    return [
        AgentStep("research", researcher, goal_key="goal", output_key="research_notes", agent_key="researcher"),
        ApprovalGateStep(
            "human-approval",
            policy_engine=PolicyEngine(),
            approval_service=approval_service,
            permission=PermissionClass.MODIFY_BUSINESS_DATA,
            action="create_crm_record",
            subject_key="goal",
            requester="researcher",
        ),
        DeterministicStep("business-write", _business_write),
        DeterministicStep("notify", _notify),
    ]


@pytest.mark.asyncio
async def test_full_workflow_completes_end_to_end_when_approved():
    approval_service = ApprovalService()
    engine = WorkflowEngine()
    steps = _build_steps(approval_service)

    workflow = await engine.start(
        "prospect-research-flow", steps, {"goal": "research Acme Corp", "workspace_id": "ws1"}
    )
    assert workflow.status == WorkflowStatus.WAITING_APPROVAL
    assert workflow.state["research_notes"] == "Acme Corp is a mid-market SaaS company, 50 employees."

    approval_service.decide(workflow.pending_approval_id, reviewer="founder", approved=True)
    resumed = await engine.resume(workflow, steps)

    assert resumed.status == WorkflowStatus.COMPLETED
    assert resumed.state["crm_record_id"] == "crm-42"
    assert resumed.state["notified"] is True


@pytest.mark.asyncio
async def test_full_workflow_stops_before_business_write_when_denied():
    approval_service = ApprovalService()
    engine = WorkflowEngine()
    steps = _build_steps(approval_service)

    workflow = await engine.start(
        "prospect-research-flow", steps, {"goal": "research Acme Corp", "workspace_id": "ws1"}
    )
    approval_service.decide(
        workflow.pending_approval_id, reviewer="founder", approved=False, reason="need more info"
    )
    resumed = await engine.resume(workflow, steps)

    assert resumed.status == WorkflowStatus.FAILED
    assert "crm_record_id" not in resumed.state
    assert "need more info" in resumed.error
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/workflows/test_full_workflow_integration.py -v`
Expected: 2 passed — this is a pure integration proof over already-implemented Tasks 1–6 plus Phase 1's `AgentRuntime`, so there is no separate "watch it fail first" step: if either test fails, it points at a real incompatibility, not a missing-module error — stop and investigate rather than proceeding.

- [ ] **Step 3: Run the full `agentos` core + workflows suites to confirm everything holds together**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/core/test_policy.py tests/agentos/core/test_approval.py tests/agentos/workflows/ -v`
Expected: all passing — 4 (policy) + 5 (approval) + 6 (models) + 5 (steps) + 5 (approval_step) + 4 (engine) + 2 (integration) = 31 total

- [ ] **Step 4: Commit**

```bash
git add backend/tests/agentos/workflows/test_full_workflow_integration.py
git commit -m "test(agentos): prove the blueprint §47 example workflow end-to-end"
```

---

## Verification (end of Phase 8)

1. Run the full new suites: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/core/test_policy.py tests/agentos/core/test_approval.py tests/agentos/workflows/ -v` — all tests pass (31 total per Task 7 Step 3).
2. Run the full `agentos` suite: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/ -v` — no regressions in Phase 0/1/3/4/5/6/7 tests.
3. Confirm no production wiring was introduced: `grep -rn "import agentos\|from agentos" backend --include="*.py" | grep -v "^backend/agentos/\|^backend/tests/agentos/"` returns no results.
4. Manually re-read `agentos/workflows/engine.py` and confirm `_run_from` never mutates `workflow.state` before checking whether the step failed — the tests in Task 6/7 prove this for the cases exercised (denied approval never leaves `crm_record_id` in state), but it's worth eyeballing given how central "don't apply partial updates from a failed step" is to the whole engine's correctness.

## Next steps (not part of this plan)

Per `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §4: Phase 9 (Evaluation & Observability — full trace tree, business outcome eval) is next. It should get its own plan via `superpowers:writing-plans` once this one is merged and reviewed. Explicitly deferred and not yet scoped anywhere: parallel branches inside a `WorkflowEngine` run (the blueprint's §47 "parallel branch" step kind — this plan only builds the linear case); a real notification transport for pending approvals (email/Slack, per blueprint §7 outbound-actions-need-human-approval territory); and workflow persistence (a `Workflow` currently only exists in memory for the caller holding the reference — there is no store to look one up by id later, unlike every other registry/service built in prior phases).
