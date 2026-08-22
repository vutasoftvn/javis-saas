# AgentOS Phase 9 — Evaluation & Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `TraceRecorder`'s flat span list (Phase 1) into a real parent/child trace tree, expose it from `AgentRuntime`, and add the three eval layers achievable from data already recorded by prior phases — Agent Eval (Phase 0/1's `AgentRun`), Workflow Eval (Phase 8's `Workflow`), and Business Outcome Eval (a generic, domain-agnostic target-vs-actual grader). Per Phase 9 of the roadmap in `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §4 ("full trace tree, business outcome eval").

**Architecture:** `TraceRecorder.record()` (Phase 1) gains a `span_id`/`parent_span_id` on every span — additive to the method's behavior but changes the shape of the dicts `.export()` returns, so Phase 1's own `test_trace.py` is updated alongside it. `AgentRuntime` (Phase 1) gains a `last_trace` attribute exposing the `TraceRecorder` it used, mirroring the existing `last_run` attribute — the only way anything outside `AgentRuntime.run()` can see the spans a real run actually produced. A new `backend/agentos/observability/` package holds `build_trace_tree()` (nests a flat span list by `parent_span_id`; spans with no known parent become roots — Executor doesn't pass `parent_span_id` yet, so today every real run's tree is degenerate/flat, and that's an honest, explicitly-noted limitation, not a bug) and `compute_run_metrics()` (latency from `AgentRun` timestamps, tool-call count from span names — the metrics genuinely available without new instrumentation). A new `backend/agentos/evals/` package holds three pure, synchronous eval functions: `evaluate_agent_run()` (blueprint §52's subset achievable today: goal completion, tool calls made, latency, an optional caller-supplied human-acceptance signal), `evaluate_workflow()` (blueprint §53's subset: completed, which step failed if any, time to terminal state, whether an approval gate was ever hit — the last two require two small additive fields on Phase 8's `Workflow` model, `failed_step_name` and `had_approval_gate`, set by `WorkflowEngine`), and `evaluate_business_outcome()` (blueprint §54: a generic target-vs-actual ratio grader, the same math as the Encore-side `services/okr/scoring.ts::computeKeyResultScore` from Phase 2, reused here on the Python side for any metric name). A final integration task runs all of this against real `AgentRuntime` and `WorkflowEngine` executions.

**Tech Stack:** Python 3.11, pydantic 2.13, pytest + pytest-asyncio — same as prior `agentos` phases, no new dependencies.

## Global Constraints

- New packages: `backend/agentos/observability/` and `backend/agentos/evals/`. Modified existing files, each called out explicitly in its task: `backend/agentos/core/trace.py`, `backend/agentos/core/runtime.py`, `backend/tests/agentos/test_trace.py`, `backend/tests/agentos/test_runtime_end_to_end.py`, `backend/agentos/workflows/models.py`, `backend/agentos/workflows/engine.py`, `backend/tests/agentos/workflows/test_models.py`, `backend/tests/agentos/workflows/test_engine.py`. Do not modify any other file outside these — in particular, do not modify `agentos/core/executor.py` or `agentos/core/model_provider.py` in this plan; wiring real parent/child span nesting through `Executor` and real token/cost usage through `ModelProvider` are both explicitly deferred (see "Next steps").
- **Prerequisite:** this plan assumes Phase 0/1 (`AgentRun`, `AgentRuntime`, `TraceRecorder`) and Phase 8 (`Workflow`, `WorkflowEngine`, `ApprovalGateStep`, `DeterministicStep`) have already landed.
- `TraceRecorder.record()`'s signature change (`parent_span_id` keyword-only parameter, now returns the new span's `span_id: str` instead of `None`) is backward-compatible for every existing caller in `Executor`/`AgentRuntime` — they call it as a statement and never use the return value, so they need no code change. Only the *test* that asserts the exact shape of an exported span dict needs updating (Task 1).
- Every new eval function (`evaluate_agent_run`, `evaluate_workflow`, `evaluate_business_outcome`) is pure and synchronous — no I/O, no model calls. An LLM-judge eval layer is explicitly out of scope (blueprint §54: "Eval cuối cùng nên gắn với outcome thực, không chỉ LLM judge").
- Every async test needs `@pytest.mark.asyncio` (`backend/pytest.ini` has `asyncio_mode = strict`).
- Run tests via: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/<path> -v`.
- Source spec: `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §3.9 (Observability), §51–56 (Evaluation, Agent/Workflow/Business Outcome Eval, Cost Management), §4 (Phase 9 scope).

---

## File Structure

```text
backend/agentos/observability/
├── __init__.py
├── trace_tree.py         # TraceNode, build_trace_tree
└── metrics.py               # RunMetrics, compute_run_metrics

backend/agentos/evals/
├── __init__.py
├── agent_eval.py            # AgentEvalResult, evaluate_agent_run
├── workflow_eval.py            # WorkflowEvalResult, evaluate_workflow
└── business_outcome_eval.py       # BusinessOutcomeEvalResult, evaluate_business_outcome

backend/agentos/core/trace.py               # MODIFIED (Task 1)
backend/agentos/core/runtime.py              # MODIFIED (Task 1)
backend/agentos/workflows/models.py           # MODIFIED (Task 4)
backend/agentos/workflows/engine.py            # MODIFIED (Task 4)

backend/tests/agentos/observability/
├── __init__.py
├── test_trace_tree.py
└── test_metrics.py

backend/tests/agentos/evals/
├── __init__.py
├── test_agent_eval.py
├── test_workflow_eval.py
├── test_business_outcome_eval.py
└── test_full_eval_integration.py

backend/tests/agentos/test_trace.py                    # MODIFIED (Task 1)
backend/tests/agentos/test_runtime_end_to_end.py         # MODIFIED (Task 1)
backend/tests/agentos/workflows/test_models.py            # MODIFIED (Task 4)
backend/tests/agentos/workflows/test_engine.py              # MODIFIED (Task 4)
```

---

### Task 1: `TraceRecorder` gets span/parent linkage; `AgentRuntime` exposes `last_trace`; `build_trace_tree`

**Files:**
- Modify: `backend/agentos/core/trace.py`
- Modify: `backend/agentos/core/runtime.py`
- Modify: `backend/tests/agentos/test_trace.py`
- Modify: `backend/tests/agentos/test_runtime_end_to_end.py`
- Create: `backend/agentos/observability/__init__.py`
- Create: `backend/agentos/observability/trace_tree.py`
- Create: `backend/tests/agentos/observability/__init__.py`
- Test: `backend/tests/agentos/observability/test_trace_tree.py`

**Interfaces:**
- Produces (changed): `TraceRecorder.record(name: str, *, parent_span_id: str | None = None, **payload) -> str` (was `-> None`; every exported span dict now includes `span_id` and `parent_span_id` keys); `AgentRuntime.last_trace: TraceRecorder | None` (new attribute, set inside `.run()` alongside the existing `last_run`).
- Produces (new): `TraceNode(span_id: str, name: str, payload: dict, children: list[TraceNode])`; `build_trace_tree(spans: list[dict]) -> list[TraceNode]`.

- [ ] **Step 1: Update `test_trace.py` for the new span shape, and add a nesting test**

```python
# backend/tests/agentos/test_trace.py
from agentos.core.events import InMemoryEventBus
from agentos.core.trace import TraceRecorder


def test_record_appends_span_and_publishes_event():
    bus = InMemoryEventBus()
    recorder = TraceRecorder(run_id="r1", event_bus=bus)
    span_id = recorder.record("tool_call.started", tool_name="echo")

    exported = recorder.export()
    assert len(exported) == 1
    assert exported[0]["span_id"] == span_id
    assert exported[0]["parent_span_id"] is None
    assert exported[0]["name"] == "tool_call.started"
    assert exported[0]["run_id"] == "r1"
    assert exported[0]["tool_name"] == "echo"
    assert len(bus.published) == 1
    assert bus.published[0].name == "tool_call.started"


def test_record_supports_parent_span_id_for_nesting():
    bus = InMemoryEventBus()
    recorder = TraceRecorder(run_id="r1", event_bus=bus)
    root_id = recorder.record("agent_run.started")
    child_id = recorder.record("tool_call.started", parent_span_id=root_id, tool_name="echo")

    exported = recorder.export()
    child_span = next(s for s in exported if s["span_id"] == child_id)
    assert child_span["parent_span_id"] == root_id
```

- [ ] **Step 2: Run the trace tests to verify the first one now fails against the old implementation**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_trace.py -v`
Expected: FAIL — `KeyError: 'span_id'` (the current `TraceRecorder.record()` doesn't produce that key yet)

- [ ] **Step 3: Modify `TraceRecorder`**

```python
# backend/agentos/core/trace.py
from __future__ import annotations

import uuid
from typing import Any

from agentos.core.events import EventEnvelope, InMemoryEventBus


class TraceRecorder:
    """Per-run trace span list with optional parent/child linkage
    (blueprint §55: a run should have a trace tree, not just a flat log).
    Each span gets a unique span_id; passing parent_span_id to record()
    nests it under an earlier span. No existing caller passes
    parent_span_id yet (Executor records flat, top-level spans) — that's
    an honest limitation of this phase, not something faked here.
    """

    def __init__(self, run_id: str, event_bus: InMemoryEventBus) -> None:
        self.run_id = run_id
        self._event_bus = event_bus
        self.spans: list[dict[str, Any]] = []

    def record(self, name: str, *, parent_span_id: str | None = None, **payload: Any) -> str:
        span_id = str(uuid.uuid4())
        span = {
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "name": name,
            "run_id": self.run_id,
            **payload,
        }
        self.spans.append(span)
        self._event_bus.publish(EventEnvelope(name=name, run_id=self.run_id, payload=payload))
        return span_id

    def export(self) -> list[dict[str, Any]]:
        return list(self.spans)
```

- [ ] **Step 4: Run the trace tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_trace.py -v`
Expected: 2 passed

- [ ] **Step 5: Add `last_trace` to `AgentRuntime`**

In `backend/agentos/core/runtime.py`, add `self.last_trace: TraceRecorder | None = None` to `__init__` (next to the existing `self.last_run: AgentRun | None = None`), and set `self.last_trace = trace` immediately after the line `trace = TraceRecorder(run_id=run.id, event_bus=event_bus)` inside `.run()`. No other line in the file changes.

- [ ] **Step 6: Add an assertion to the existing end-to-end test proving `last_trace` is populated**

In `backend/tests/agentos/test_runtime_end_to_end.py`, add these two lines to the end of `test_single_agent_loop_end_to_end_completes` (after the existing `assert runtime.last_run.is_terminal() is True` line):

```python
    assert runtime.last_trace is not None
    assert len(runtime.last_trace.export()) > 0
```

- [ ] **Step 7: Run the full runtime test file to verify it still passes**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_runtime_end_to_end.py -v`
Expected: 4 passed

- [ ] **Step 8: Write the failing `build_trace_tree` tests**

```python
# backend/tests/agentos/observability/test_trace_tree.py
from agentos.observability.trace_tree import build_trace_tree


def test_build_trace_tree_nests_children_under_parent():
    spans = [
        {"span_id": "root", "parent_span_id": None, "name": "agent_run.started", "run_id": "r1"},
        {"span_id": "child1", "parent_span_id": "root", "name": "tool_call.started", "run_id": "r1", "tool_name": "a"},
        {"span_id": "child2", "parent_span_id": "root", "name": "tool_call.started", "run_id": "r1", "tool_name": "b"},
    ]

    tree = build_trace_tree(spans)

    assert len(tree) == 1
    root = tree[0]
    assert root.span_id == "root"
    assert [c.span_id for c in root.children] == ["child1", "child2"]
    assert root.children[0].payload == {"tool_name": "a"}


def test_build_trace_tree_supports_grandchildren():
    spans = [
        {"span_id": "root", "parent_span_id": None, "name": "agent_run.started", "run_id": "r1"},
        {"span_id": "mid", "parent_span_id": "root", "name": "skill_execution", "run_id": "r1"},
        {"span_id": "leaf", "parent_span_id": "mid", "name": "tool_call.started", "run_id": "r1"},
    ]

    tree = build_trace_tree(spans)

    assert tree[0].children[0].children[0].span_id == "leaf"


def test_build_trace_tree_treats_multiple_top_level_spans_as_separate_roots():
    spans = [
        {"span_id": "a", "parent_span_id": None, "name": "a", "run_id": "r1"},
        {"span_id": "b", "parent_span_id": None, "name": "b", "run_id": "r1"},
    ]

    tree = build_trace_tree(spans)

    assert [n.span_id for n in tree] == ["a", "b"]
```

- [ ] **Step 9: Run the tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/observability/test_trace_tree.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.observability'`

- [ ] **Step 10: Create package scaffolding and the implementation**

```python
# backend/agentos/observability/__init__.py
```

```python
# backend/tests/agentos/observability/__init__.py
```

```python
# backend/agentos/observability/trace_tree.py
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TraceNode(BaseModel):
    span_id: str
    name: str
    payload: dict[str, Any] = Field(default_factory=dict)
    children: list["TraceNode"] = Field(default_factory=list)


TraceNode.model_rebuild()


def build_trace_tree(spans: list[dict[str, Any]]) -> list[TraceNode]:
    """Nest a flat TraceRecorder.export() span list into a tree by
    parent_span_id (blueprint §55). Spans with no parent (or an unknown
    parent) become roots — a run with no nesting at all (every span
    top-level, which is what real Executor-produced spans look like
    today) is still a valid, degenerate tree, not an error.
    """
    nodes: dict[str, TraceNode] = {}
    for span in spans:
        payload = {k: v for k, v in span.items() if k not in {"span_id", "parent_span_id", "name", "run_id"}}
        nodes[span["span_id"]] = TraceNode(span_id=span["span_id"], name=span["name"], payload=payload)

    roots: list[TraceNode] = []
    for span in spans:
        node = nodes[span["span_id"]]
        parent_id = span.get("parent_span_id")
        if parent_id is not None and parent_id in nodes:
            nodes[parent_id].children.append(node)
        else:
            roots.append(node)
    return roots
```

- [ ] **Step 11: Run the tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/observability/test_trace_tree.py -v`
Expected: 3 passed

- [ ] **Step 12: Commit**

```bash
git add backend/agentos/core/trace.py backend/agentos/core/runtime.py backend/tests/agentos/test_trace.py backend/tests/agentos/test_runtime_end_to_end.py backend/agentos/observability/__init__.py backend/agentos/observability/trace_tree.py backend/tests/agentos/observability/__init__.py backend/tests/agentos/observability/test_trace_tree.py
git commit -m "feat(agentos): add span/parent linkage, AgentRuntime.last_trace, and build_trace_tree"
```

---

### Task 2: `compute_run_metrics`

**Files:**
- Create: `backend/agentos/observability/metrics.py`
- Test: `backend/tests/agentos/observability/test_metrics.py`

**Interfaces:**
- Consumes: `AgentRun` from `agentos.core.models` (Phase 0).
- Produces: `RunMetrics(latency_seconds: float, span_count: int, tool_call_count: int)`; `compute_run_metrics(run: AgentRun, spans: list[dict]) -> RunMetrics`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/observability/test_metrics.py
from agentos.core.models import AgentRun, AgentRunStatus
from agentos.observability.metrics import compute_run_metrics


def test_compute_run_metrics_counts_completed_tool_calls():
    run = AgentRun(agent_key="a1", goal="g")
    run.transition(AgentRunStatus.RUNNING)
    run.transition(AgentRunStatus.COMPLETED)
    spans = [
        {"name": "agent_run.started"},
        {"name": "tool_call.started"},
        {"name": "tool_call.completed"},
        {"name": "tool_call.started"},
        {"name": "tool_call.completed"},
        {"name": "agent_run.completed"},
    ]

    metrics = compute_run_metrics(run, spans)

    assert metrics.tool_call_count == 2
    assert metrics.span_count == 6
    assert metrics.latency_seconds >= 0.0


def test_compute_run_metrics_zero_tool_calls_and_no_spans():
    run = AgentRun(agent_key="a1", goal="g")

    metrics = compute_run_metrics(run, [])

    assert metrics.tool_call_count == 0
    assert metrics.span_count == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/observability/test_metrics.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.observability.metrics'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/observability/metrics.py
from __future__ import annotations

from pydantic import BaseModel

from agentos.core.models import AgentRun


class RunMetrics(BaseModel):
    latency_seconds: float
    span_count: int
    tool_call_count: int


def compute_run_metrics(run: AgentRun, spans: list[dict]) -> RunMetrics:
    """Derive observability metrics purely from what's already recorded —
    no new instrumentation added here. Blueprint §56 token/model cost
    tracking needs real ModelProvider usage reporting, which is later
    hardening; latency and tool-call count are the metrics genuinely
    available from Phase 0/1 data as-is.
    """
    latency_seconds = (run.updated_at - run.created_at).total_seconds()
    tool_call_count = sum(1 for span in spans if span["name"] == "tool_call.completed")
    return RunMetrics(latency_seconds=latency_seconds, span_count=len(spans), tool_call_count=tool_call_count)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/observability/test_metrics.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/observability/metrics.py backend/tests/agentos/observability/test_metrics.py
git commit -m "feat(agentos): add compute_run_metrics"
```

---

### Task 3: `evaluate_agent_run`

**Files:**
- Create: `backend/agentos/evals/__init__.py`
- Create: `backend/agentos/evals/agent_eval.py`
- Create: `backend/tests/agentos/evals/__init__.py`
- Test: `backend/tests/agentos/evals/test_agent_eval.py`

**Interfaces:**
- Consumes: `AgentRun`, `AgentRunStatus` from `agentos.core.models` (Phase 0); `RunMetrics`, `compute_run_metrics` from `agentos.observability.metrics` (Task 2).
- Produces: `AgentEvalResult(goal_completion: bool, tool_calls_made: int, latency_seconds: float, human_acceptance: bool | None = None)`; `evaluate_agent_run(run: AgentRun, spans: list[dict], *, human_acceptance: bool | None = None) -> AgentEvalResult`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/evals/test_agent_eval.py
from agentos.core.models import AgentRun, AgentRunStatus
from agentos.evals.agent_eval import evaluate_agent_run


def test_evaluate_agent_run_marks_goal_completion_true_when_completed():
    run = AgentRun(agent_key="a1", goal="g")
    run.transition(AgentRunStatus.RUNNING)
    run.transition(AgentRunStatus.COMPLETED)

    result = evaluate_agent_run(run, [{"name": "tool_call.completed"}])

    assert result.goal_completion is True
    assert result.tool_calls_made == 1


def test_evaluate_agent_run_marks_goal_completion_false_when_failed():
    run = AgentRun(agent_key="a1", goal="g")
    run.transition(AgentRunStatus.RUNNING)
    run.transition(AgentRunStatus.FAILED)

    result = evaluate_agent_run(run, [])

    assert result.goal_completion is False


def test_evaluate_agent_run_carries_optional_human_acceptance():
    run = AgentRun(agent_key="a1", goal="g")

    result = evaluate_agent_run(run, [], human_acceptance=True)

    assert result.human_acceptance is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/evals/test_agent_eval.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.evals'`

- [ ] **Step 3: Create package scaffolding and the implementation**

```python
# backend/agentos/evals/__init__.py
```

```python
# backend/tests/agentos/evals/__init__.py
```

```python
# backend/agentos/evals/agent_eval.py
from __future__ import annotations

from pydantic import BaseModel

from agentos.core.models import AgentRun, AgentRunStatus
from agentos.observability.metrics import RunMetrics, compute_run_metrics


class AgentEvalResult(BaseModel):
    goal_completion: bool
    tool_calls_made: int
    latency_seconds: float
    human_acceptance: bool | None = None


def evaluate_agent_run(
    run: AgentRun, spans: list[dict], *, human_acceptance: bool | None = None
) -> AgentEvalResult:
    """Agent Eval (blueprint §52), the metrics achievable purely from
    Phase 0/1 data: goal completion (run status), tool_calls_made and
    latency (from RunMetrics), and human_acceptance as an optional
    caller-supplied signal (there's no feedback-collection mechanism yet
    to source it automatically — later hardening). Plan quality, tool
    accuracy, retry count, cost, and policy compliance need
    instrumentation this phase doesn't add (real ModelProvider usage
    tracking, a Planner that produces gradeable multi-step plans,
    GovernanceKernel wiring) — deliberately out of scope here.
    """
    metrics: RunMetrics = compute_run_metrics(run, spans)
    return AgentEvalResult(
        goal_completion=run.status == AgentRunStatus.COMPLETED,
        tool_calls_made=metrics.tool_call_count,
        latency_seconds=metrics.latency_seconds,
        human_acceptance=human_acceptance,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/evals/test_agent_eval.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/evals/__init__.py backend/agentos/evals/agent_eval.py backend/tests/agentos/evals/__init__.py backend/tests/agentos/evals/test_agent_eval.py
git commit -m "feat(agentos): add evaluate_agent_run"
```

---

### Task 4: `Workflow` gains `failed_step_name`/`had_approval_gate`; `evaluate_workflow`

**Files:**
- Modify: `backend/agentos/workflows/models.py`
- Modify: `backend/agentos/workflows/engine.py`
- Modify: `backend/tests/agentos/workflows/test_models.py`
- Modify: `backend/tests/agentos/workflows/test_engine.py`
- Create: `backend/agentos/evals/workflow_eval.py`
- Test: `backend/tests/agentos/evals/test_workflow_eval.py`

**Interfaces:**
- Produces (changed): `Workflow` gains `failed_step_name: str | None = None` and `had_approval_gate: bool = False`; `WorkflowEngine._run_from`/`.resume` set `failed_step_name` to the failing step's `.name` whenever transitioning to `FAILED`, and set `had_approval_gate = True` the first time a step returns `WAITING_APPROVAL`.
- Produces (new): `WorkflowEvalResult(completed: bool, failed_step_name: str | None, time_to_completion_seconds: float, reached_approval_gate: bool)`; `evaluate_workflow(workflow: Workflow) -> WorkflowEvalResult`.

- [ ] **Step 1: Add a test for the new `Workflow` field defaults**

Append to `backend/tests/agentos/workflows/test_models.py`:

```python
def test_workflow_new_fields_default_to_none_and_false():
    workflow = Workflow(name="onboarding")
    assert workflow.failed_step_name is None
    assert workflow.had_approval_gate is False
```

- [ ] **Step 2: Update the existing engine tests with assertions on the new fields**

In `backend/tests/agentos/workflows/test_engine.py`:

- In `test_workflow_completes_when_all_deterministic_steps_succeed`, append:
  ```python
      assert workflow.had_approval_gate is False
      assert workflow.failed_step_name is None
  ```
- In `test_workflow_pauses_at_approval_gate_and_resumes_when_approved`, right after the existing `assert workflow.pending_approval_id is not None` line, add:
  ```python
      assert workflow.had_approval_gate is True
  ```
  and after the existing `assert resumed.state["notified"] is True` line, add:
  ```python
      assert resumed.had_approval_gate is True
  ```
- In `test_workflow_fails_when_resumed_approval_is_denied`, append:
  ```python
      assert resumed.failed_step_name == "approve-send"
  ```

- [ ] **Step 3: Run the workflows test suite to verify the new/updated assertions fail against the current implementation**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/workflows/test_models.py tests/agentos/workflows/test_engine.py -v`
Expected: FAIL — `AttributeError: 'Workflow' object has no attribute 'failed_step_name'` (and similarly for `had_approval_gate`)

- [ ] **Step 4: Modify `Workflow`**

In `backend/agentos/workflows/models.py`, add two fields to the `Workflow` class, right after `pending_approval_id: str | None = None`:

```python
    failed_step_name: str | None = None
    had_approval_gate: bool = False
```

- [ ] **Step 5: Modify `WorkflowEngine`**

In `backend/agentos/workflows/engine.py`, update `_run_from` and `resume`:

```python
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
            workflow.failed_step_name = step.name
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
                workflow.had_approval_gate = True
                workflow.transition(WorkflowStatus.WAITING_APPROVAL)
                return workflow

            if outcome.status == StepStatus.FAILED:
                workflow.failed_step_name = step.name
                workflow.error = outcome.error
                workflow.transition(WorkflowStatus.FAILED)
                return workflow

            workflow.state.update(outcome.updates)
            workflow.current_step_index += 1

        workflow.transition(WorkflowStatus.COMPLETED)
        return workflow
```

(Only the two `if outcome.status == StepStatus.FAILED:` blocks and the `WAITING_APPROVAL` block change — the rest of the file is unchanged.)

- [ ] **Step 6: Run the workflows test suite to verify everything passes**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/workflows/ -v`
Expected: all passing — 7 (models, was 6) + 5 (steps) + 5 (approval_step) + 4 (engine, same count, new assertions inside existing tests) + 2 (full workflow integration) = 23 total

- [ ] **Step 7: Write the failing `evaluate_workflow` tests**

```python
# backend/tests/agentos/evals/test_workflow_eval.py
from agentos.evals.workflow_eval import evaluate_workflow
from agentos.workflows.models import Workflow, WorkflowStatus


def test_evaluate_workflow_completed_without_approval_gate():
    workflow = Workflow(name="flow")
    workflow.transition(WorkflowStatus.RUNNING)
    workflow.transition(WorkflowStatus.COMPLETED)

    result = evaluate_workflow(workflow)

    assert result.completed is True
    assert result.failed_step_name is None
    assert result.reached_approval_gate is False
    assert result.time_to_completion_seconds >= 0.0


def test_evaluate_workflow_failed_reports_the_failing_step():
    workflow = Workflow(name="flow")
    workflow.transition(WorkflowStatus.RUNNING)
    workflow.failed_step_name = "business-write"
    workflow.transition(WorkflowStatus.FAILED)

    result = evaluate_workflow(workflow)

    assert result.completed is False
    assert result.failed_step_name == "business-write"


def test_evaluate_workflow_reports_approval_gate_was_reached():
    workflow = Workflow(name="flow")
    workflow.transition(WorkflowStatus.RUNNING)
    workflow.had_approval_gate = True
    workflow.transition(WorkflowStatus.COMPLETED)

    result = evaluate_workflow(workflow)

    assert result.reached_approval_gate is True
```

- [ ] **Step 8: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/evals/test_workflow_eval.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.evals.workflow_eval'`

- [ ] **Step 9: Write the implementation**

```python
# backend/agentos/evals/workflow_eval.py
from __future__ import annotations

from pydantic import BaseModel

from agentos.workflows.models import Workflow, WorkflowStatus


class WorkflowEvalResult(BaseModel):
    completed: bool
    failed_step_name: str | None
    time_to_completion_seconds: float
    reached_approval_gate: bool


def evaluate_workflow(workflow: Workflow) -> WorkflowEvalResult:
    """Workflow Eval (blueprint §53), the metrics achievable purely from
    the Phase 8 Workflow object: completion, which step failed (if any),
    and wall-clock time to reach a terminal state. Retry count and cost
    aren't tracked by WorkflowEngine yet — later hardening. Approval wait
    duration needs the Approval object's own timestamps
    (created_at/decided_at, already on Phase 8's Approval) joined in by
    the caller, since Workflow itself only stores the approval id, not
    the Approval object.
    """
    return WorkflowEvalResult(
        completed=workflow.status == WorkflowStatus.COMPLETED,
        failed_step_name=workflow.failed_step_name,
        time_to_completion_seconds=(workflow.updated_at - workflow.created_at).total_seconds(),
        reached_approval_gate=workflow.had_approval_gate,
    )
```

- [ ] **Step 10: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/evals/test_workflow_eval.py -v`
Expected: 3 passed

- [ ] **Step 11: Commit**

```bash
git add backend/agentos/workflows/models.py backend/agentos/workflows/engine.py backend/tests/agentos/workflows/test_models.py backend/tests/agentos/workflows/test_engine.py backend/agentos/evals/workflow_eval.py backend/tests/agentos/evals/test_workflow_eval.py
git commit -m "feat(agentos): track Workflow failure/approval-gate state and add evaluate_workflow"
```

---

### Task 5: `evaluate_business_outcome`

**Files:**
- Create: `backend/agentos/evals/business_outcome_eval.py`
- Test: `backend/tests/agentos/evals/test_business_outcome_eval.py`

**Interfaces:**
- Produces: `BusinessOutcomeEvalResult(metric_name: str, target: float, actual: float, achievement_ratio: float, achieved: bool)`; `evaluate_business_outcome(metric_name: str, *, target: float, actual: float) -> BusinessOutcomeEvalResult`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/evals/test_business_outcome_eval.py
from agentos.evals.business_outcome_eval import evaluate_business_outcome


def test_evaluate_business_outcome_full_achievement():
    result = evaluate_business_outcome("kr_hit_10k_mrr", target=10000, actual=10000)
    assert result.achievement_ratio == 1.0
    assert result.achieved is True


def test_evaluate_business_outcome_partial_achievement():
    result = evaluate_business_outcome("kr_hit_10k_mrr", target=10000, actual=2500)
    assert result.achievement_ratio == 0.25
    assert result.achieved is False


def test_evaluate_business_outcome_clamps_at_one_when_actual_exceeds_target():
    result = evaluate_business_outcome("kr_hit_10k_mrr", target=10000, actual=15000)
    assert result.achievement_ratio == 1.0
    assert result.achieved is True


def test_evaluate_business_outcome_handles_zero_target():
    result = evaluate_business_outcome("ctr", target=0, actual=5)
    assert result.achievement_ratio == 0.0
    assert result.achieved is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/evals/test_business_outcome_eval.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.evals.business_outcome_eval'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/evals/business_outcome_eval.py
from __future__ import annotations

from pydantic import BaseModel


class BusinessOutcomeEvalResult(BaseModel):
    metric_name: str
    target: float
    actual: float
    achievement_ratio: float
    achieved: bool


def evaluate_business_outcome(metric_name: str, *, target: float, actual: float) -> BusinessOutcomeEvalResult:
    """Business Outcome Eval (blueprint §51/§54): the final layer that
    grounds an eval in a real outcome, not just an LLM judge. Deliberately
    generic — works for the blueprint's Marketing example (CTR, conversion,
    CAC) and OKR example (KR completion) alike, since both reduce to
    "actual vs target" the same way §26's OKR key-result scoring does on
    the Encore side (services/okr/scoring.ts::computeKeyResultScore, added
    in Phase 2).
    """
    ratio = 0.0 if target <= 0 else min(actual / target, 1.0)
    return BusinessOutcomeEvalResult(
        metric_name=metric_name,
        target=target,
        actual=actual,
        achievement_ratio=ratio,
        achieved=ratio >= 1.0,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/evals/test_business_outcome_eval.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/evals/business_outcome_eval.py backend/tests/agentos/evals/test_business_outcome_eval.py
git commit -m "feat(agentos): add evaluate_business_outcome"
```

---

### Task 6: Integration — real `AgentRuntime`, real `WorkflowEngine`, all three eval layers

**Files:**
- Test: `backend/tests/agentos/evals/test_full_eval_integration.py`

**Interfaces:** None new — proves Tasks 1–5 work together over real Phase 1/8 executions, not just hand-built fixtures.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/evals/test_full_eval_integration.py
import pytest

from agentos.core.approval import ApprovalService
from agentos.core.model_provider import ModelResponse, StubModelProvider, ToolCallRequest
from agentos.core.models import TaskContext
from agentos.core.policy import PermissionClass, PolicyEngine
from agentos.core.runtime import AgentRuntime
from agentos.evals.agent_eval import evaluate_agent_run
from agentos.evals.business_outcome_eval import evaluate_business_outcome
from agentos.evals.workflow_eval import evaluate_workflow
from agentos.observability.trace_tree import build_trace_tree
from agentos.tools.registry import ToolRegistry, ToolSpec
from agentos.workflows.approval_step import ApprovalGateStep
from agentos.workflows.engine import WorkflowEngine
from agentos.workflows.steps import DeterministicStep


async def _echo(arguments: dict) -> dict:
    return {"echoed": arguments.get("text")}


async def _business_write(state: dict) -> dict:
    return {"crm_record_id": "crm-42"}


@pytest.mark.asyncio
async def test_agent_eval_reflects_a_real_agent_runtime_run_including_its_tool_call():
    registry = ToolRegistry()
    registry.register(ToolSpec(name="echo", description="d", handler=_echo))
    provider = StubModelProvider(
        [
            ModelResponse(tool_call=ToolCallRequest(tool_name="echo", arguments={"text": "hi"})),
            ModelResponse(text="Echoed: hi"),
        ]
    )
    runtime = AgentRuntime(provider, registry)
    task = TaskContext(goal="echo hi", agent_key="echo_agent", workspace_id="ws1")

    await runtime.run(task)

    assert runtime.last_trace is not None
    spans = runtime.last_trace.export()
    eval_result = evaluate_agent_run(runtime.last_run, spans, human_acceptance=True)

    assert eval_result.goal_completion is True
    assert eval_result.tool_calls_made == 1
    assert eval_result.human_acceptance is True

    # Executor doesn't pass parent_span_id yet (see Task 1's docstring), so
    # every span is still a top-level root — an honest, degenerate tree.
    tree = build_trace_tree(spans)
    assert len(tree) == len(spans)


@pytest.mark.asyncio
async def test_workflow_eval_reflects_a_denied_approval_end_to_end():
    approval_service = ApprovalService()
    engine = WorkflowEngine()
    gate = ApprovalGateStep(
        "human-approval",
        policy_engine=PolicyEngine(),
        approval_service=approval_service,
        permission=PermissionClass.MODIFY_BUSINESS_DATA,
        action="create_crm_record",
        subject_key="goal",
        requester="researcher",
    )
    steps = [gate, DeterministicStep("business-write", _business_write)]

    workflow = await engine.start("prospect-flow", steps, {"goal": "research Acme Corp"})
    approval_service.decide(workflow.pending_approval_id, reviewer="founder", approved=False, reason="not ready")
    resumed = await engine.resume(workflow, steps)

    eval_result = evaluate_workflow(resumed)

    assert eval_result.completed is False
    assert eval_result.failed_step_name == "human-approval"
    assert eval_result.reached_approval_gate is True


def test_business_outcome_eval_matches_the_blueprint_okr_example():
    result = evaluate_business_outcome("hit_10k_mrr", target=10000, actual=6500)

    assert result.achievement_ratio == 0.65
    assert result.achieved is False
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/evals/test_full_eval_integration.py -v`
Expected: 3 passed — this is a pure integration proof over already-implemented Tasks 1–5, so there is no separate "watch it fail first" step: if any test fails here, it points at a real incompatibility between the eval layer and `AgentRuntime`/`WorkflowEngine`, not a missing-module error — stop and investigate rather than proceeding.

- [ ] **Step 3: Run the full `observability` + `evals` suites to confirm everything holds together**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/observability/ tests/agentos/evals/ -v`
Expected: all passing — 3 (trace_tree) + 2 (metrics) + 3 (agent_eval) + 3 (workflow_eval) + 4 (business_outcome_eval) + 3 (full integration) = 18 total

- [ ] **Step 4: Commit**

```bash
git add backend/tests/agentos/evals/test_full_eval_integration.py
git commit -m "test(agentos): prove the eval layer works over real AgentRuntime and WorkflowEngine runs"
```

---

## Verification (end of Phase 9)

1. Run the full new/modified suites: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/observability/ tests/agentos/evals/ tests/agentos/test_trace.py tests/agentos/test_runtime_end_to_end.py tests/agentos/workflows/ -v` — all pass.
2. Run the full `agentos` suite: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/ -v` — no regressions in Phase 0/1/3/4/5/6/7/8 tests.
3. Confirm no production wiring was introduced: `grep -rn "import agentos\|from agentos" backend --include="*.py" | grep -v "^backend/agentos/\|^backend/tests/agentos/"` returns no results.
4. Manually diff `agentos/workflows/engine.py` against its Phase 8 version and confirm the only changes are the two `failed_step_name`/`had_approval_gate` assignments — no control-flow changed.

## Next steps (not part of this plan)

Per `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §4: Phase 10 (Self-Improvement — capability gap detection, skill distillation, canary, promote) is next. It should get its own plan via `superpowers:writing-plans` once this one is merged and reviewed. Explicitly deferred and not yet scoped anywhere: wiring real parent/child span nesting through `Executor` (so a real run's trace tree is actually nested — Context Retrieval → Skill Search → Skill Execution → Tool Call → Tool Call → Review → Final Output, per blueprint §55's example, rather than today's flat list of roots); real token/cost usage tracking on `ModelProvider` responses, needed for blueprint §56 cost metrics and the `cost` field of Agent/Workflow Eval; and an `Approval`-joined workflow-eval metric for approval wait time (needs the caller to pass the `Approval` object alongside the `Workflow`, since `Workflow` only stores the id).
