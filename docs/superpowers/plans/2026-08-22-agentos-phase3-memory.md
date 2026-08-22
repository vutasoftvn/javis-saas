# AgentOS Phase 3 — Memory (Episodic/Semantic, Retrieval, Consolidation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `MemoryStore` protocol + MVP in-memory implementation, a retrieval pipeline that turns a `TaskContext` into ranked/compressed memory snippets, and an episode consolidator that summarizes a raw run into a durable episodic memory — then wire retrieval into the existing `ContextBuilder` so `AgentContext.memory_snippets` (already defined, always empty since Phase 1) gets populated for real. Per Phase 3 of the roadmap in `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §4.

**Architecture:** New subpackage `backend/agentos/memory/` implementing the blueprint's `MemoryStore` protocol (§3.6): `put`/`search`/`delete` on an MVP `InMemoryMemoryStore` (process-local, no persistence — a durable/pluggable backend such as TencentDB/pgvector is explicitly deferred, Agent Core only ever depends on the protocol). A `MemoryRetriever` implements the retrieval pipeline (query → scope filter → naive term-overlap relevance scoring → importance/recency ranking → compression) using a pure `score_relevance` function that stands in for real embedding-based semantic search until a later phase adds a vector backend. An `EpisodeConsolidator` reuses the `ModelProvider` protocol from Phase 1 to summarize a raw episode into one `EPISODIC` `MemoryItem` — the first stage of the blueprint's consolidation lifecycle (raw events → episode → summary); fact extraction into `SEMANTIC` memory is out of scope here. The only change to already-committed Phase 0/1 code is `ContextBuilder`, which gains an optional `memory_retriever` parameter and becomes `async` (it was previously synchronous).

**Tech Stack:** Python 3.11, pydantic 2.13, pytest + pytest-asyncio — same as Phase 0/1, no new dependencies.

## Global Constraints

- New code lives under `backend/agentos/memory/` and `backend/tests/agentos/memory/`. The one exception is `backend/agentos/core/context_builder.py`, which this plan deliberately modifies (Task 6) — do not touch any other file under `backend/agentos/core/` or `backend/agentos/tools/`.
- **Breaking change, called out explicitly:** `ContextBuilder.build()` changes from `def build(...)` to `async def build(...)` in Task 6. As of this plan being written, no `executor.py` or `runtime.py` exists yet in `backend/agentos/core/` (Phase 1 Tasks 10–12 are still in progress elsewhere) — if they exist by the time you execute Task 6, update their call site from `self._context_builder.build(task)` to `await self._context_builder.build(task)` as part of that same task, and re-run the Phase 0/1 end-to-end tests before committing.
- `MemoryItem.importance` is a `float` constrained to `[0.0, 1.0]` via pydantic `Field(ge=0.0, le=1.0)` — reject out-of-range values at construction, don't clamp silently.
- `InMemoryMemoryStore` is explicitly process-local and non-durable — do not add file/DB persistence in this phase; that's a later phase per the spec (§3.6, §3.12).
- `score_relevance` (naive term-overlap) is an explicitly-flagged MVP placeholder for real semantic/embedding retrieval — do not attempt to make it "smarter" (stemming, TF-IDF, etc.) in this plan; the point is proving the retrieval pipeline's shape, not the ranking quality.
- Every async test needs `@pytest.mark.asyncio` (`backend/pytest.ini` has `asyncio_mode = strict`).
- Run tests via: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/memory/<file> -v` (and `tests/agentos/test_context_builder.py` for Task 6).
- Source spec: `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §3.6 (Memory & Knowledge), §4 (Phase 3 scope).

---

## File Structure

```text
backend/agentos/memory/
├── __init__.py
├── models.py           # MemoryKind, MemoryItem
├── store.py              # MemoryStore protocol, MemoryNotFoundError, InMemoryMemoryStore
├── retrieval.py            # MemoryQuery, score_relevance
├── retriever.py              # MemoryRetriever (pipeline)
└── consolidation.py            # EpisodeConsolidator

backend/tests/agentos/memory/
├── __init__.py
├── test_models.py
├── test_store.py
├── test_retrieval.py
├── test_retriever.py
└── test_consolidation.py

backend/agentos/core/context_builder.py   # MODIFIED (Task 6)
backend/tests/agentos/test_context_builder.py   # MODIFIED (Task 6)
```

---

### Task 1: `MemoryKind` + `MemoryItem` model

**Files:**
- Create: `backend/agentos/memory/__init__.py`
- Create: `backend/agentos/memory/models.py`
- Create: `backend/tests/agentos/memory/__init__.py`
- Test: `backend/tests/agentos/memory/test_models.py`

**Interfaces:**
- Produces: `MemoryKind` (str enum: `WORKING`, `EPISODIC`, `SEMANTIC`, `PROCEDURAL`, `ORGANIZATIONAL`); `MemoryItem(id: str, workspace_id: str, agent_key: str, kind: MemoryKind, content: str, importance: float = 0.5, tags: list[str], created_at: datetime, metadata: dict)`.

- [x] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/memory/test_models.py
import pytest
from pydantic import ValidationError

from agentos.memory.models import MemoryItem, MemoryKind


def test_memory_item_defaults():
    item = MemoryItem(workspace_id="ws1", agent_key="a1", kind=MemoryKind.EPISODIC, content="did X")
    assert item.importance == 0.5
    assert item.tags == []
    assert item.kind == MemoryKind.EPISODIC


def test_memory_item_rejects_importance_above_one():
    with pytest.raises(ValidationError):
        MemoryItem(workspace_id="ws1", agent_key="a1", kind=MemoryKind.EPISODIC, content="x", importance=1.5)


def test_memory_item_rejects_importance_below_zero():
    with pytest.raises(ValidationError):
        MemoryItem(workspace_id="ws1", agent_key="a1", kind=MemoryKind.EPISODIC, content="x", importance=-0.1)
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/memory/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.memory'`

- [x] **Step 3: Create package scaffolding and the implementation**

```python
# backend/agentos/memory/__init__.py
```

```python
# backend/tests/agentos/memory/__init__.py
```

```python
# backend/agentos/memory/models.py
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class MemoryKind(str, enum.Enum):
    WORKING = "WORKING"
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"
    PROCEDURAL = "PROCEDURAL"
    ORGANIZATIONAL = "ORGANIZATIONAL"


class MemoryItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: str
    agent_key: str
    kind: MemoryKind
    content: str
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/memory/test_models.py -v`
Expected: 3 passed

- [x] **Step 5: Commit**

```bash
git add backend/agentos/memory/__init__.py backend/agentos/memory/models.py backend/tests/agentos/memory/__init__.py backend/tests/agentos/memory/test_models.py
git commit -m "feat(agentos): add MemoryKind and MemoryItem model"
```

---

### Task 2: `MemoryStore` protocol + `InMemoryMemoryStore`

**Files:**
- Create: `backend/agentos/memory/store.py`
- Test: `backend/tests/agentos/memory/test_store.py`

**Interfaces:**
- Consumes: `MemoryItem`, `MemoryKind` from `agentos.memory.models` (Task 1).
- Produces: `MemoryNotFoundError(item_id: str)`; `MemoryStore` (runtime-checkable `Protocol` with `async def put(item: MemoryItem) -> None`, `async def search(*, workspace_id: str, agent_key: str | None = None, kind: MemoryKind | None = None, limit: int = 20) -> list[MemoryItem]`, `async def delete(item_id: str) -> None`); `InMemoryMemoryStore` implementing it.

- [x] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/memory/test_store.py
import pytest

from agentos.memory.models import MemoryItem, MemoryKind
from agentos.memory.store import InMemoryMemoryStore, MemoryNotFoundError, MemoryStore


def test_in_memory_store_satisfies_protocol():
    assert isinstance(InMemoryMemoryStore(), MemoryStore)


@pytest.mark.asyncio
async def test_put_then_search_returns_item_scoped_to_workspace():
    store = InMemoryMemoryStore()
    item = MemoryItem(workspace_id="ws1", agent_key="a1", kind=MemoryKind.EPISODIC, content="did X")
    await store.put(item)

    results = await store.search(workspace_id="ws1")

    assert results == [item]


@pytest.mark.asyncio
async def test_search_excludes_other_workspaces():
    store = InMemoryMemoryStore()
    await store.put(MemoryItem(workspace_id="ws1", agent_key="a1", kind=MemoryKind.EPISODIC, content="x"))
    await store.put(MemoryItem(workspace_id="ws2", agent_key="a1", kind=MemoryKind.EPISODIC, content="y"))

    results = await store.search(workspace_id="ws1")

    assert len(results) == 1
    assert results[0].workspace_id == "ws1"


@pytest.mark.asyncio
async def test_search_filters_by_kind():
    store = InMemoryMemoryStore()
    await store.put(MemoryItem(workspace_id="ws1", agent_key="a1", kind=MemoryKind.EPISODIC, content="e"))
    await store.put(MemoryItem(workspace_id="ws1", agent_key="a1", kind=MemoryKind.SEMANTIC, content="s"))

    results = await store.search(workspace_id="ws1", kind=MemoryKind.SEMANTIC)

    assert len(results) == 1
    assert results[0].kind == MemoryKind.SEMANTIC


@pytest.mark.asyncio
async def test_delete_missing_item_raises():
    store = InMemoryMemoryStore()
    with pytest.raises(MemoryNotFoundError):
        await store.delete("missing")


@pytest.mark.asyncio
async def test_delete_removes_item():
    store = InMemoryMemoryStore()
    item = MemoryItem(workspace_id="ws1", agent_key="a1", kind=MemoryKind.EPISODIC, content="x")
    await store.put(item)
    await store.delete(item.id)

    results = await store.search(workspace_id="ws1")

    assert results == []
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/memory/test_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.memory.store'`

- [x] **Step 3: Write the implementation**

```python
# backend/agentos/memory/store.py
from __future__ import annotations

from typing import Protocol, runtime_checkable

from agentos.memory.models import MemoryItem, MemoryKind


class MemoryNotFoundError(Exception):
    def __init__(self, item_id: str) -> None:
        super().__init__(f"Memory item not found: {item_id}")
        self.item_id = item_id


@runtime_checkable
class MemoryStore(Protocol):
    async def put(self, item: MemoryItem) -> None:
        ...

    async def search(
        self,
        *,
        workspace_id: str,
        agent_key: str | None = None,
        kind: MemoryKind | None = None,
        limit: int = 20,
    ) -> list[MemoryItem]:
        ...

    async def delete(self, item_id: str) -> None:
        ...


class InMemoryMemoryStore:
    """MVP store: process-local dict, no persistence. A durable/pluggable
    backend (TencentDB/pgvector/Qdrant/Redis, per blueprint §3.6) is a later
    phase — Agent Core only ever depends on the MemoryStore protocol.
    """

    def __init__(self) -> None:
        self._items: dict[str, MemoryItem] = {}

    async def put(self, item: MemoryItem) -> None:
        self._items[item.id] = item

    async def search(
        self,
        *,
        workspace_id: str,
        agent_key: str | None = None,
        kind: MemoryKind | None = None,
        limit: int = 20,
    ) -> list[MemoryItem]:
        results = [
            item
            for item in self._items.values()
            if item.workspace_id == workspace_id
            and (agent_key is None or item.agent_key == agent_key)
            and (kind is None or item.kind == kind)
        ]
        results.sort(key=lambda item: item.created_at, reverse=True)
        return results[:limit]

    async def delete(self, item_id: str) -> None:
        try:
            del self._items[item_id]
        except KeyError:
            raise MemoryNotFoundError(item_id) from None
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/memory/test_store.py -v`
Expected: 6 passed

- [x] **Step 5: Commit**

```bash
git add backend/agentos/memory/store.py backend/tests/agentos/memory/test_store.py
git commit -m "feat(agentos): add MemoryStore protocol and InMemoryMemoryStore"
```

---

### Task 3: `MemoryQuery` + naive relevance scoring

**Files:**
- Create: `backend/agentos/memory/retrieval.py`
- Test: `backend/tests/agentos/memory/test_retrieval.py`

**Interfaces:**
- Produces: `MemoryQuery(workspace_id: str, agent_key: str, text: str, limit: int = 20)`; `score_relevance(query_text: str, content: str) -> float` (term-overlap ratio in `[0, 1]`).

- [x] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/memory/test_retrieval.py
import pytest

from agentos.memory.retrieval import MemoryQuery, score_relevance


def test_score_relevance_full_overlap_is_one():
    assert score_relevance("hit target revenue", "hit target revenue") == 1.0


def test_score_relevance_partial_overlap():
    assert score_relevance("hit target revenue", "hit target churn") == pytest.approx(2 / 3)


def test_score_relevance_no_overlap_is_zero():
    assert score_relevance("hit target revenue", "completely unrelated text") == 0.0


def test_score_relevance_empty_content_is_zero():
    assert score_relevance("hit target revenue", "") == 0.0


def test_score_relevance_is_case_insensitive():
    assert score_relevance("Hit Target", "hit target") == 1.0


def test_memory_query_defaults_limit():
    query = MemoryQuery(workspace_id="ws1", agent_key="a1", text="hi")
    assert query.limit == 20
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/memory/test_retrieval.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.memory.retrieval'`

- [x] **Step 3: Write the implementation**

```python
# backend/agentos/memory/retrieval.py
from __future__ import annotations

import re

from pydantic import BaseModel, Field

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class MemoryQuery(BaseModel):
    workspace_id: str
    agent_key: str
    text: str
    limit: int = Field(default=20, gt=0)


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_PATTERN.findall(text.lower()))


def score_relevance(query_text: str, content: str) -> float:
    """Naive term-overlap relevance score in [0, 1]. A placeholder for real
    embedding-based semantic retrieval (blueprint §3.6) — good enough to
    prove the retrieval pipeline shape without adding a vector DB dependency
    in this phase.
    """
    query_tokens = _tokenize(query_text)
    content_tokens = _tokenize(content)
    if not query_tokens or not content_tokens:
        return 0.0
    overlap = query_tokens & content_tokens
    return len(overlap) / len(query_tokens)
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/memory/test_retrieval.py -v`
Expected: 6 passed

- [x] **Step 5: Commit**

```bash
git add backend/agentos/memory/retrieval.py backend/tests/agentos/memory/test_retrieval.py
git commit -m "feat(agentos): add MemoryQuery and naive relevance scoring"
```

---

### Task 4: `MemoryRetriever` pipeline

**Files:**
- Create: `backend/agentos/memory/retriever.py`
- Test: `backend/tests/agentos/memory/test_retriever.py`

**Interfaces:**
- Consumes: `TaskContext` from `agentos.core.models` (Phase 1); `MemoryItem` (Task 1); `MemoryQuery`/`score_relevance` (Task 3); `MemoryStore` (Task 2).
- Produces: `DEFAULT_MAX_SNIPPETS = 5`; `DEFAULT_MAX_CHARS_PER_SNIPPET = 280`; `MemoryRetriever(store: MemoryStore, max_snippets: int = DEFAULT_MAX_SNIPPETS, max_chars_per_snippet: int = DEFAULT_MAX_CHARS_PER_SNIPPET)` with `async def retrieve(task: TaskContext) -> list[str]`.

- [x] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/memory/test_retriever.py
import pytest

from agentos.core.models import TaskContext
from agentos.memory.models import MemoryItem, MemoryKind
from agentos.memory.retriever import MemoryRetriever
from agentos.memory.store import InMemoryMemoryStore


@pytest.mark.asyncio
async def test_retrieve_returns_only_relevant_snippets():
    store = InMemoryMemoryStore()
    await store.put(
        MemoryItem(
            workspace_id="ws1", agent_key="a1", kind=MemoryKind.EPISODIC,
            content="closed deal with acme corp", importance=0.9,
        )
    )
    await store.put(
        MemoryItem(
            workspace_id="ws1", agent_key="a1", kind=MemoryKind.EPISODIC,
            content="unrelated note about lunch", importance=0.9,
        )
    )
    retriever = MemoryRetriever(store)
    task = TaskContext(goal="follow up on acme corp deal", agent_key="a1", workspace_id="ws1")

    snippets = await retriever.retrieve(task)

    assert snippets == ["closed deal with acme corp"]


@pytest.mark.asyncio
async def test_retrieve_returns_empty_list_when_nothing_relevant():
    store = InMemoryMemoryStore()
    await store.put(MemoryItem(workspace_id="ws1", agent_key="a1", kind=MemoryKind.EPISODIC, content="unrelated"))
    retriever = MemoryRetriever(store)
    task = TaskContext(goal="follow up on acme corp deal", agent_key="a1", workspace_id="ws1")

    snippets = await retriever.retrieve(task)

    assert snippets == []


@pytest.mark.asyncio
async def test_retrieve_compresses_long_content():
    store = InMemoryMemoryStore()
    long_content = "acme corp deal " + ("details " * 100)
    await store.put(MemoryItem(workspace_id="ws1", agent_key="a1", kind=MemoryKind.EPISODIC, content=long_content))
    retriever = MemoryRetriever(store, max_chars_per_snippet=50)
    task = TaskContext(goal="acme corp deal", agent_key="a1", workspace_id="ws1")

    snippets = await retriever.retrieve(task)

    assert len(snippets) == 1
    assert len(snippets[0]) == 50
    assert snippets[0].endswith("…")


@pytest.mark.asyncio
async def test_retrieve_respects_max_snippets():
    store = InMemoryMemoryStore()
    for i in range(10):
        await store.put(
            MemoryItem(workspace_id="ws1", agent_key="a1", kind=MemoryKind.EPISODIC, content=f"acme corp deal number {i}")
        )
    retriever = MemoryRetriever(store, max_snippets=3)
    task = TaskContext(goal="acme corp deal", agent_key="a1", workspace_id="ws1")

    snippets = await retriever.retrieve(task)

    assert len(snippets) == 3
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/memory/test_retriever.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.memory.retriever'`

- [x] **Step 3: Write the implementation**

```python
# backend/agentos/memory/retriever.py
from __future__ import annotations

from agentos.core.models import TaskContext
from agentos.memory.models import MemoryItem
from agentos.memory.retrieval import MemoryQuery, score_relevance
from agentos.memory.store import MemoryStore

DEFAULT_MAX_SNIPPETS = 5
DEFAULT_MAX_CHARS_PER_SNIPPET = 280


class MemoryRetriever:
    """Retrieval pipeline: task -> query -> scope filter -> naive semantic
    scoring -> importance/recency ranking -> compression -> snippets.
    Policy filtering (blueprint §3.6/§13) is a pass-through hook here —
    Governance integration is a later phase.
    """

    def __init__(
        self,
        store: MemoryStore,
        max_snippets: int = DEFAULT_MAX_SNIPPETS,
        max_chars_per_snippet: int = DEFAULT_MAX_CHARS_PER_SNIPPET,
    ) -> None:
        self._store = store
        self._max_snippets = max_snippets
        self._max_chars_per_snippet = max_chars_per_snippet

    async def retrieve(self, task: TaskContext) -> list[str]:
        query = MemoryQuery(workspace_id=task.workspace_id, agent_key=task.agent_key, text=task.goal)
        candidates = await self._store.search(
            workspace_id=query.workspace_id,
            agent_key=query.agent_key,
            limit=max(query.limit, self._max_snippets * 4),
        )
        ranked = sorted(candidates, key=lambda item: self._rank_key(query, item), reverse=True)
        relevant = [item for item in ranked if score_relevance(query.text, item.content) > 0]
        top = relevant[: self._max_snippets]
        return [self._compress(item.content) for item in top]

    def _rank_key(self, query: MemoryQuery, item: MemoryItem) -> float:
        relevance = score_relevance(query.text, item.content)
        return relevance * 0.7 + item.importance * 0.3

    def _compress(self, content: str) -> str:
        if len(content) <= self._max_chars_per_snippet:
            return content
        return content[: self._max_chars_per_snippet - 1].rstrip() + "…"
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/memory/test_retriever.py -v`
Expected: 4 passed

- [x] **Step 5: Commit**

```bash
git add backend/agentos/memory/retriever.py backend/tests/agentos/memory/test_retriever.py
git commit -m "feat(agentos): add MemoryRetriever pipeline"
```

---

### Task 5: `EpisodeConsolidator`

**Files:**
- Create: `backend/agentos/memory/consolidation.py`
- Test: `backend/tests/agentos/memory/test_consolidation.py`

**Interfaces:**
- Consumes: `ModelProvider`/`StubModelProvider`/`ModelResponse` from `agentos.core.model_provider` (Phase 1); `TaskContext` (Phase 1); `MemoryItem`/`MemoryKind` (Task 1); `MemoryStore` (Task 2).
- Produces: `CONSOLIDATION_SYSTEM_PROMPT: str`; `EpisodeConsolidator(model_provider: ModelProvider, store: MemoryStore)` with `async def consolidate(task: TaskContext, raw_episode_text: str) -> MemoryItem`.

- [x] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/memory/test_consolidation.py
import pytest

from agentos.core.model_provider import ModelResponse, StubModelProvider
from agentos.core.models import TaskContext
from agentos.memory.consolidation import EpisodeConsolidator
from agentos.memory.models import MemoryKind
from agentos.memory.store import InMemoryMemoryStore


@pytest.mark.asyncio
async def test_consolidate_stores_summarized_episode():
    provider = StubModelProvider([ModelResponse(text="Closed the Acme deal after three follow-ups.")])
    store = InMemoryMemoryStore()
    consolidator = EpisodeConsolidator(provider, store)
    task = TaskContext(goal="close acme deal", agent_key="sales_agent", workspace_id="ws1")

    item = await consolidator.consolidate(task, raw_episode_text="tool_call: crm.update ... tool_call: email.send ...")

    assert item.content == "Closed the Acme deal after three follow-ups."
    assert item.kind == MemoryKind.EPISODIC
    assert item.tags == ["consolidated"]
    stored = await store.search(workspace_id="ws1")
    assert stored == [item]


@pytest.mark.asyncio
async def test_consolidate_falls_back_to_raw_text_when_model_returns_no_text():
    provider = StubModelProvider([ModelResponse(text=None)])
    store = InMemoryMemoryStore()
    consolidator = EpisodeConsolidator(provider, store)
    task = TaskContext(goal="close acme deal", agent_key="sales_agent", workspace_id="ws1")

    item = await consolidator.consolidate(task, raw_episode_text="raw trace text")

    assert item.content == "raw trace text"
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/memory/test_consolidation.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.memory.consolidation'`

- [x] **Step 3: Write the implementation**

```python
# backend/agentos/memory/consolidation.py
from __future__ import annotations

from agentos.core.model_provider import ModelProvider
from agentos.core.models import TaskContext
from agentos.memory.models import MemoryItem, MemoryKind
from agentos.memory.store import MemoryStore

CONSOLIDATION_SYSTEM_PROMPT = (
    "Summarize the following agent run into one or two sentences of durable "
    "episodic memory. Be factual, do not invent details."
)


class EpisodeConsolidator:
    """Raw run trace -> summary -> episodic MemoryItem (blueprint §3.6
    consolidation lifecycle, first stage only: raw events -> episode ->
    summary). Fact extraction into SEMANTIC memory is a later phase.
    """

    def __init__(self, model_provider: ModelProvider, store: MemoryStore) -> None:
        self._model_provider = model_provider
        self._store = store

    async def consolidate(self, task: TaskContext, raw_episode_text: str) -> MemoryItem:
        response = await self._model_provider.generate(
            system_prompt=CONSOLIDATION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": raw_episode_text}],
        )
        summary = response.text or raw_episode_text
        item = MemoryItem(
            workspace_id=task.workspace_id,
            agent_key=task.agent_key,
            kind=MemoryKind.EPISODIC,
            content=summary,
            tags=["consolidated"],
        )
        await self._store.put(item)
        return item
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/memory/test_consolidation.py -v`
Expected: 2 passed

- [x] **Step 5: Commit**

```bash
git add backend/agentos/memory/consolidation.py backend/tests/agentos/memory/test_consolidation.py
git commit -m "feat(agentos): add EpisodeConsolidator"
```

---

### Task 6: Wire `MemoryRetriever` into `ContextBuilder`

**Files:**
- Modify: `backend/agentos/core/context_builder.py`
- Modify: `backend/tests/agentos/test_context_builder.py`

**Interfaces:**
- Consumes: `MemoryRetriever` (Task 4).
- Produces (changed): `ContextBuilder.__init__(tool_registry, system_policy=DEFAULT_SYSTEM_POLICY, memory_retriever: MemoryRetriever | None = None)`; `ContextBuilder.build` is now `async def build(task: TaskContext) -> AgentContext` (was synchronous).

- [x] **Step 1: Write the failing tests (replace the existing test file's content)**

```python
# backend/tests/agentos/test_context_builder.py
import pytest

from agentos.core.context_builder import ContextBuilder, DEFAULT_SYSTEM_POLICY
from agentos.core.models import TaskContext
from agentos.memory.models import MemoryItem, MemoryKind
from agentos.memory.retriever import MemoryRetriever
from agentos.memory.store import InMemoryMemoryStore
from agentos.tools.registry import ToolRegistry, ToolSpec


async def _noop(arguments: dict) -> dict:
    return {}


@pytest.mark.asyncio
async def test_build_includes_registered_tool_names_and_default_policy():
    registry = ToolRegistry()
    registry.register(ToolSpec(name="echo", description="d", handler=_noop))
    builder = ContextBuilder(registry)
    task = TaskContext(goal="say hi", agent_key="fake", workspace_id="ws1")

    context = await builder.build(task)

    assert context.task == task
    assert context.tool_names == ["echo"]
    assert context.system_policy == DEFAULT_SYSTEM_POLICY


@pytest.mark.asyncio
async def test_build_without_memory_retriever_returns_empty_snippets():
    registry = ToolRegistry()
    builder = ContextBuilder(registry)
    task = TaskContext(goal="say hi", agent_key="fake", workspace_id="ws1")

    context = await builder.build(task)

    assert context.memory_snippets == []


@pytest.mark.asyncio
async def test_build_populates_memory_snippets_from_retriever():
    registry = ToolRegistry()
    store = InMemoryMemoryStore()
    await store.put(
        MemoryItem(workspace_id="ws1", agent_key="fake", kind=MemoryKind.EPISODIC, content="closed acme corp deal")
    )
    retriever = MemoryRetriever(store)
    builder = ContextBuilder(registry, memory_retriever=retriever)
    task = TaskContext(goal="follow up acme corp deal", agent_key="fake", workspace_id="ws1")

    context = await builder.build(task)

    assert context.memory_snippets == ["closed acme corp deal"]
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_context_builder.py -v`
Expected: FAIL — `TypeError: object AgentContext can't be used in 'await' expression` (current `build` is synchronous, so `await builder.build(task)` fails) and `ContextBuilder() got an unexpected keyword argument 'memory_retriever'`

- [x] **Step 3: Modify the implementation**

```python
# backend/agentos/core/context_builder.py
from __future__ import annotations

from agentos.core.context import AgentContext
from agentos.core.models import TaskContext
from agentos.memory.retriever import MemoryRetriever
from agentos.tools.registry import ToolRegistry

DEFAULT_SYSTEM_POLICY = (
    "You are an AI Agent OS agent. Use only the tools listed. "
    "Never fabricate tool results."
)


class ContextBuilder:
    def __init__(
        self,
        tool_registry: ToolRegistry,
        system_policy: str = DEFAULT_SYSTEM_POLICY,
        memory_retriever: MemoryRetriever | None = None,
    ) -> None:
        self._tool_registry = tool_registry
        self._system_policy = system_policy
        self._memory_retriever = memory_retriever

    async def build(self, task: TaskContext) -> AgentContext:
        memory_snippets = await self._memory_retriever.retrieve(task) if self._memory_retriever else []
        return AgentContext(
            task=task,
            system_policy=self._system_policy,
            tool_names=self._tool_registry.names(),
            memory_snippets=memory_snippets,
        )
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_context_builder.py -v`
Expected: 3 passed

- [x] **Step 5: Check for and fix any other caller of the old synchronous `build()`**

Run: `grep -rn "context_builder.build\|_context_builder.build" backend/agentos backend/tests/agentos`
Expected: only matches inside `context_builder.py` itself and `test_context_builder.py`. If `executor.py`/`runtime.py` exist by now and call `self._context_builder.build(task)` synchronously (see Global Constraints note above), change that call site to `await self._context_builder.build(task)` and re-run `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/ -v` before committing.

- [x] **Step 6: Run the full `agentos` suite to confirm no regressions**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/ -v`
Expected: all passing (Phase 0/1 tests + Phase 3 `memory/` tests: 3 + 6 + 6 + 4 + 2 = 21 new memory tests, plus 3 updated `test_context_builder.py` tests, plus whatever Phase 0/1 has already committed)

- [x] **Step 7: Commit**

```bash
git add backend/agentos/core/context_builder.py backend/tests/agentos/test_context_builder.py
git commit -m "feat(agentos): wire MemoryRetriever into ContextBuilder"
```

---

## Verification (end of Phase 3)

1. Run the full `agentos` suite: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/ -v` — all tests pass.
2. Run the full existing backend suite to confirm zero impact outside `agentos/`: `cd backend && PYTHONPATH=. ./.venv/bin/pytest -q` — no existing test outside `backend/agentos/`/`backend/tests/agentos/` newly fails.
3. Confirm the memory subsystem still isn't wired into any production call site: `grep -rn "import agentos\|from agentos" backend --include="*.py" | grep -v "^backend/agentos/\|^backend/tests/agentos/"` returns no results.
4. Re-read `backend/agentos/core/context_builder.py` and confirm the `memory_retriever` parameter defaults to `None` and behaves as a true no-op when omitted (Task 6's second test proves this).

## Next steps (not part of this plan)

Per `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §4: Phase 4 (Skill Layer: manifest, registry, router, loader, permissions) is next. It should get its own plan via `superpowers:writing-plans` once this one is merged and reviewed. Wiring `AgentRuntime` to call `EpisodeConsolidator.consolidate()` after a completed run (so future retrievals actually see past episodes) is also deferred — flag it as a follow-up task once Phase 1's `runtime.py` lands, rather than reaching into that file speculatively here.
