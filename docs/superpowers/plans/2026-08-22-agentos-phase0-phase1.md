# AgentOS Phase 0 + Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the `agentos/` Python package (blueprint's Agent Core) with its Phase 0 baseline interfaces and a working Phase 1 single-agent tool-calling loop (MVP `AgentRuntime`), fully isolated from and non-invasive to the existing `cosa_core`/`workforce` production runtime.

**Architecture:** New package `backend/agentos/` (Python 3.11, pydantic v2 for cross-boundary contracts, plain classes for internal wiring) implementing: `AgentRun`/`TaskContext`/`AgentResult`/`AgentContext` models, an `Agent` protocol, canonical `entity.action` events on an in-memory bus, a `ModelProvider` protocol with a deterministic test double, a minimal `ToolRegistry`, and a `ContextBuilder → Planner → Executor → AgentRuntime` pipeline implementing a ReAct-style single-agent tool-calling loop with full trace recording. No wiring into `main.py` or any production call site — this phase only proves the runtime shape works end-to-end under test.

**Tech Stack:** Python 3.11, pydantic 2.13, pytest + pytest-asyncio (all already present in `backend/.venv` and `backend/pytest.ini`, `asyncio_mode = strict`).

## Global Constraints

- New code lives entirely under `backend/agentos/` (package) and `backend/tests/agentos/` (tests) — do not modify any file under `backend/cosa_core/`, `backend/workforce/`, or any other existing production module in this plan.
- No new third-party dependencies — everything needed (`pydantic`, `pytest`, `pytest-asyncio`) is already in `backend/requirements.txt`.
- Every public class/function gets a docstring only where the "why" is non-obvious (MVP scope note, deferred concern) — no restating what the code already says.
- Every test file uses `pytest-asyncio` strict mode: async tests need `@pytest.mark.asyncio` (already project convention, confirmed in `backend/pytest.ini`).
- Run tests via: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/<file> -v`
- Source spec: `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §3.1, §3.2 (Agent Core / Orchestration), §4 (Phase 0 / Phase 1 scope).

---

## File Structure

```text
backend/agentos/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── models.py           # AgentRun, AgentRunStatus, TaskContext, AgentResult
│   ├── agent.py             # Agent protocol
│   ├── context.py            # AgentContext model
│   ├── events.py              # canonical event names, EventEnvelope, InMemoryEventBus
│   ├── model_provider.py       # ModelProvider protocol, ModelResponse, ToolCallRequest, StubModelProvider
│   ├── planner.py               # Planner, PlanAction
│   ├── trace.py                  # TraceRecorder
│   ├── context_builder.py         # ContextBuilder
│   ├── executor.py                 # Executor (tool-calling loop)
│   └── runtime.py                   # AgentRuntime (wires everything)
└── tools/
    ├── __init__.py
    └── registry.py           # ToolSpec, ToolRegistry, ToolNotFoundError

backend/tests/agentos/
├── test_models.py
├── test_agent_protocol.py
├── test_events.py
├── test_model_provider.py
├── test_tool_registry.py
├── test_trace.py
├── test_context_builder.py
├── test_planner.py
├── test_executor.py
└── test_runtime_end_to_end.py

docs/architecture/adr/
└── ADR-AGENTOS-001-introduce-agentos-package.md
```

---

### Task 1: Package scaffold + core data models (`AgentRun`, `TaskContext`, `AgentResult`)

**Files:**
- Create: `backend/agentos/__init__.py`
- Create: `backend/agentos/core/__init__.py`
- Create: `backend/agentos/core/models.py`
- Test: `backend/tests/agentos/test_models.py`

**Interfaces:**
- Produces: `AgentRunStatus` (str enum: `CREATED`, `RUNNING`, `WAITING_APPROVAL`, `COMPLETED`, `FAILED`, `CANCELLED`); `AgentRun(agent_key: str, goal: str, id: str, status: AgentRunStatus, result: dict | None, error: str | None).transition(target: AgentRunStatus) -> None` (raises `InvalidAgentRunTransition`), `.is_terminal() -> bool`; `TaskContext(goal: str, agent_key: str, workspace_id: str, metadata: dict)`; `AgentResult(run_id: str, status: AgentRunStatus, output: str | None, tool_calls_made: int, error: str | None)`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/test_models.py
import pytest

from agentos.core.models import AgentRun, AgentRunStatus, InvalidAgentRunTransition


def test_agent_run_starts_created():
    run = AgentRun(agent_key="test_agent", goal="say hi")
    assert run.status == AgentRunStatus.CREATED
    assert run.is_terminal() is False


def test_agent_run_valid_transition_to_running():
    run = AgentRun(agent_key="test_agent", goal="say hi")
    run.transition(AgentRunStatus.RUNNING)
    assert run.status == AgentRunStatus.RUNNING


def test_agent_run_invalid_transition_raises():
    run = AgentRun(agent_key="test_agent", goal="say hi")
    with pytest.raises(InvalidAgentRunTransition):
        run.transition(AgentRunStatus.COMPLETED)


def test_agent_run_completed_is_terminal():
    run = AgentRun(agent_key="test_agent", goal="say hi")
    run.transition(AgentRunStatus.RUNNING)
    run.transition(AgentRunStatus.COMPLETED)
    assert run.is_terminal() is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_models.py -v`
Expected: FAIL / ERROR with `ModuleNotFoundError: No module named 'agentos'`

- [ ] **Step 3: Create package scaffolding**

```python
# backend/agentos/__init__.py
```

```python
# backend/agentos/core/__init__.py
```

- [ ] **Step 4: Write the models implementation**

```python
# backend/agentos/core/models.py
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class AgentRunStatus(str, enum.Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


_TERMINAL_STATUSES = frozenset(
    {AgentRunStatus.COMPLETED, AgentRunStatus.FAILED, AgentRunStatus.CANCELLED}
)

_ALLOWED_TRANSITIONS: dict[AgentRunStatus, frozenset[AgentRunStatus]] = {
    AgentRunStatus.CREATED: frozenset({AgentRunStatus.RUNNING, AgentRunStatus.CANCELLED}),
    AgentRunStatus.RUNNING: frozenset(
        {
            AgentRunStatus.WAITING_APPROVAL,
            AgentRunStatus.COMPLETED,
            AgentRunStatus.FAILED,
            AgentRunStatus.CANCELLED,
        }
    ),
    AgentRunStatus.WAITING_APPROVAL: frozenset(
        {AgentRunStatus.RUNNING, AgentRunStatus.CANCELLED, AgentRunStatus.FAILED}
    ),
    AgentRunStatus.COMPLETED: frozenset(),
    AgentRunStatus.FAILED: frozenset(),
    AgentRunStatus.CANCELLED: frozenset(),
}


class InvalidAgentRunTransition(Exception):
    def __init__(self, current: AgentRunStatus, target: AgentRunStatus) -> None:
        super().__init__(f"Cannot transition AgentRun from {current.value} to {target.value}")
        self.current = current
        self.target = target


class AgentRun(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_key: str
    status: AgentRunStatus = AgentRunStatus.CREATED
    goal: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    result: dict[str, Any] | None = None
    error: str | None = None

    def transition(self, target: AgentRunStatus) -> None:
        allowed = _ALLOWED_TRANSITIONS[self.status]
        if target not in allowed:
            raise InvalidAgentRunTransition(self.status, target)
        self.status = target
        self.updated_at = datetime.now(timezone.utc)

    def is_terminal(self) -> bool:
        return self.status in _TERMINAL_STATUSES


class TaskContext(BaseModel):
    goal: str
    agent_key: str
    workspace_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    run_id: str
    status: AgentRunStatus
    output: str | None = None
    tool_calls_made: int = 0
    error: str | None = None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_models.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add backend/agentos/__init__.py backend/agentos/core/__init__.py backend/agentos/core/models.py backend/tests/agentos/test_models.py
git commit -m "feat(agentos): add AgentRun/TaskContext/AgentResult core models"
```

---

### Task 2: `Agent` protocol + `AgentContext` model

**Files:**
- Create: `backend/agentos/core/agent.py`
- Create: `backend/agentos/core/context.py`
- Test: `backend/tests/agentos/test_agent_protocol.py`

**Interfaces:**
- Consumes: `TaskContext`, `AgentResult`, `AgentRunStatus` from `agentos.core.models` (Task 1).
- Produces: `Agent` (runtime-checkable `Protocol` with `async def run(self, task: TaskContext) -> AgentResult`); `AgentContext(task: TaskContext, system_policy: str, tool_names: list[str], memory_snippets: list[str])`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/test_agent_protocol.py
import pytest

from agentos.core.agent import Agent
from agentos.core.context import AgentContext
from agentos.core.models import AgentResult, AgentRunStatus, TaskContext


class _FakeAgent:
    async def run(self, task: TaskContext) -> AgentResult:
        return AgentResult(run_id="r1", status=AgentRunStatus.COMPLETED, output="ok")


def test_fake_agent_satisfies_protocol():
    assert isinstance(_FakeAgent(), Agent)


@pytest.mark.asyncio
async def test_fake_agent_run_returns_result():
    task = TaskContext(goal="hi", agent_key="fake", workspace_id="ws1")
    result = await _FakeAgent().run(task)
    assert result.status == AgentRunStatus.COMPLETED


def test_agent_context_holds_task_and_policy():
    task = TaskContext(goal="hi", agent_key="fake", workspace_id="ws1")
    context = AgentContext(task=task, system_policy="be nice", tool_names=["echo"])
    assert context.task == task
    assert context.tool_names == ["echo"]
    assert context.memory_snippets == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_agent_protocol.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.core.agent'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/core/agent.py
from __future__ import annotations

from typing import Protocol, runtime_checkable

from agentos.core.models import AgentResult, TaskContext


@runtime_checkable
class Agent(Protocol):
    async def run(self, task: TaskContext) -> AgentResult:
        ...
```

```python
# backend/agentos/core/context.py
from __future__ import annotations

from pydantic import BaseModel, Field

from agentos.core.models import TaskContext


class AgentContext(BaseModel):
    task: TaskContext
    system_policy: str
    tool_names: list[str] = Field(default_factory=list)
    memory_snippets: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_agent_protocol.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/core/agent.py backend/agentos/core/context.py backend/tests/agentos/test_agent_protocol.py
git commit -m "feat(agentos): add Agent protocol and AgentContext model"
```

---

### Task 3: Canonical events (`entity.action` naming) + in-memory event bus

**Files:**
- Create: `backend/agentos/core/events.py`
- Test: `backend/tests/agentos/test_events.py`

**Interfaces:**
- Produces: `EVENT_AGENT_RUN_CREATED`, `EVENT_AGENT_RUN_STARTED`, `EVENT_AGENT_RUN_COMPLETED`, `EVENT_AGENT_RUN_FAILED`, `EVENT_TOOL_CALL_STARTED`, `EVENT_TOOL_CALL_COMPLETED` (all `str` constants); `EventEnvelope(name: str, run_id: str, payload: dict, emitted_at: datetime)`; `InMemoryEventBus` with `.subscribe(handler: Callable[[EventEnvelope], None]) -> None`, `.publish(event: EventEnvelope) -> None`, `.published: list[EventEnvelope]`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/test_events.py
from agentos.core.events import EVENT_AGENT_RUN_CREATED, EventEnvelope, InMemoryEventBus


def test_publish_appends_to_published_log():
    bus = InMemoryEventBus()
    bus.publish(EventEnvelope(name=EVENT_AGENT_RUN_CREATED, run_id="r1"))
    assert len(bus.published) == 1
    assert bus.published[0].name == EVENT_AGENT_RUN_CREATED


def test_subscribers_receive_published_events():
    bus = InMemoryEventBus()
    received = []
    bus.subscribe(received.append)
    event = EventEnvelope(name=EVENT_AGENT_RUN_CREATED, run_id="r1")
    bus.publish(event)
    assert received == [event]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_events.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.core.events'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/core/events.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from pydantic import BaseModel, Field

# Canonical event names follow "entity.action" (blueprint spec §3.9 / Master Architecture §46).
EVENT_AGENT_RUN_CREATED = "agent_run.created"
EVENT_AGENT_RUN_STARTED = "agent_run.started"
EVENT_AGENT_RUN_COMPLETED = "agent_run.completed"
EVENT_AGENT_RUN_FAILED = "agent_run.failed"
EVENT_TOOL_CALL_STARTED = "tool_call.started"
EVENT_TOOL_CALL_COMPLETED = "tool_call.completed"


class EventEnvelope(BaseModel):
    name: str
    run_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    emitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InMemoryEventBus:
    """MVP event bus for a single process/run. A durable, cross-process bus
    is Phase 8 scope (blueprint §4) — do not treat this as production-durable.
    """

    def __init__(self) -> None:
        self._subscribers: list[Callable[[EventEnvelope], None]] = []
        self.published: list[EventEnvelope] = []

    def subscribe(self, handler: Callable[[EventEnvelope], None]) -> None:
        self._subscribers.append(handler)

    def publish(self, event: EventEnvelope) -> None:
        self.published.append(event)
        for handler in self._subscribers:
            handler(event)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_events.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/core/events.py backend/tests/agentos/test_events.py
git commit -m "feat(agentos): add canonical event names and in-memory event bus"
```

---

### Task 4: ADR documenting the baseline decision

**Files:**
- Create: `docs/architecture/adr/ADR-AGENTOS-001-introduce-agentos-package.md`

**Interfaces:** None (documentation only).

- [ ] **Step 1: Write the ADR**

```markdown
# ADR-AGENTOS-001: Introduce `agentos/` package as the Agent Core baseline

## Context
`docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` proposes a
target architecture where a small, stable Python "Agent Core" (`agentos/`)
owns reasoning/runtime, while business state stays in domain services. This
is a big-bang blueprint decision, not an incremental refactor of the
existing `cosa_core`/`workforce` modules — see the spec §6 for explicit
conflicts with `CLAUDE.md`'s "smallest safe change" guidance, accepted
knowingly by the user who requested this blueprint.

## Decision
Add a new top-level Python package `backend/agentos/` implementing the
Agent Core primitives from the blueprint: `AgentRun`, `TaskContext`,
`AgentResult`, `AgentContext`, the `Agent` protocol, and canonical event
names (`entity.action`). Phase 1 builds the MVP single-agent runtime loop
on top of these. Existing `cosa_core`/`workforce` code is left untouched in
this phase — no migration, no deletion, no production wiring.

## Consequences
- Two parallel agent-runtime implementations exist during the migration
  window: production traffic keeps flowing through `cosa_core`/`workforce`;
  `agentos/` is inert (no caller wires it into `main.py`) until a later
  phase explicitly cuts traffic over.
- Every new `agentos/` module defines its interface (protocol/pydantic
  model) before any implementation task — Phase 0 tasks are ordered
  strictly before Phase 1 tasks in the implementation plan for this reason.
```

- [ ] **Step 2: Commit**

```bash
git add docs/architecture/adr/ADR-AGENTOS-001-introduce-agentos-package.md
git commit -m "docs(adr): record decision to introduce agentos/ package"
```

---

### Task 5: `ModelProvider` protocol + `StubModelProvider` test double

**Files:**
- Create: `backend/agentos/core/model_provider.py`
- Test: `backend/tests/agentos/test_model_provider.py`

**Interfaces:**
- Produces: `ToolCallRequest(tool_name: str, arguments: dict)`; `ModelResponse(text: str | None, tool_call: ToolCallRequest | None)`; `ModelProvider` (runtime-checkable `Protocol` with `async def generate(self, *, system_prompt: str, messages: list[dict]) -> ModelResponse`); `StubModelProvider(responses: list[ModelResponse])` with `.calls: list[dict]`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/test_model_provider.py
import pytest

from agentos.core.model_provider import ModelProvider, ModelResponse, StubModelProvider, ToolCallRequest


def test_stub_model_provider_satisfies_protocol():
    assert isinstance(StubModelProvider([]), ModelProvider)


@pytest.mark.asyncio
async def test_stub_model_provider_replays_responses_in_order():
    provider = StubModelProvider(
        [
            ModelResponse(tool_call=ToolCallRequest(tool_name="echo", arguments={"text": "hi"})),
            ModelResponse(text="done"),
        ]
    )
    first = await provider.generate(system_prompt="p", messages=[])
    second = await provider.generate(system_prompt="p", messages=[])
    assert first.tool_call.tool_name == "echo"
    assert second.text == "done"
    assert len(provider.calls) == 2


@pytest.mark.asyncio
async def test_stub_model_provider_raises_when_exhausted():
    provider = StubModelProvider([])
    with pytest.raises(RuntimeError):
        await provider.generate(system_prompt="p", messages=[])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_model_provider.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.core.model_provider'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/core/model_provider.py
from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field


class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: dict = Field(default_factory=dict)


class ModelResponse(BaseModel):
    text: str | None = None
    tool_call: ToolCallRequest | None = None


@runtime_checkable
class ModelProvider(Protocol):
    async def generate(self, *, system_prompt: str, messages: list[dict]) -> ModelResponse:
        ...


class StubModelProvider:
    """Deterministic test double: replays a fixed queue of responses.

    Not a production model — Phase 1 scope is proving the runtime loop
    shape works end-to-end; a real ModelGateway-backed provider (blueprint
    §3.11) is a later phase.
    """

    def __init__(self, responses: list[ModelResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    async def generate(self, *, system_prompt: str, messages: list[dict]) -> ModelResponse:
        self.calls.append({"system_prompt": system_prompt, "messages": messages})
        if not self._responses:
            raise RuntimeError("StubModelProvider ran out of scripted responses")
        return self._responses.pop(0)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_model_provider.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/core/model_provider.py backend/tests/agentos/test_model_provider.py
git commit -m "feat(agentos): add ModelProvider protocol and StubModelProvider"
```

---

### Task 6: `ToolRegistry`

**Files:**
- Create: `backend/agentos/tools/__init__.py`
- Create: `backend/agentos/tools/registry.py`
- Test: `backend/tests/agentos/test_tool_registry.py`

**Interfaces:**
- Produces: `ToolSpec(name: str, description: str, handler: Callable[[dict], Awaitable[dict]])`; `ToolNotFoundError(name: str)`; `ToolRegistry` with `.register(spec: ToolSpec) -> None`, `.get(name: str) -> ToolSpec` (raises `ToolNotFoundError`), `.names() -> list[str]`, `async def invoke(name: str, arguments: dict) -> dict`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/test_tool_registry.py
import pytest

from agentos.tools.registry import ToolNotFoundError, ToolRegistry, ToolSpec


async def _echo(arguments: dict) -> dict:
    return {"echoed": arguments.get("text")}


def test_register_and_names():
    registry = ToolRegistry()
    registry.register(ToolSpec(name="echo", description="echoes text", handler=_echo))
    assert registry.names() == ["echo"]


def test_get_missing_tool_raises():
    registry = ToolRegistry()
    with pytest.raises(ToolNotFoundError):
        registry.get("missing")


@pytest.mark.asyncio
async def test_invoke_calls_handler():
    registry = ToolRegistry()
    registry.register(ToolSpec(name="echo", description="echoes text", handler=_echo))
    result = await registry.invoke("echo", {"text": "hi"})
    assert result == {"echoed": "hi"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_tool_registry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.tools'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/tools/__init__.py
```

```python
# backend/agentos/tools/registry.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    handler: Callable[[dict], Awaitable[dict]]


class ToolNotFoundError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Tool not registered: {name}")
        self.name = name


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        try:
            return self._tools[name]
        except KeyError:
            raise ToolNotFoundError(name) from None

    def names(self) -> list[str]:
        return sorted(self._tools)

    async def invoke(self, name: str, arguments: dict) -> dict:
        spec = self.get(name)
        return await spec.handler(arguments)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_tool_registry.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/tools/__init__.py backend/agentos/tools/registry.py backend/tests/agentos/test_tool_registry.py
git commit -m "feat(agentos): add ToolRegistry"
```

---

### Task 7: `TraceRecorder`

**Files:**
- Create: `backend/agentos/core/trace.py`
- Test: `backend/tests/agentos/test_trace.py`

**Interfaces:**
- Consumes: `EventEnvelope`, `InMemoryEventBus` from `agentos.core.events` (Task 3).
- Produces: `TraceRecorder(run_id: str, event_bus: InMemoryEventBus)` with `.record(name: str, **payload) -> None`, `.export() -> list[dict]`, `.spans: list[dict]`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/agentos/test_trace.py
from agentos.core.events import InMemoryEventBus
from agentos.core.trace import TraceRecorder


def test_record_appends_span_and_publishes_event():
    bus = InMemoryEventBus()
    recorder = TraceRecorder(run_id="r1", event_bus=bus)
    recorder.record("tool_call.started", tool_name="echo")
    assert recorder.export() == [{"name": "tool_call.started", "run_id": "r1", "tool_name": "echo"}]
    assert len(bus.published) == 1
    assert bus.published[0].name == "tool_call.started"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_trace.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.core.trace'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/core/trace.py
from __future__ import annotations

from typing import Any

from agentos.core.events import EventEnvelope, InMemoryEventBus


class TraceRecorder:
    """Per-run trace span list. MVP scope: flat ordered list keyed to a
    single AgentRun; a full trace tree (blueprint §3.9) is a later phase.
    """

    def __init__(self, run_id: str, event_bus: InMemoryEventBus) -> None:
        self.run_id = run_id
        self._event_bus = event_bus
        self.spans: list[dict[str, Any]] = []

    def record(self, name: str, **payload: Any) -> None:
        span = {"name": name, "run_id": self.run_id, **payload}
        self.spans.append(span)
        self._event_bus.publish(EventEnvelope(name=name, run_id=self.run_id, payload=payload))

    def export(self) -> list[dict[str, Any]]:
        return list(self.spans)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_trace.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/core/trace.py backend/tests/agentos/test_trace.py
git commit -m "feat(agentos): add TraceRecorder"
```

---

### Task 8: `ContextBuilder`

**Files:**
- Create: `backend/agentos/core/context_builder.py`
- Test: `backend/tests/agentos/test_context_builder.py`

**Interfaces:**
- Consumes: `AgentContext` (Task 2), `TaskContext` (Task 1), `ToolRegistry` (Task 6).
- Produces: `DEFAULT_SYSTEM_POLICY: str`; `ContextBuilder(tool_registry: ToolRegistry, system_policy: str = DEFAULT_SYSTEM_POLICY)` with `.build(task: TaskContext) -> AgentContext`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/agentos/test_context_builder.py
from agentos.core.context_builder import ContextBuilder, DEFAULT_SYSTEM_POLICY
from agentos.core.models import TaskContext
from agentos.tools.registry import ToolRegistry, ToolSpec


async def _noop(arguments: dict) -> dict:
    return {}


def test_build_includes_registered_tool_names_and_default_policy():
    registry = ToolRegistry()
    registry.register(ToolSpec(name="echo", description="d", handler=_noop))
    builder = ContextBuilder(registry)
    task = TaskContext(goal="say hi", agent_key="fake", workspace_id="ws1")

    context = builder.build(task)

    assert context.task == task
    assert context.tool_names == ["echo"]
    assert context.system_policy == DEFAULT_SYSTEM_POLICY
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_context_builder.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.core.context_builder'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/core/context_builder.py
from __future__ import annotations

from agentos.core.context import AgentContext
from agentos.core.models import TaskContext
from agentos.tools.registry import ToolRegistry

DEFAULT_SYSTEM_POLICY = (
    "You are an AI Agent OS agent. Use only the tools listed. "
    "Never fabricate tool results."
)


class ContextBuilder:
    def __init__(self, tool_registry: ToolRegistry, system_policy: str = DEFAULT_SYSTEM_POLICY) -> None:
        self._tool_registry = tool_registry
        self._system_policy = system_policy

    def build(self, task: TaskContext) -> AgentContext:
        return AgentContext(
            task=task,
            system_policy=self._system_policy,
            tool_names=self._tool_registry.names(),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_context_builder.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/core/context_builder.py backend/tests/agentos/test_context_builder.py
git commit -m "feat(agentos): add ContextBuilder"
```

---

### Task 9: `Planner`

**Files:**
- Create: `backend/agentos/core/planner.py`
- Test: `backend/tests/agentos/test_planner.py`

**Interfaces:**
- Consumes: `ModelResponse` from `agentos.core.model_provider` (Task 5).
- Produces: `PlanAction` (str enum: `CALL_TOOL`, `FINISH`); `Planner` with `.decide(response: ModelResponse) -> PlanAction`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/test_planner.py
from agentos.core.model_provider import ModelResponse, ToolCallRequest
from agentos.core.planner import PlanAction, Planner


def test_decide_call_tool_when_tool_call_present():
    planner = Planner()
    response = ModelResponse(tool_call=ToolCallRequest(tool_name="echo", arguments={}))
    assert planner.decide(response) == PlanAction.CALL_TOOL


def test_decide_finish_when_only_text_present():
    planner = Planner()
    response = ModelResponse(text="done")
    assert planner.decide(response) == PlanAction.FINISH
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_planner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.core.planner'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/core/planner.py
from __future__ import annotations

import enum

from agentos.core.model_provider import ModelResponse


class PlanAction(str, enum.Enum):
    CALL_TOOL = "CALL_TOOL"
    FINISH = "FINISH"


class Planner:
    """MVP planner: reactive, one decision per model turn (ReAct-style).
    Multi-step upfront planning (blueprint §3.1) is out of scope until a
    later phase.
    """

    def decide(self, response: ModelResponse) -> PlanAction:
        if response.tool_call is not None:
            return PlanAction.CALL_TOOL
        return PlanAction.FINISH
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_planner.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/core/planner.py backend/tests/agentos/test_planner.py
git commit -m "feat(agentos): add Planner"
```

---

### Task 10: `Executor` (tool-calling loop)

**Files:**
- Create: `backend/agentos/core/executor.py`
- Test: `backend/tests/agentos/test_executor.py`

**Interfaces:**
- Consumes: `AgentContext` (Task 2), `ModelProvider`/`StubModelProvider`/`ModelResponse`/`ToolCallRequest` (Task 5), `Planner`/`PlanAction` (Task 9), `TraceRecorder` (Task 7), `ToolRegistry`/`ToolSpec` (Task 6), `EVENT_TOOL_CALL_STARTED`/`EVENT_TOOL_CALL_COMPLETED` (Task 3).
- Produces: `MAX_TOOL_ROUNDS: int = 5`; `ExecutorExhaustedError(max_rounds: int)`; `Executor(model_provider, tool_registry, planner, trace)` with `async def run(context: AgentContext) -> tuple[str, int]` (output text, tool_calls_made).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/test_executor.py
import pytest

from agentos.core.context import AgentContext
from agentos.core.events import InMemoryEventBus
from agentos.core.executor import Executor, ExecutorExhaustedError
from agentos.core.model_provider import ModelResponse, StubModelProvider, ToolCallRequest
from agentos.core.models import TaskContext
from agentos.core.planner import Planner
from agentos.core.trace import TraceRecorder
from agentos.tools.registry import ToolRegistry, ToolSpec


async def _echo(arguments: dict) -> dict:
    return {"echoed": arguments.get("text")}


def _make_context() -> AgentContext:
    task = TaskContext(goal="echo hi", agent_key="fake", workspace_id="ws1")
    return AgentContext(task=task, system_policy="p", tool_names=["echo"])


@pytest.mark.asyncio
async def test_executor_calls_tool_then_finishes():
    registry = ToolRegistry()
    registry.register(ToolSpec(name="echo", description="d", handler=_echo))
    provider = StubModelProvider(
        [
            ModelResponse(tool_call=ToolCallRequest(tool_name="echo", arguments={"text": "hi"})),
            ModelResponse(text="echoed hi back"),
        ]
    )
    trace = TraceRecorder(run_id="r1", event_bus=InMemoryEventBus())
    executor = Executor(provider, registry, Planner(), trace)

    output, tool_calls_made = await executor.run(_make_context())

    assert output == "echoed hi back"
    assert tool_calls_made == 1
    assert [s["name"] for s in trace.export()] == ["tool_call.started", "tool_call.completed"]


@pytest.mark.asyncio
async def test_executor_finishes_immediately_without_tool_call():
    registry = ToolRegistry()
    provider = StubModelProvider([ModelResponse(text="hello")])
    trace = TraceRecorder(run_id="r1", event_bus=InMemoryEventBus())
    executor = Executor(provider, registry, Planner(), trace)

    output, tool_calls_made = await executor.run(_make_context())

    assert output == "hello"
    assert tool_calls_made == 0


@pytest.mark.asyncio
async def test_executor_raises_when_max_rounds_exceeded():
    registry = ToolRegistry()
    registry.register(ToolSpec(name="echo", description="d", handler=_echo))
    responses = [
        ModelResponse(tool_call=ToolCallRequest(tool_name="echo", arguments={"text": "hi"}))
        for _ in range(5)
    ]
    provider = StubModelProvider(responses)
    trace = TraceRecorder(run_id="r1", event_bus=InMemoryEventBus())
    executor = Executor(provider, registry, Planner(), trace)

    with pytest.raises(ExecutorExhaustedError):
        await executor.run(_make_context())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_executor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.core.executor'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/core/executor.py
from __future__ import annotations

from agentos.core.context import AgentContext
from agentos.core.events import EVENT_TOOL_CALL_COMPLETED, EVENT_TOOL_CALL_STARTED
from agentos.core.model_provider import ModelProvider
from agentos.core.planner import PlanAction, Planner
from agentos.core.trace import TraceRecorder
from agentos.tools.registry import ToolRegistry

MAX_TOOL_ROUNDS = 5


class ExecutorExhaustedError(Exception):
    def __init__(self, max_rounds: int) -> None:
        super().__init__(f"Executor exceeded MAX_TOOL_ROUNDS={max_rounds} without finishing")


class Executor:
    def __init__(
        self,
        model_provider: ModelProvider,
        tool_registry: ToolRegistry,
        planner: Planner,
        trace: TraceRecorder,
    ) -> None:
        self._model_provider = model_provider
        self._tool_registry = tool_registry
        self._planner = planner
        self._trace = trace

    async def run(self, context: AgentContext) -> tuple[str, int]:
        messages: list[dict] = [{"role": "user", "content": context.task.goal}]
        tool_calls_made = 0

        for _ in range(MAX_TOOL_ROUNDS):
            response = await self._model_provider.generate(
                system_prompt=context.system_policy, messages=messages
            )
            action = self._planner.decide(response)

            if action is PlanAction.FINISH:
                return response.text or "", tool_calls_made

            assert response.tool_call is not None
            self._trace.record(
                EVENT_TOOL_CALL_STARTED,
                tool_name=response.tool_call.tool_name,
                arguments=response.tool_call.arguments,
            )
            result = await self._tool_registry.invoke(
                response.tool_call.tool_name, response.tool_call.arguments
            )
            self._trace.record(
                EVENT_TOOL_CALL_COMPLETED,
                tool_name=response.tool_call.tool_name,
                result=result,
            )
            tool_calls_made += 1
            messages.append({"role": "assistant", "tool_call": response.tool_call.model_dump()})
            messages.append({"role": "tool", "content": result})

        raise ExecutorExhaustedError(MAX_TOOL_ROUNDS)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_executor.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/core/executor.py backend/tests/agentos/test_executor.py
git commit -m "feat(agentos): add Executor tool-calling loop"
```

---

### Task 11: `AgentRuntime` (wires ContextBuilder → Executor → AgentRun lifecycle)

**Files:**
- Create: `backend/agentos/core/runtime.py`
- Test: covered by Task 12's integration tests (no standalone unit test file — `AgentRuntime` has no meaningful behavior to test in isolation from its wired components).

**Interfaces:**
- Consumes: `ContextBuilder` (Task 8), `Executor`/`ExecutorExhaustedError` (Task 10), `Planner` (Task 9), `TraceRecorder`/`InMemoryEventBus` (Task 7/3), `ModelProvider` (Task 5), `ToolRegistry` (Task 6), `AgentRun`/`AgentRunStatus`/`AgentResult`/`TaskContext` (Task 1), `EVENT_AGENT_RUN_STARTED`/`EVENT_AGENT_RUN_COMPLETED`/`EVENT_AGENT_RUN_FAILED` (Task 3).
- Produces: `AgentRuntime(model_provider: ModelProvider, tool_registry: ToolRegistry)` with `async def run(task: TaskContext) -> AgentResult`, `.last_run: AgentRun | None` (satisfies the `Agent` protocol from Task 2).

- [ ] **Step 1: Write the implementation**

(No separate failing-test step here — Task 12 writes the failing integration tests first and this task's code is the minimal implementation that makes them pass. This ordering keeps the wiring task and its test in the same TDD cycle as Task 12, since `AgentRuntime` has no behavior worth testing except end-to-end.)

```python
# backend/agentos/core/runtime.py
from __future__ import annotations

from agentos.core.context_builder import ContextBuilder
from agentos.core.events import (
    EVENT_AGENT_RUN_COMPLETED,
    EVENT_AGENT_RUN_FAILED,
    EVENT_AGENT_RUN_STARTED,
    InMemoryEventBus,
)
from agentos.core.executor import Executor, ExecutorExhaustedError
from agentos.core.model_provider import ModelProvider
from agentos.core.models import AgentResult, AgentRun, AgentRunStatus, TaskContext
from agentos.core.planner import Planner
from agentos.core.trace import TraceRecorder
from agentos.tools.registry import ToolRegistry


class AgentRuntime:
    """MVP single-agent loop implementing the `Agent` protocol (core/agent.py):
    build context, run the executor's tool-calling loop, record trace,
    manage AgentRun status transitions. Multi-agent delegation/parallel
    flows (blueprint §3.2) are out of scope for Phase 1.
    """

    def __init__(self, model_provider: ModelProvider, tool_registry: ToolRegistry) -> None:
        self._model_provider = model_provider
        self._tool_registry = tool_registry
        self._context_builder = ContextBuilder(tool_registry)
        self.last_run: AgentRun | None = None

    async def run(self, task: TaskContext) -> AgentResult:
        run = AgentRun(agent_key=task.agent_key, goal=task.goal)
        self.last_run = run
        event_bus = InMemoryEventBus()
        trace = TraceRecorder(run_id=run.id, event_bus=event_bus)

        run.transition(AgentRunStatus.RUNNING)
        trace.record(EVENT_AGENT_RUN_STARTED)

        context = self._context_builder.build(task)
        executor = Executor(self._model_provider, self._tool_registry, Planner(), trace)

        try:
            output, tool_calls_made = await executor.run(context)
        except ExecutorExhaustedError as exc:
            run.transition(AgentRunStatus.FAILED)
            run.error = str(exc)
            trace.record(EVENT_AGENT_RUN_FAILED, error=str(exc))
            return AgentResult(run_id=run.id, status=run.status, error=str(exc))

        run.transition(AgentRunStatus.COMPLETED)
        run.result = {"output": output, "tool_calls_made": tool_calls_made}
        trace.record(EVENT_AGENT_RUN_COMPLETED, output=output)

        return AgentResult(
            run_id=run.id,
            status=run.status,
            output=output,
            tool_calls_made=tool_calls_made,
        )
```

- [ ] **Step 2: Commit** (bundled with Task 12 — see that task's commit step; do not commit `runtime.py` alone without its passing tests)

---

### Task 12: End-to-end integration tests for the single-agent loop

**Files:**
- Test: `backend/tests/agentos/test_runtime_end_to_end.py`

**Interfaces:**
- Consumes: `Agent` (Task 2), `AgentRuntime` (Task 11), `StubModelProvider`/`ModelResponse`/`ToolCallRequest` (Task 5), `TaskContext`/`AgentRunStatus` (Task 1), `ToolRegistry`/`ToolSpec` (Task 6).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/test_runtime_end_to_end.py
import pytest

from agentos.core.agent import Agent
from agentos.core.model_provider import ModelResponse, StubModelProvider, ToolCallRequest
from agentos.core.models import AgentRunStatus, TaskContext
from agentos.core.runtime import AgentRuntime
from agentos.tools.registry import ToolRegistry, ToolSpec


async def _echo(arguments: dict) -> dict:
    return {"echoed": arguments.get("text")}


def test_agent_runtime_satisfies_agent_protocol():
    runtime = AgentRuntime(StubModelProvider([]), ToolRegistry())
    assert isinstance(runtime, Agent)


@pytest.mark.asyncio
async def test_single_agent_loop_end_to_end_completes():
    registry = ToolRegistry()
    registry.register(ToolSpec(name="echo", description="echoes text", handler=_echo))
    provider = StubModelProvider(
        [
            ModelResponse(tool_call=ToolCallRequest(tool_name="echo", arguments={"text": "hi"})),
            ModelResponse(text="Echoed: hi"),
        ]
    )
    runtime = AgentRuntime(provider, registry)
    task = TaskContext(goal="echo hi", agent_key="echo_agent", workspace_id="ws1")

    result = await runtime.run(task)

    assert result.status == AgentRunStatus.COMPLETED
    assert result.output == "Echoed: hi"
    assert result.tool_calls_made == 1
    assert runtime.last_run is not None
    assert runtime.last_run.is_terminal() is True


@pytest.mark.asyncio
async def test_single_agent_loop_end_to_end_no_tool_needed():
    registry = ToolRegistry()
    provider = StubModelProvider([ModelResponse(text="Hello there")])
    runtime = AgentRuntime(provider, registry)
    task = TaskContext(goal="say hi", agent_key="chat_agent", workspace_id="ws1")

    result = await runtime.run(task)

    assert result.status == AgentRunStatus.COMPLETED
    assert result.output == "Hello there"
    assert result.tool_calls_made == 0


@pytest.mark.asyncio
async def test_single_agent_loop_end_to_end_reports_failure_on_exhaustion():
    registry = ToolRegistry()
    registry.register(ToolSpec(name="echo", description="d", handler=_echo))
    responses = [
        ModelResponse(tool_call=ToolCallRequest(tool_name="echo", arguments={"text": "hi"}))
        for _ in range(5)
    ]
    provider = StubModelProvider(responses)
    runtime = AgentRuntime(provider, registry)
    task = TaskContext(goal="loop forever", agent_key="echo_agent", workspace_id="ws1")

    result = await runtime.run(task)

    assert result.status == AgentRunStatus.FAILED
    assert result.error is not None
    assert runtime.last_run.status == AgentRunStatus.FAILED
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_runtime_end_to_end.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.core.runtime'` (confirms Task 11's `runtime.py` has not been added to git tracking/committed yet — the file exists on disk from Task 11 Step 1 but this step is what proves the whole pipeline is exercised together)

- [ ] **Step 3: Run tests again to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_runtime_end_to_end.py -v`
Expected: 4 passed

- [ ] **Step 4: Run the full `agentos` test suite to confirm no regressions**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/ -v`
Expected: 26 passed (4 models + 3 agent_protocol + 2 events + 3 model_provider + 3 tool_registry + 1 trace + 1 context_builder + 2 planner + 3 executor + 4 runtime_end_to_end)

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/core/runtime.py backend/tests/agentos/test_runtime_end_to_end.py
git commit -m "feat(agentos): wire AgentRuntime and add end-to-end single-agent loop tests"
```

---

## Verification (end of Phase 0 + Phase 1)

1. Run the full new suite: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/ -v` — all tests pass.
2. Run the full existing backend suite to confirm zero impact on production code: `cd backend && PYTHONPATH=. ./.venv/bin/pytest -q` — pass/skip counts unchanged from before this plan (no existing test should newly fail, since no file outside `backend/agentos/` and `backend/tests/agentos/` was touched).
3. Confirm no production wiring was introduced: `grep -rn "import agentos\|from agentos" backend --include="*.py" | grep -v "^backend/agentos/\|^backend/tests/agentos/"` returns no results — `agentos/` is not yet called from any existing router, service, or `main.py`.
4. Manually re-read `docs/architecture/adr/ADR-AGENTOS-001-introduce-agentos-package.md` and confirm it accurately reflects what was built.

## Next steps (not part of this plan)

Phase 2 (Business OS MVP via Encore/TypeScript) and Phases 3–10 are out of scope here — see `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §4 for the full roadmap. Each subsequent phase should get its own plan via `superpowers:writing-plans` once this one is merged and reviewed.
