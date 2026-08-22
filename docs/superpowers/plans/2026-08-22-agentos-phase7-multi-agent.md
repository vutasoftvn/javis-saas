# AgentOS Phase 7 — Multi-Agent (Delegation, Parallel, Supervisor, Debate) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the multi-agent composition primitives the blueprint describes (§9.2: Sequential, Parallel, Delegation, Debate/Critic, Supervisor) on top of the single-agent `Agent` protocol/`AgentRuntime` already built in Phase 1 — without ever forcing multi-agent as a default. Per Phase 7 of the roadmap in `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §4 ("§9.1: không phải mọi bài toán đều multi-agent... ưu tiên single agent → delegation → multi-agent parallel").

**Architecture:** New subpackage `backend/agentos/agents/`, matching the blueprint's own top-level layout (§2 lists `agentos/agents/` alongside `core/`, `skills/`, `tools/`, `memory/`). An `AgentRegistry` holds live `Agent`-protocol instances tagged with a `domain` and `intents` list — unlike `SkillRegistry` (Phase 4) there is no filesystem discovery, since agents are code objects assembled by whoever builds a topology, not files to scan. `score_agent()` reuses the exact same naive term-overlap relevance scoring already proven twice (`agentos.memory.retrieval.score_relevance` in Phase 3, `agentos.skills.router.score_skill` in Phase 4) — same MVP tradeoff, same caveat about being a placeholder for real semantic matching. `SupervisorAgent` itself implements the `Agent` protocol: it scores every registered specialist against the task goal and delegates the whole task to the best match, returning that specialist's own `AgentResult` — because it's just another `Agent`, a `SupervisorAgent` can be registered as a specialist under another `SupervisorAgent` if a topology ever needs that. `SequentialPipeline` chains agents, feeding each one's output forward as the next one's goal, stopping at the first non-`COMPLETED` result. `ParallelFanOut` runs several agents concurrently via `asyncio.gather` and returns every result regardless of individual failures — the point of fan-out is that one branch failing shouldn't block the others. `DebateLoop` implements the Generator/Critic pattern: generate, critique, revise-if-not-approved, capped at `max_rounds` so it can never loop forever. A final integration task proves all of this composes over real `AgentRuntime` instances (Phase 1), not just test doubles.

**Tech Stack:** Python 3.11, pydantic 2.13, pytest + pytest-asyncio — same as prior `agentos` phases, no new dependencies.

## Global Constraints

- New code lives under `backend/agentos/agents/` and `backend/tests/agentos/agents/`. Do not modify any file under `backend/agentos/core/`, `backend/agentos/memory/`, `backend/agentos/skills/`, or `backend/agentos/tools/` — this phase only adds a new composition layer on top of the already-stable `Agent` protocol and `AgentRuntime`.
- **Prerequisite:** this plan assumes Phase 1's `AgentRuntime`, `Agent` protocol, `TaskContext`, `AgentResult`, `AgentRunStatus`, `StubModelProvider`, and `ToolRegistry` already exist (Task 6 of this plan exercises them directly).
- Every multi-agent primitive returns results the same way `AgentRuntime` does — a `FAILED` `AgentResult` with an `error` message, never a raised exception for an expected "couldn't complete" case (e.g. no specialist matched). This keeps every composition primitive itself usable as an `Agent`, which requires `run()` to always return an `AgentResult`, not raise.
- `score_agent()` is a deliberately-flagged MVP placeholder (naive term overlap) — do not try to make it "smarter" in this plan; that's consistent with the same call made twice already for memory retrieval and skill routing.
- `TaskContext` is immutable-by-convention pydantic — use `.model_copy(update={...})` to derive a new task for a next pipeline stage, never mutate a `TaskContext` in place.
- Every async test needs `@pytest.mark.asyncio` (`backend/pytest.ini` has `asyncio_mode = strict`).
- Run tests via: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/agents/<file> -v`.
- Source spec: `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §3.2/§9/§10 (Multi-Agent Architecture, Agent roles), §4 (Phase 7 scope).

---

## File Structure

```text
backend/agentos/agents/
├── __init__.py
├── agent_registry.py    # AgentRecord, AgentNotFoundError, AgentRegistry
├── supervisor.py           # score_agent, SupervisorAgent
├── sequential.py              # SequentialPipeline
├── parallel.py                   # ParallelFanOut
└── debate.py                        # DebateLoop

backend/tests/agentos/agents/
├── __init__.py
├── test_agent_registry.py
├── test_supervisor.py
├── test_sequential.py
├── test_parallel.py
├── test_debate.py
└── test_real_agent_runtime_integration.py
```

---

### Task 1: `AgentRegistry`

**Files:**
- Create: `backend/agentos/agents/__init__.py`
- Create: `backend/agentos/agents/agent_registry.py`
- Create: `backend/tests/agentos/agents/__init__.py`
- Test: `backend/tests/agentos/agents/test_agent_registry.py`

**Interfaces:**
- Consumes: `Agent` from `agentos.core.agent` (Phase 1).
- Produces: `AgentRecord(agent_key: str, agent: Agent, domain: str, intents: list[str])` (dataclass); `AgentNotFoundError(agent_key: str)`; `AgentRegistry` with `.register(agent_key: str, agent: Agent, *, domain: str, intents: list[str]) -> None`, `.get(agent_key: str) -> AgentRecord`, `.list(*, domain: str | None = None) -> list[AgentRecord]`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/agents/test_agent_registry.py
import pytest

from agentos.agents.agent_registry import AgentNotFoundError, AgentRegistry
from agentos.core.models import AgentResult, AgentRunStatus, TaskContext


class _FakeAgent:
    async def run(self, task: TaskContext) -> AgentResult:
        return AgentResult(run_id="r1", status=AgentRunStatus.COMPLETED, output="ok")


def test_register_and_get():
    registry = AgentRegistry()
    agent = _FakeAgent()
    registry.register("sales_specialist", agent, domain="sales", intents=["qualify lead"])

    record = registry.get("sales_specialist")

    assert record.agent is agent
    assert record.domain == "sales"
    assert record.intents == ["qualify lead"]


def test_get_missing_agent_raises():
    registry = AgentRegistry()
    with pytest.raises(AgentNotFoundError):
        registry.get("missing")


def test_list_filters_by_domain():
    registry = AgentRegistry()
    registry.register("sales_specialist", _FakeAgent(), domain="sales", intents=["qualify lead"])
    registry.register("finance_specialist", _FakeAgent(), domain="finance", intents=["review invoice"])

    sales_only = registry.list(domain="sales")

    assert [r.agent_key for r in sales_only] == ["sales_specialist"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/agents/test_agent_registry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.agents'`

- [ ] **Step 3: Create package scaffolding and the implementation**

```python
# backend/agentos/agents/__init__.py
```

```python
# backend/tests/agentos/agents/__init__.py
```

```python
# backend/agentos/agents/agent_registry.py
from __future__ import annotations

from dataclasses import dataclass, field

from agentos.core.agent import Agent


@dataclass
class AgentRecord:
    agent_key: str
    agent: Agent
    domain: str
    intents: list[str] = field(default_factory=list)


class AgentNotFoundError(Exception):
    def __init__(self, agent_key: str) -> None:
        super().__init__(f"Agent not registered: {agent_key}")
        self.agent_key = agent_key


class AgentRegistry:
    """In-process registry of live Agent instances available for
    delegation (blueprint §9/§10). Unlike SkillRegistry (Phase 4), there
    is no filesystem discovery — agents are code objects constructed and
    registered explicitly by whoever assembles the multi-agent topology.
    """

    def __init__(self) -> None:
        self._records: dict[str, AgentRecord] = {}

    def register(self, agent_key: str, agent: Agent, *, domain: str, intents: list[str]) -> None:
        self._records[agent_key] = AgentRecord(agent_key=agent_key, agent=agent, domain=domain, intents=intents)

    def get(self, agent_key: str) -> AgentRecord:
        try:
            return self._records[agent_key]
        except KeyError:
            raise AgentNotFoundError(agent_key) from None

    def list(self, *, domain: str | None = None) -> list[AgentRecord]:
        records = list(self._records.values())
        if domain is not None:
            records = [r for r in records if r.domain == domain]
        return records
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/agents/test_agent_registry.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/agents/__init__.py backend/agentos/agents/agent_registry.py backend/tests/agentos/agents/__init__.py backend/tests/agentos/agents/test_agent_registry.py
git commit -m "feat(agentos): add AgentRegistry"
```

---

### Task 2: `score_agent` + `SupervisorAgent`

**Files:**
- Create: `backend/agentos/agents/supervisor.py`
- Test: `backend/tests/agentos/agents/test_supervisor.py`

**Interfaces:**
- Consumes: `AgentRegistry` (Task 1); `Agent`, `AgentResult`, `AgentRunStatus`, `TaskContext` from `agentos.core` (Phase 1).
- Produces: `score_agent(goal: str, intents: list[str]) -> float`; `SupervisorAgent(registry: AgentRegistry, *, domain: str | None = None)` implementing `Agent` — `.run(task: TaskContext) -> AgentResult` delegates to the highest-scoring specialist, or returns a `FAILED` result if nothing scores above zero.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/agents/test_supervisor.py
import pytest

from agentos.agents.agent_registry import AgentRegistry
from agentos.agents.supervisor import SupervisorAgent, score_agent
from agentos.core.agent import Agent
from agentos.core.models import AgentResult, AgentRunStatus, TaskContext


class _FakeAgent:
    def __init__(self, tag: str) -> None:
        self._tag = tag

    async def run(self, task: TaskContext) -> AgentResult:
        return AgentResult(run_id="r1", status=AgentRunStatus.COMPLETED, output=f"handled by {self._tag}")


def test_score_agent_rewards_matching_intents():
    assert score_agent("qualify this lead", ["qualify lead", "score lead"]) > score_agent(
        "qualify this lead", ["review invoice"]
    )


def test_supervisor_satisfies_agent_protocol():
    assert isinstance(SupervisorAgent(AgentRegistry()), Agent)


@pytest.mark.asyncio
async def test_supervisor_delegates_to_highest_scoring_specialist():
    registry = AgentRegistry()
    registry.register(
        "sales_specialist", _FakeAgent("sales"), domain="sales", intents=["qualify lead", "sales outreach"]
    )
    registry.register("finance_specialist", _FakeAgent("finance"), domain="finance", intents=["review invoice"])
    supervisor = SupervisorAgent(registry)
    task = TaskContext(goal="qualify this new lead", agent_key="supervisor", workspace_id="ws1")

    result = await supervisor.run(task)

    assert result.status == AgentRunStatus.COMPLETED
    assert result.output == "handled by sales"


@pytest.mark.asyncio
async def test_supervisor_respects_domain_scope():
    registry = AgentRegistry()
    registry.register("sales_specialist", _FakeAgent("sales"), domain="sales", intents=["qualify lead"])
    registry.register("finance_specialist", _FakeAgent("finance"), domain="finance", intents=["qualify lead"])
    supervisor = SupervisorAgent(registry, domain="finance")
    task = TaskContext(goal="qualify this lead", agent_key="supervisor", workspace_id="ws1")

    result = await supervisor.run(task)

    assert result.output == "handled by finance"


@pytest.mark.asyncio
async def test_supervisor_returns_failed_result_when_no_specialist_matches():
    registry = AgentRegistry()
    registry.register("sales_specialist", _FakeAgent("sales"), domain="sales", intents=["qualify lead"])
    supervisor = SupervisorAgent(registry)
    task = TaskContext(goal="completely unrelated task", agent_key="supervisor", workspace_id="ws1")

    result = await supervisor.run(task)

    assert result.status == AgentRunStatus.FAILED
    assert result.error is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/agents/test_supervisor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.agents.supervisor'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/agents/supervisor.py
from __future__ import annotations

import re
import uuid

from agentos.agents.agent_registry import AgentRegistry
from agentos.core.models import AgentResult, AgentRunStatus, TaskContext

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_PATTERN.findall(text.lower()))


def score_agent(goal: str, intents: list[str]) -> float:
    """Naive term-overlap relevance score in [0, 1] — same MVP approach as
    agentos.memory.retrieval.score_relevance (Phase 3) and
    agentos.skills.router.score_skill (Phase 4), applied here to agent
    capability matching (blueprint §9 Supervisor pattern).
    """
    goal_tokens = _tokenize(goal)
    intent_tokens: set[str] = set()
    for intent in intents:
        intent_tokens |= _tokenize(intent)
    if not goal_tokens or not intent_tokens:
        return 0.0
    return len(goal_tokens & intent_tokens) / len(goal_tokens)


class SupervisorAgent:
    """Supervisor pattern (blueprint §9.2): picks the best-scoring
    specialist from an AgentRegistry and delegates the entire task to it.
    Implements the Agent protocol itself, so a SupervisorAgent can be
    nested as a specialist under another SupervisorAgent if a topology
    ever needs that.
    """

    def __init__(self, registry: AgentRegistry, *, domain: str | None = None) -> None:
        self._registry = registry
        self._domain = domain

    async def run(self, task: TaskContext) -> AgentResult:
        candidates = self._registry.list(domain=self._domain)
        scored = [(score_agent(task.goal, record.intents), record) for record in candidates]
        relevant = [(score, record) for score, record in scored if score > 0]
        if not relevant:
            return AgentResult(
                run_id=str(uuid.uuid4()),
                status=AgentRunStatus.FAILED,
                error=f"No registered specialist scored above zero for goal: {task.goal!r}",
            )
        relevant.sort(key=lambda pair: pair[0], reverse=True)
        _, chosen = relevant[0]
        return await chosen.agent.run(task)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/agents/test_supervisor.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/agents/supervisor.py backend/tests/agentos/agents/test_supervisor.py
git commit -m "feat(agentos): add score_agent and SupervisorAgent"
```

---

### Task 3: `SequentialPipeline`

**Files:**
- Create: `backend/agentos/agents/sequential.py`
- Test: `backend/tests/agentos/agents/test_sequential.py`

**Interfaces:**
- Consumes: `Agent`, `AgentResult`, `AgentRunStatus`, `TaskContext` from `agentos.core` (Phase 1).
- Produces: `SequentialPipeline(agents: list[Agent])` with `.run(initial_task: TaskContext) -> list[AgentResult]` — feeds each agent's `output` forward as the next agent's `goal`; stops at the first non-`COMPLETED` result.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/agents/test_sequential.py
import pytest

from agentos.agents.sequential import SequentialPipeline
from agentos.core.models import AgentResult, AgentRunStatus, TaskContext


class _EchoAgent:
    def __init__(self, prefix: str) -> None:
        self._prefix = prefix

    async def run(self, task: TaskContext) -> AgentResult:
        return AgentResult(run_id="r", status=AgentRunStatus.COMPLETED, output=f"{self._prefix}:{task.goal}")


class _FailingAgent:
    async def run(self, task: TaskContext) -> AgentResult:
        return AgentResult(run_id="r", status=AgentRunStatus.FAILED, error="boom")


@pytest.mark.asyncio
async def test_sequential_pipeline_feeds_output_forward():
    pipeline = SequentialPipeline([_EchoAgent("plan"), _EchoAgent("execute")])
    task = TaskContext(goal="ship the feature", agent_key="pipeline", workspace_id="ws1")

    results = await pipeline.run(task)

    assert [r.output for r in results] == ["plan:ship the feature", "execute:plan:ship the feature"]


@pytest.mark.asyncio
async def test_sequential_pipeline_stops_on_first_failure():
    pipeline = SequentialPipeline([_EchoAgent("plan"), _FailingAgent(), _EchoAgent("never runs")])
    task = TaskContext(goal="ship the feature", agent_key="pipeline", workspace_id="ws1")

    results = await pipeline.run(task)

    assert len(results) == 2
    assert results[-1].status == AgentRunStatus.FAILED
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/agents/test_sequential.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.agents.sequential'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/agents/sequential.py
from __future__ import annotations

from agentos.core.agent import Agent
from agentos.core.models import AgentResult, AgentRunStatus, TaskContext


class SequentialPipeline:
    """Sequential multi-agent flow (blueprint §9.2): each agent's output
    becomes the next agent's goal. Stops at the first non-COMPLETED
    result — a broken link in the chain should not silently continue.
    """

    def __init__(self, agents: list[Agent]) -> None:
        self._agents = agents

    async def run(self, initial_task: TaskContext) -> list[AgentResult]:
        results: list[AgentResult] = []
        current_task = initial_task
        for agent in self._agents:
            result = await agent.run(current_task)
            results.append(result)
            if result.status != AgentRunStatus.COMPLETED:
                break
            current_task = current_task.model_copy(update={"goal": result.output or current_task.goal})
        return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/agents/test_sequential.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/agents/sequential.py backend/tests/agentos/agents/test_sequential.py
git commit -m "feat(agentos): add SequentialPipeline"
```

---

### Task 4: `ParallelFanOut`

**Files:**
- Create: `backend/agentos/agents/parallel.py`
- Test: `backend/tests/agentos/agents/test_parallel.py`

**Interfaces:**
- Consumes: `Agent`, `AgentResult`, `TaskContext` from `agentos.core` (Phase 1).
- Produces: `ParallelFanOut(agents: list[Agent])` with `.run(task: TaskContext) -> list[AgentResult]` — runs every agent concurrently against the same task via `asyncio.gather`, preserving input order in the result list.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/agents/test_parallel.py
import asyncio

import pytest

from agentos.agents.parallel import ParallelFanOut
from agentos.core.models import AgentResult, AgentRunStatus, TaskContext


class _SlowEchoAgent:
    def __init__(self, tag: str, delay: float = 0.0) -> None:
        self._tag = tag
        self._delay = delay

    async def run(self, task: TaskContext) -> AgentResult:
        if self._delay:
            await asyncio.sleep(self._delay)
        return AgentResult(run_id="r", status=AgentRunStatus.COMPLETED, output=self._tag)


@pytest.mark.asyncio
async def test_parallel_fan_out_collects_all_results_in_order():
    fan_out = ParallelFanOut([_SlowEchoAgent("market"), _SlowEchoAgent("competitor"), _SlowEchoAgent("customer")])
    task = TaskContext(goal="research", agent_key="fanout", workspace_id="ws1")

    results = await fan_out.run(task)

    assert [r.output for r in results] == ["market", "competitor", "customer"]


@pytest.mark.asyncio
async def test_parallel_fan_out_runs_concurrently_not_sequentially():
    fan_out = ParallelFanOut([_SlowEchoAgent("a", delay=0.05), _SlowEchoAgent("b", delay=0.05)])
    task = TaskContext(goal="research", agent_key="fanout", workspace_id="ws1")

    loop = asyncio.get_event_loop()
    start = loop.time()
    await fan_out.run(task)
    elapsed = loop.time() - start

    assert elapsed < 0.09  # would be >= 0.1 if the two agents ran sequentially
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/agents/test_parallel.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.agents.parallel'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/agents/parallel.py
from __future__ import annotations

import asyncio

from agentos.core.agent import Agent
from agentos.core.models import AgentResult, TaskContext


class ParallelFanOut:
    """Parallel multi-agent flow (blueprint §9.2): run several agents
    concurrently against the same task and collect every result — no
    early exit on failure, since the whole point of fan-out is that one
    branch's failure shouldn't block the others from completing.
    """

    def __init__(self, agents: list[Agent]) -> None:
        self._agents = agents

    async def run(self, task: TaskContext) -> list[AgentResult]:
        return list(await asyncio.gather(*(agent.run(task) for agent in self._agents)))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/agents/test_parallel.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/agents/parallel.py backend/tests/agentos/agents/test_parallel.py
git commit -m "feat(agentos): add ParallelFanOut"
```

---

### Task 5: `DebateLoop`

**Files:**
- Create: `backend/agentos/agents/debate.py`
- Test: `backend/tests/agentos/agents/test_debate.py`

**Interfaces:**
- Consumes: `Agent`, `AgentResult`, `AgentRunStatus`, `TaskContext` from `agentos.core` (Phase 1).
- Produces: `DEFAULT_MAX_ROUNDS = 2`; `DebateLoop(generator: Agent, critic: Agent, *, max_rounds: int = DEFAULT_MAX_ROUNDS)` with `.run(task: TaskContext) -> tuple[AgentResult, AgentResult]` (returns `(generator_result, critic_result)` from the final round).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/agents/test_debate.py
import pytest

from agentos.agents.debate import DebateLoop
from agentos.core.models import AgentResult, AgentRunStatus, TaskContext


class _ScriptedAgent:
    def __init__(self, outputs: list[str]) -> None:
        self._outputs = list(outputs)

    async def run(self, task: TaskContext) -> AgentResult:
        output = self._outputs.pop(0)
        return AgentResult(run_id="r", status=AgentRunStatus.COMPLETED, output=output)


@pytest.mark.asyncio
async def test_debate_loop_stops_immediately_when_critic_approves():
    generator = _ScriptedAgent(["draft v1"])
    critic = _ScriptedAgent(["approved"])
    loop = DebateLoop(generator, critic)
    task = TaskContext(goal="write a tagline", agent_key="debate", workspace_id="ws1")

    generator_result, critic_result = await loop.run(task)

    assert generator_result.output == "draft v1"
    assert critic_result.output == "approved"


@pytest.mark.asyncio
async def test_debate_loop_revises_once_then_stops_at_max_rounds():
    generator = _ScriptedAgent(["draft v1", "draft v2"])
    critic = _ScriptedAgent(["needs more punch", "still not great"])
    loop = DebateLoop(generator, critic, max_rounds=2)
    task = TaskContext(goal="write a tagline", agent_key="debate", workspace_id="ws1")

    generator_result, critic_result = await loop.run(task)

    assert generator_result.output == "draft v2"
    assert critic_result.output == "still not great"


@pytest.mark.asyncio
async def test_debate_loop_respects_max_rounds_of_one():
    generator = _ScriptedAgent(["draft v1"])
    critic = _ScriptedAgent(["needs work"])
    loop = DebateLoop(generator, critic, max_rounds=1)
    task = TaskContext(goal="write a tagline", agent_key="debate", workspace_id="ws1")

    generator_result, critic_result = await loop.run(task)

    assert generator_result.output == "draft v1"
    assert critic_result.output == "needs work"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/agents/test_debate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.agents.debate'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/agents/debate.py
from __future__ import annotations

from agentos.core.agent import Agent
from agentos.core.models import AgentResult, AgentRunStatus, TaskContext

DEFAULT_MAX_ROUNDS = 2


class DebateLoop:
    """Generator/Critic multi-agent flow (blueprint §9.2): the generator
    produces a draft, the critic reviews it, and — if the critic's
    verdict isn't a bare "approved" — the generator revises using the
    critique as its next goal. Stops after max_rounds even if the critic
    never approves, so this can't loop forever.
    """

    def __init__(self, generator: Agent, critic: Agent, *, max_rounds: int = DEFAULT_MAX_ROUNDS) -> None:
        self._generator = generator
        self._critic = critic
        self._max_rounds = max_rounds

    async def run(self, task: TaskContext) -> tuple[AgentResult, AgentResult]:
        draft_task = task
        generator_result = await self._generator.run(draft_task)
        critic_result = await self._critic.run(
            draft_task.model_copy(update={"goal": f"Critique this: {generator_result.output}"})
        )

        rounds = 1
        while (
            rounds < self._max_rounds
            and generator_result.status == AgentRunStatus.COMPLETED
            and critic_result.status == AgentRunStatus.COMPLETED
            and (critic_result.output or "").strip().lower() != "approved"
        ):
            revision_goal = (
                f"Revise this: {generator_result.output}\nBased on this feedback: {critic_result.output}"
            )
            generator_result = await self._generator.run(draft_task.model_copy(update={"goal": revision_goal}))
            critic_result = await self._critic.run(
                draft_task.model_copy(update={"goal": f"Critique this: {generator_result.output}"})
            )
            rounds += 1

        return generator_result, critic_result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/agents/test_debate.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/agents/debate.py backend/tests/agentos/agents/test_debate.py
git commit -m "feat(agentos): add DebateLoop"
```

---

### Task 6: Integration — compose over real `AgentRuntime` instances

**Files:**
- Test: `backend/tests/agentos/agents/test_real_agent_runtime_integration.py`

**Interfaces:** None new — this task proves Tasks 1–4 (registry, supervisor, parallel — sequential/debate follow the same proven pattern and aren't re-tested here to avoid redundant coverage) work with real Phase 1 `AgentRuntime` instances, not just the hand-rolled test doubles used in Tasks 1–5's isolated unit tests.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/agents/test_real_agent_runtime_integration.py
import pytest

from agentos.agents.agent_registry import AgentRegistry
from agentos.agents.parallel import ParallelFanOut
from agentos.agents.supervisor import SupervisorAgent
from agentos.core.model_provider import ModelResponse, StubModelProvider
from agentos.core.models import AgentRunStatus, TaskContext
from agentos.core.runtime import AgentRuntime
from agentos.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_supervisor_delegates_to_a_real_agent_runtime_specialist():
    sales_provider = StubModelProvider([ModelResponse(text="Lead qualified: high intent.")])
    sales_runtime = AgentRuntime(sales_provider, ToolRegistry())

    finance_provider = StubModelProvider([ModelResponse(text="Invoice reviewed: approved.")])
    finance_runtime = AgentRuntime(finance_provider, ToolRegistry())

    registry = AgentRegistry()
    registry.register(
        "sales_specialist", sales_runtime, domain="sales", intents=["qualify lead", "sales outreach"]
    )
    registry.register("finance_specialist", finance_runtime, domain="finance", intents=["review invoice"])
    supervisor = SupervisorAgent(registry)

    task = TaskContext(goal="qualify this inbound lead", agent_key="supervisor", workspace_id="ws1")
    result = await supervisor.run(task)

    assert result.status == AgentRunStatus.COMPLETED
    assert result.output == "Lead qualified: high intent."


@pytest.mark.asyncio
async def test_parallel_fan_out_runs_multiple_real_agent_runtimes():
    market_runtime = AgentRuntime(StubModelProvider([ModelResponse(text="market: growing")]), ToolRegistry())
    competitor_runtime = AgentRuntime(
        StubModelProvider([ModelResponse(text="competitor: 3 major players")]), ToolRegistry()
    )

    fan_out = ParallelFanOut([market_runtime, competitor_runtime])
    task = TaskContext(goal="research the market", agent_key="fanout", workspace_id="ws1")

    results = await fan_out.run(task)

    assert [r.output for r in results] == ["market: growing", "competitor: 3 major players"]
    assert all(r.status == AgentRunStatus.COMPLETED for r in results)
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/agents/test_real_agent_runtime_integration.py -v`
Expected: 2 passed — this is a pure integration proof over already-implemented Tasks 1/2/4 plus Phase 1's `AgentRuntime`, so there is no separate "watch it fail first" step: if either test fails, it points at a real incompatibility between the multi-agent layer and `AgentRuntime`, not a missing-module error — stop and investigate rather than proceeding.

- [ ] **Step 3: Run the full `agentos` agents suite to confirm everything holds together**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/agents/ -v`
Expected: all passing — 3 (registry) + 5 (supervisor) + 2 (sequential) + 2 (parallel) + 3 (debate) + 2 (integration) = 17 total

- [ ] **Step 4: Commit**

```bash
git add backend/tests/agentos/agents/test_real_agent_runtime_integration.py
git commit -m "test(agentos): prove multi-agent primitives compose over real AgentRuntime"
```

---

## Verification (end of Phase 7)

1. Run the full agents suite: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/agents/ -v` — all tests pass (17 total per Task 6 Step 3).
2. Run the full `agentos` suite: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/ -v` — no regressions in Phase 0/1/3/4/5/6 tests.
3. Confirm no production wiring was introduced: `grep -rn "import agentos\|from agentos" backend --include="*.py" | grep -v "^backend/agentos/\|^backend/tests/agentos/"` returns no results.
4. Manually re-read `agentos/agents/supervisor.py` and `agentos/agents/debate.py` and confirm every path returns an `AgentResult` rather than raising — the "always return, never raise" convention is what lets these primitives be nested inside each other.

## Next steps (not part of this plan)

Per `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §4: Phase 8 (Workflow & Approval — business + agent workflow, approval gates) is next. It should get its own plan via `superpowers:writing-plans` once this one is merged and reviewed. A synthesis step for `ParallelFanOut` (blueprint §9.2's Synthesizer node, combining fan-out results into one output) is deliberately not built here — callers currently do that themselves by feeding `ParallelFanOut`'s results into a `SequentialPipeline`-style follow-up agent call; a dedicated helper for that composition can be added once a real use case needs it (YAGNI).
