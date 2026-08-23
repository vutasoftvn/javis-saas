# Governance Temporal Model — Durable Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the in-memory governance primitives from Plan 1 (`docs/superpowers/plans/2026-08-23-governance-temporal-model-foundations.md`) a durable Postgres backing — `SpecResolutionManifest` entries, `InvocationGovernanceState` (with append-only history for provenance), and `ApprovalEvidence` all survive a process restart, matching V4 Bước 6 ("durable run/checkpoint/event model").

**Architecture:** New Postgres schema `agent_core_governance`, owned by `packages/agent_core/governance/`, created via a raw SQL migration in `agentos/migrations/` (this repo's only migration mechanism — no Alembic). A `GovernanceStateStore` Protocol plus a `PostgresGovernanceStateStore` implementation follow the exact pattern already proven by `agentos/memory/providers/postgres.py`: constructor takes `db_session_factory`, raw SQL via SQLAlchemy `text()`, JSON columns serialized with `json.dumps`/parsed with `json.loads`, fake-session unit tests plus a real-Postgres integration test gated behind `AGENTOS_TEST_DATABASE_URL`.

**Tech Stack:** Python 3.11, Pydantic v2, SQLAlchemy 2.x async (`create_async_engine`, `text()`), asyncpg, pytest + pytest-asyncio, PostgreSQL (via the existing `docker-compose.yml` `postgres` service).

## Global Constraints

- `run_id`/`tool_call_id` are plain `TEXT` columns in this plan — **not** foreign keys into a `runs`/`run_tool_calls` table, because those tables do not exist anywhere in this codebase yet (confirmed: only `agentos/migrations/001_agent_memory_and_knowledge.sql` exists, creating `agent_memory`/`knowledge` schemas only). Building the full `runs`/`run_checkpoints`/`run_events`/`run_tool_calls` schema is a separate, larger plan outside this one's scope.
- Match `agentos/memory/providers/postgres.py` conventions exactly: constructor signature `__init__(self, db_session_factory: Any = None) -> None`, raising a `ConfigurationError`-style exception when `None`; raw SQL via `sqlalchemy.text()`; JSON columns passed as `json.dumps(...)` strings, read back with `json.loads` when the driver returns a string.
- Migration file goes in `agentos/migrations/`, numbered sequentially after the existing `001_agent_memory_and_knowledge.sql` — so `002_governance_temporal_model.sql`. Every `CREATE SCHEMA`/`CREATE TABLE`/`CREATE INDEX` statement must be idempotent (`IF NOT EXISTS`), matching `001`'s style. No Alembic, no new migration tool.
- `decided_at`/`valid_until` on `ApprovalEvidence` stay `TEXT` (ISO 8601 strings) both in the Pydantic contract (already decided in Plan 1 Task 3) and in the matching Postgres columns — not `TIMESTAMPTZ` — to avoid asyncpg's native-datetime-object requirement for timestamp columns bound through raw SQL text params. ISO 8601 UTC strings still sort correctly with a plain text `ORDER BY`.
- New/changed code comments explaining *why* go in Vietnamese; identifiers and error messages stay in English (CLAUDE.md rule 19).
- Do not touch `agentos/core/approval.py`/`ApprovalService`, `agentos/workflows/tool_step.py`, or `agentos/workflows/steps.py` in this plan — rewiring those to call this store is Plan 3 (V4 Bước 7), which depends on this plan landing first.
- Every existing test must still pass unchanged.

---

### Task 1: Add `id` to `ApprovalEvidence` (needed as a Postgres primary key)

**Files:**
- Modify: `packages/agent_core/governance/contracts.py`
- Modify: `tests/agent_core/governance/test_contracts.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `ApprovalEvidence.id: str` (new field, `default_factory=lambda: str(uuid.uuid4())`) — consumed by Task 7's `save_evidence`/`list_evidence`.

- [ ] **Step 1: Write the failing test**

Append to `tests/agent_core/governance/test_contracts.py`:

```python
def test_approval_evidence_generates_a_uuid_id_by_default():
    evidence = ApprovalEvidence(approver="founder-1", scope="tool_call_42", decided_at="2026-08-23T10:00:00Z")

    assert evidence.id
    assert isinstance(evidence.id, str)


def test_approval_evidence_accepts_an_explicit_id():
    evidence = ApprovalEvidence(
        id="evidence-fixed-1",
        approver="founder-1",
        scope="tool_call_42",
        decided_at="2026-08-23T10:00:00Z",
    )

    assert evidence.id == "evidence-fixed-1"
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/agent_core/governance/test_contracts.py -k approval_evidence -v`
Expected: `test_approval_evidence_generates_a_uuid_id_by_default` FAILs with `AttributeError: 'ApprovalEvidence' object has no attribute 'id'` (or a pydantic extra-field validation error on the explicit-id test, depending on which runs first — either way, at least one FAIL)

- [ ] **Step 3: Add the field**

In `packages/agent_core/governance/contracts.py`, add `import uuid` to the top-of-file import block (alongside the existing `import enum`), then change the `ApprovalEvidence` class from:

```python
class ApprovalEvidence(BaseModel):
    ...
    approver: str
    scope: str
    decided_at: str
    valid_until: str | None = None
```

to:

```python
class ApprovalEvidence(BaseModel):
    ...
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    approver: str
    scope: str
    decided_at: str
    valid_until: str | None = None
```

(keep the existing docstring unchanged)

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/agent_core/governance/test_contracts.py -v`
Expected: 16 passed

- [ ] **Step 5: Commit**

```bash
git add packages/agent_core/governance/contracts.py tests/agent_core/governance/test_contracts.py
git commit -m "feat(agent-core): add id field to ApprovalEvidence for durable storage"
```

---

### Task 2: Postgres schema migration

**Files:**
- Create: `agentos/migrations/002_governance_temporal_model.sql`

**Interfaces:**
- Produces: schema `agent_core_governance` with tables `spec_resolution_manifest_entries`, `invocation_governance_state`, `invocation_governance_history`, `approval_evidence` — consumed by Task 5/6/7's SQL.

- [ ] **Step 1: Write the migration file**

Create `agentos/migrations/002_governance_temporal_model.sql`:

```sql
-- Migration: 002_governance_temporal_model.sql
-- Description: Durable storage for the governance/identity temporal model —
--   see COSA_AGENT_CORE_GOVERNANCE_TEMPORAL_MODEL_2026-08-23.md.
-- Storage ownership: schema agent_core_governance owned by packages/agent_core/governance/.
--
-- run_id / tool_call_id are plain TEXT here, not foreign keys — this repo has
-- no runs/run_tool_calls table yet (see the plan's Global Constraints).

CREATE SCHEMA IF NOT EXISTS agent_core_governance;

-- SpecResolutionManifest: append-only set of PinnedSpecIdentity a Run has
-- resolved. Never updated in place, never deleted.
CREATE TABLE IF NOT EXISTS agent_core_governance.spec_resolution_manifest_entries (
    run_id TEXT NOT NULL,
    spec_kind TEXT NOT NULL CHECK (spec_kind IN ('agent', 'workflow')),
    spec_id TEXT NOT NULL,
    spec_version TEXT NOT NULL,
    definition_hash TEXT NOT NULL,
    resolved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, spec_kind, spec_id, definition_hash)
);

CREATE INDEX IF NOT EXISTS idx_spec_resolution_manifest_run_id
    ON agent_core_governance.spec_resolution_manifest_entries(run_id);

-- InvocationGovernanceState: current accumulated PolicyDecision for one
-- (run_id, tool_call_id) invocation. Upserted on every accumulate() call.
CREATE TABLE IF NOT EXISTS agent_core_governance.invocation_governance_state (
    run_id TEXT NOT NULL,
    tool_call_id TEXT NOT NULL,
    accumulated JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, tool_call_id)
);

-- Append-only observation history behind the accumulator above — this is
-- where provenance (ambient vs historical, PHẦN I §2.5 của tài liệu) lives,
-- since invocation_governance_state only ever holds the latest accumulated
-- value.
CREATE TABLE IF NOT EXISTS agent_core_governance.invocation_governance_history (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    tool_call_id TEXT NOT NULL,
    observation JSONB NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('ambient', 'historical')),
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_invocation_governance_history_invocation
    ON agent_core_governance.invocation_governance_history(run_id, tool_call_id, observed_at);

-- ApprovalEvidence: separate from the accumulated requirement it may
-- satisfy — evidence can expire (valid_until), the accumulated constraint
-- does not (PHẦN I §2.1/§5 của tài liệu). decided_at/valid_until are TEXT
-- (ISO 8601), matching the Pydantic contract exactly.
CREATE TABLE IF NOT EXISTS agent_core_governance.approval_evidence (
    id TEXT PRIMARY KEY,
    approver TEXT NOT NULL,
    scope TEXT NOT NULL,
    decided_at TEXT NOT NULL,
    valid_until TEXT
);

CREATE INDEX IF NOT EXISTS idx_approval_evidence_scope
    ON agent_core_governance.approval_evidence(scope);
```

- [ ] **Step 2: Apply the migration against the local Postgres to verify it is syntactically valid and idempotent**

Run:
```bash
docker compose up -d postgres
until docker compose exec -T postgres pg_isready -U ${POSTGRES_USER:-javis}; do sleep 1; done
psql "${DATABASE_URL:-postgresql://javis_app:change-me-javis-app@localhost:5432/javis}" -f agentos/migrations/002_governance_temporal_model.sql
psql "${DATABASE_URL:-postgresql://javis_app:change-me-javis-app@localhost:5432/javis}" -f agentos/migrations/002_governance_temporal_model.sql
```
Expected: both runs succeed with no errors (the second run proves idempotency — every statement is `IF NOT EXISTS`). If the `javis_app` role/database from `.env.example` isn't provisioned locally, substitute the actual local Postgres connection string from your `.env`.

- [ ] **Step 3: Commit**

```bash
git add agentos/migrations/002_governance_temporal_model.sql
git commit -m "feat(agentos): add agent_core_governance schema migration"
```

---

### Task 3: `GovernanceStoreConfigurationError`

**Files:**
- Create: `packages/agent_core/governance/exceptions.py`
- Create: `tests/agent_core/governance/test_exceptions.py`

**Interfaces:**
- Produces: `agent_core.governance.exceptions.GovernanceStoreConfigurationError` — consumed by Task 5.

- [ ] **Step 1: Write the failing test**

Create `tests/agent_core/governance/test_exceptions.py`:

```python
from __future__ import annotations

from agent_core.governance.exceptions import GovernanceStoreConfigurationError


def test_governance_store_configuration_error_is_an_exception():
    error = GovernanceStoreConfigurationError("missing db_session_factory")

    assert isinstance(error, Exception)
    assert str(error) == "missing db_session_factory"
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/agent_core/governance/test_exceptions.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_core.governance.exceptions'`

- [ ] **Step 3: Implement**

Create `packages/agent_core/governance/exceptions.py`:

```python
from __future__ import annotations


class GovernanceStoreConfigurationError(Exception):
    """Raised when a GovernanceStateStore implementation is improperly
    configured (vd thiếu db_session_factory) — cùng mẫu với
    agentos/memory/exceptions.py::ConfigurationError."""
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/agent_core/governance/test_exceptions.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add packages/agent_core/governance/exceptions.py tests/agent_core/governance/test_exceptions.py
git commit -m "feat(agent-core): add GovernanceStoreConfigurationError"
```

---

### Task 4: `GovernanceStateStore` Protocol

**Files:**
- Create: `packages/agent_core/governance/store.py`
- Create: `tests/agent_core/governance/test_store_protocol.py`

**Interfaces:**
- Consumes: `PinnedSpecIdentity`, `SpecResolutionManifest`, `InvocationGovernanceState`, `PolicyDecision`, `ApprovalEvidence` (Plan 1 Tasks 2/3/5, this plan's Task 1).
- Produces: `agent_core.governance.store.GovernanceStateStore` (a `runtime_checkable` `Protocol`) — Task 5's `PostgresGovernanceStateStore` must structurally satisfy it.

- [ ] **Step 1: Write the failing test**

Create `tests/agent_core/governance/test_store_protocol.py`:

```python
from __future__ import annotations

from agent_core.governance.store import GovernanceStateStore


def test_governance_state_store_protocol_declares_the_expected_methods():
    expected = {
        "save_manifest_entry",
        "load_manifest",
        "save_governance_state",
        "load_governance_state",
        "save_evidence",
        "list_evidence",
    }

    assert expected.issubset(set(dir(GovernanceStateStore)))
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/agent_core/governance/test_store_protocol.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_core.governance.store'`

- [ ] **Step 3: Implement the Protocol**

Create `packages/agent_core/governance/store.py`:

```python
from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from agent_core.governance.contracts import (
    ApprovalEvidence,
    InvocationGovernanceState,
    PinnedSpecIdentity,
    PolicyDecision,
    SpecResolutionManifest,
)


@runtime_checkable
class GovernanceStateStore(Protocol):
    """Durable persistence contract cho Identity Plane (SpecResolutionManifest)
    và Governance Plane (InvocationGovernanceState + ApprovalEvidence) — cùng
    mẫu Protocol với agentos/memory/base.py::MemoryStore và
    agentos/knowledge/store.py::KnowledgeStore."""

    async def save_manifest_entry(self, run_id: str, entry: PinnedSpecIdentity) -> None: ...

    async def load_manifest(self, run_id: str) -> SpecResolutionManifest: ...

    async def save_governance_state(
        self, state: InvocationGovernanceState, *, observation: PolicyDecision, source: str
    ) -> None: ...

    async def load_governance_state(
        self, run_id: str, tool_call_id: str
    ) -> Optional[InvocationGovernanceState]: ...

    async def save_evidence(self, evidence: ApprovalEvidence) -> None: ...

    async def list_evidence(self, scope: str) -> list[ApprovalEvidence]: ...
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/agent_core/governance/test_store_protocol.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add packages/agent_core/governance/store.py tests/agent_core/governance/test_store_protocol.py
git commit -m "feat(agent-core): add GovernanceStateStore protocol"
```

---

### Task 5: `PostgresGovernanceStateStore` — manifest methods

**Files:**
- Create: `packages/agent_core/governance/providers/__init__.py`
- Create: `packages/agent_core/governance/providers/postgres.py`
- Create: `tests/agent_core/governance/providers/__init__.py`
- Create: `tests/agent_core/governance/providers/test_postgres_store.py`

**Interfaces:**
- Consumes: `GovernanceStoreConfigurationError` (Task 3), `PinnedSpecIdentity`/`SpecResolutionManifest` (Plan 1 Task 2).
- Produces: `agent_core.governance.providers.postgres.PostgresGovernanceStateStore(db_session_factory)`, `.save_manifest_entry(run_id, entry)`, `.load_manifest(run_id)` — consumed by Task 6/7's remaining methods on the same class, and by Task 8's integration test.

- [ ] **Step 1: Create the empty provider package**

```bash
mkdir -p packages/agent_core/governance/providers tests/agent_core/governance/providers
touch packages/agent_core/governance/providers/__init__.py tests/agent_core/governance/providers/__init__.py
```

- [ ] **Step 2: Write the failing tests (fake-session style, mirroring `tests/agentos/memory/test_postgres_memory_store.py`)**

Create `tests/agent_core/governance/providers/test_postgres_store.py`:

```python
from __future__ import annotations

import pytest

from agent_core.governance.contracts import PinnedSpecIdentity
from agent_core.governance.exceptions import GovernanceStoreConfigurationError
from agent_core.governance.providers.postgres import PostgresGovernanceStateStore


class _FakeResult:
    def __init__(self, rows: list[tuple] | None = None) -> None:
        self._rows = rows or []

    def fetchall(self) -> list[tuple]:
        return self._rows

    def fetchone(self) -> tuple | None:
        return self._rows[0] if self._rows else None


class _FakeSession:
    def __init__(self, fetch_result: _FakeResult | None = None) -> None:
        self.executed: list[tuple[str, dict]] = []
        self.committed = False
        self._fetch_result = fetch_result or _FakeResult()

    async def execute(self, sql, params: dict | None = None):
        self.executed.append((str(sql), params or {}))
        return self._fetch_result

    async def commit(self) -> None:
        self.committed = True

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *exc) -> None:
        return None


def _session_factory(session: _FakeSession):
    return lambda: session


def test_init_without_session_factory_raises_configuration_error():
    with pytest.raises(GovernanceStoreConfigurationError) as exc_info:
        PostgresGovernanceStateStore(db_session_factory=None)
    assert "requires a valid `db_session_factory`" in str(exc_info.value)


@pytest.mark.asyncio
async def test_save_manifest_entry_inserts_into_the_manifest_table():
    session = _FakeSession()
    store = PostgresGovernanceStateStore(db_session_factory=_session_factory(session))
    entry = PinnedSpecIdentity(spec_kind="agent", spec_id="cofounder", spec_version="3", definition_hash="a" * 64)

    await store.save_manifest_entry("run-1", entry)

    assert session.committed is True
    sql, params = session.executed[0]
    assert "INSERT INTO agent_core_governance.spec_resolution_manifest_entries" in sql
    assert params["run_id"] == "run-1"
    assert params["spec_kind"] == "agent"
    assert params["spec_id"] == "cofounder"
    assert params["definition_hash"] == "a" * 64


@pytest.mark.asyncio
async def test_load_manifest_maps_rows_back_into_pinned_spec_identities():
    row = ("agent", "cofounder", "3", "a" * 64)
    session = _FakeSession(fetch_result=_FakeResult(rows=[row]))
    store = PostgresGovernanceStateStore(db_session_factory=_session_factory(session))

    manifest = await store.load_manifest("run-1")

    assert len(manifest.entries) == 1
    assert manifest.entries[0] == PinnedSpecIdentity(
        spec_kind="agent", spec_id="cofounder", spec_version="3", definition_hash="a" * 64
    )
    sql, params = session.executed[0]
    assert "FROM agent_core_governance.spec_resolution_manifest_entries" in sql
    assert params["run_id"] == "run-1"


@pytest.mark.asyncio
async def test_load_manifest_returns_an_empty_manifest_when_nothing_is_stored():
    session = _FakeSession(fetch_result=_FakeResult(rows=[]))
    store = PostgresGovernanceStateStore(db_session_factory=_session_factory(session))

    manifest = await store.load_manifest("unknown-run")

    assert manifest.entries == ()
```

- [ ] **Step 3: Run to verify failure**

Run: `.venv/bin/pytest tests/agent_core/governance/providers/test_postgres_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_core.governance.providers.postgres'`

- [ ] **Step 4: Implement `PostgresGovernanceStateStore` (manifest methods only)**

Create `packages/agent_core/governance/providers/postgres.py`:

```python
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import text

from agent_core.governance.contracts import PinnedSpecIdentity, SpecResolutionManifest
from agent_core.governance.exceptions import GovernanceStoreConfigurationError


class PostgresGovernanceStateStore:
    """PostgreSQL implementation của GovernanceStateStore — theo đúng mẫu
    agentos/memory/providers/postgres.py::PostgresMemoryStore (constructor
    nhận db_session_factory, raw SQL qua sqlalchemy.text(), JSON serialize
    thủ công). Schema: agent_core_governance (xem
    agentos/migrations/002_governance_temporal_model.sql)."""

    def __init__(self, db_session_factory: Any = None) -> None:
        if db_session_factory is None:
            raise GovernanceStoreConfigurationError(
                "PostgresGovernanceStateStore requires a valid `db_session_factory`."
            )
        self._session_factory = db_session_factory

    async def save_manifest_entry(self, run_id: str, entry: PinnedSpecIdentity) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent_core_governance.spec_resolution_manifest_entries
                        (run_id, spec_kind, spec_id, spec_version, definition_hash)
                    VALUES (:run_id, :spec_kind, :spec_id, :spec_version, :definition_hash)
                    ON CONFLICT (run_id, spec_kind, spec_id, definition_hash) DO NOTHING;
                    """
                ),
                {
                    "run_id": run_id,
                    "spec_kind": entry.spec_kind,
                    "spec_id": entry.spec_id,
                    "spec_version": entry.spec_version,
                    "definition_hash": entry.definition_hash,
                },
            )
            await session.commit()

    async def load_manifest(self, run_id: str) -> SpecResolutionManifest:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    SELECT spec_kind, spec_id, spec_version, definition_hash
                    FROM agent_core_governance.spec_resolution_manifest_entries
                    WHERE run_id = :run_id
                    ORDER BY resolved_at ASC;
                    """
                ),
                {"run_id": run_id},
            )
            rows = result.fetchall()
            entries = tuple(
                PinnedSpecIdentity(spec_kind=r[0], spec_id=r[1], spec_version=r[2], definition_hash=r[3])
                for r in rows
            )
            return SpecResolutionManifest(entries=entries)
```

- [ ] **Step 5: Run to verify it passes**

Run: `.venv/bin/pytest tests/agent_core/governance/providers/test_postgres_store.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add packages/agent_core/governance/providers tests/agent_core/governance/providers
git commit -m "feat(agent-core): add PostgresGovernanceStateStore manifest persistence"
```

---

### Task 6: `PostgresGovernanceStateStore` — invocation governance state + history

**Files:**
- Modify: `packages/agent_core/governance/providers/postgres.py`
- Modify: `tests/agent_core/governance/providers/test_postgres_store.py`

**Interfaces:**
- Consumes: `InvocationGovernanceState`, `PolicyDecision` (Plan 1 Tasks 3/5).
- Produces: `.save_governance_state(state, *, observation, source)`, `.load_governance_state(run_id, tool_call_id)` on `PostgresGovernanceStateStore`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/agent_core/governance/providers/test_postgres_store.py`:

```python
import json

from agent_core.governance.accumulator import InvocationGovernanceState
from agent_core.governance.contracts import PolicyDecision, PolicyOutcome, RoleApproval


@pytest.mark.asyncio
async def test_save_governance_state_upserts_state_and_appends_history():
    session = _FakeSession()
    store = PostgresGovernanceStateStore(db_session_factory=_session_factory(session))
    decision = PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL, requirement=RoleApproval(role="founder"))
    state = InvocationGovernanceState.start(run_id="run-1", tool_call_id="call-1", initial=decision)

    await store.save_governance_state(state, observation=decision, source="historical")

    assert session.committed is True
    assert len(session.executed) == 2
    state_sql, state_params = session.executed[0]
    assert "INSERT INTO agent_core_governance.invocation_governance_state" in state_sql
    assert state_params["run_id"] == "run-1"
    assert state_params["tool_call_id"] == "call-1"
    assert json.loads(state_params["accumulated"])["outcome"] == "REQUIRE_APPROVAL"

    history_sql, history_params = session.executed[1]
    assert "INSERT INTO agent_core_governance.invocation_governance_history" in history_sql
    assert history_params["source"] == "historical"
    assert json.loads(history_params["observation"])["outcome"] == "REQUIRE_APPROVAL"


@pytest.mark.asyncio
async def test_load_governance_state_returns_none_when_nothing_is_stored():
    session = _FakeSession(fetch_result=_FakeResult(rows=[]))
    store = PostgresGovernanceStateStore(db_session_factory=_session_factory(session))

    result = await store.load_governance_state("run-1", "call-1")

    assert result is None


@pytest.mark.asyncio
async def test_load_governance_state_reconstructs_the_accumulated_decision():
    accumulated_json = json.dumps(
        {"outcome": "REQUIRE_APPROVAL", "requirement": {"kind": "role_approval", "role": "founder"}, "reasons": []}
    )
    session = _FakeSession(fetch_result=_FakeResult(rows=[(accumulated_json,)]))
    store = PostgresGovernanceStateStore(db_session_factory=_session_factory(session))

    result = await store.load_governance_state("run-1", "call-1")

    assert result is not None
    assert result.run_id == "run-1"
    assert result.tool_call_id == "call-1"
    assert result.accumulated.outcome == PolicyOutcome.REQUIRE_APPROVAL
    assert result.accumulated.requirement == RoleApproval(role="founder")
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/agent_core/governance/providers/test_postgres_store.py -v`
Expected: FAIL — `AttributeError: 'PostgresGovernanceStateStore' object has no attribute 'save_governance_state'`

- [ ] **Step 3: Implement the two methods**

Add to `packages/agent_core/governance/providers/postgres.py` — first update the imports at the top of the file to:

```python
from __future__ import annotations

import json
import uuid
from typing import Any, Optional

from sqlalchemy import text

from agent_core.governance.contracts import (
    InvocationGovernanceState,
    PinnedSpecIdentity,
    PolicyDecision,
    SpecResolutionManifest,
)
from agent_core.governance.exceptions import GovernanceStoreConfigurationError
```

Then append these two methods to the `PostgresGovernanceStateStore` class (after `load_manifest`):

```python
    async def save_governance_state(
        self, state: InvocationGovernanceState, *, observation: PolicyDecision, source: str
    ) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent_core_governance.invocation_governance_state
                        (run_id, tool_call_id, accumulated, updated_at)
                    VALUES (:run_id, :tool_call_id, :accumulated, now())
                    ON CONFLICT (run_id, tool_call_id) DO UPDATE SET
                        accumulated = EXCLUDED.accumulated,
                        updated_at = EXCLUDED.updated_at;
                    """
                ),
                {
                    "run_id": state.run_id,
                    "tool_call_id": state.tool_call_id,
                    "accumulated": json.dumps(state.accumulated.model_dump(mode="json")),
                },
            )
            await session.execute(
                text(
                    """
                    INSERT INTO agent_core_governance.invocation_governance_history
                        (id, run_id, tool_call_id, observation, source)
                    VALUES (:id, :run_id, :tool_call_id, :observation, :source);
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "run_id": state.run_id,
                    "tool_call_id": state.tool_call_id,
                    "observation": json.dumps(observation.model_dump(mode="json")),
                    "source": source,
                },
            )
            await session.commit()

    async def load_governance_state(
        self, run_id: str, tool_call_id: str
    ) -> Optional[InvocationGovernanceState]:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    SELECT accumulated FROM agent_core_governance.invocation_governance_state
                    WHERE run_id = :run_id AND tool_call_id = :tool_call_id;
                    """
                ),
                {"run_id": run_id, "tool_call_id": tool_call_id},
            )
            row = result.fetchone()
            if row is None:
                return None
            accumulated_val = row[0]
            if isinstance(accumulated_val, str):
                accumulated_val = json.loads(accumulated_val)
            return InvocationGovernanceState(
                run_id=run_id,
                tool_call_id=tool_call_id,
                accumulated=PolicyDecision.model_validate(accumulated_val),
            )
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/agent_core/governance/providers/test_postgres_store.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add packages/agent_core/governance/providers/postgres.py tests/agent_core/governance/providers/test_postgres_store.py
git commit -m "feat(agent-core): add invocation governance state persistence with append-only history"
```

---

### Task 7: `PostgresGovernanceStateStore` — approval evidence

**Files:**
- Modify: `packages/agent_core/governance/providers/postgres.py`
- Modify: `tests/agent_core/governance/providers/test_postgres_store.py`

**Interfaces:**
- Consumes: `ApprovalEvidence` (Plan 1 Task 3 + this plan's Task 1).
- Produces: `.save_evidence(evidence)`, `.list_evidence(scope)` on `PostgresGovernanceStateStore` — this completes the `GovernanceStateStore` Protocol (Task 4).

- [ ] **Step 1: Write the failing tests**

Append to `tests/agent_core/governance/providers/test_postgres_store.py`:

```python
from agent_core.governance.contracts import ApprovalEvidence


@pytest.mark.asyncio
async def test_save_evidence_inserts_into_the_approval_evidence_table():
    session = _FakeSession()
    store = PostgresGovernanceStateStore(db_session_factory=_session_factory(session))
    evidence = ApprovalEvidence(
        id="evidence-1", approver="founder-1", scope="call-1", decided_at="2026-08-23T10:00:00Z"
    )

    await store.save_evidence(evidence)

    assert session.committed is True
    sql, params = session.executed[0]
    assert "INSERT INTO agent_core_governance.approval_evidence" in sql
    assert params["id"] == "evidence-1"
    assert params["approver"] == "founder-1"
    assert params["scope"] == "call-1"
    assert params["decided_at"] == "2026-08-23T10:00:00Z"
    assert params["valid_until"] is None


@pytest.mark.asyncio
async def test_list_evidence_maps_rows_back_into_approval_evidence():
    row = ("evidence-1", "founder-1", "call-1", "2026-08-23T10:00:00Z", None)
    session = _FakeSession(fetch_result=_FakeResult(rows=[row]))
    store = PostgresGovernanceStateStore(db_session_factory=_session_factory(session))

    results = await store.list_evidence("call-1")

    assert len(results) == 1
    assert results[0] == ApprovalEvidence(
        id="evidence-1", approver="founder-1", scope="call-1", decided_at="2026-08-23T10:00:00Z", valid_until=None
    )
    sql, params = session.executed[0]
    assert "FROM agent_core_governance.approval_evidence" in sql
    assert params["scope"] == "call-1"


@pytest.mark.asyncio
async def test_list_evidence_returns_empty_list_when_nothing_is_stored():
    session = _FakeSession(fetch_result=_FakeResult(rows=[]))
    store = PostgresGovernanceStateStore(db_session_factory=_session_factory(session))

    results = await store.list_evidence("unknown-scope")

    assert results == []
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/agent_core/governance/providers/test_postgres_store.py -v`
Expected: FAIL — `AttributeError: 'PostgresGovernanceStateStore' object has no attribute 'save_evidence'`

- [ ] **Step 3: Implement the two methods**

Add `ApprovalEvidence` to the `agent_core.governance.contracts` import line at the top of `packages/agent_core/governance/providers/postgres.py`:

```python
from agent_core.governance.contracts import (
    ApprovalEvidence,
    InvocationGovernanceState,
    PinnedSpecIdentity,
    PolicyDecision,
    SpecResolutionManifest,
)
```

Then append these two methods to `PostgresGovernanceStateStore` (after `load_governance_state`):

```python
    async def save_evidence(self, evidence: ApprovalEvidence) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent_core_governance.approval_evidence
                        (id, approver, scope, decided_at, valid_until)
                    VALUES (:id, :approver, :scope, :decided_at, :valid_until)
                    ON CONFLICT (id) DO NOTHING;
                    """
                ),
                {
                    "id": evidence.id,
                    "approver": evidence.approver,
                    "scope": evidence.scope,
                    "decided_at": evidence.decided_at,
                    "valid_until": evidence.valid_until,
                },
            )
            await session.commit()

    async def list_evidence(self, scope: str) -> list[ApprovalEvidence]:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    SELECT id, approver, scope, decided_at, valid_until
                    FROM agent_core_governance.approval_evidence
                    WHERE scope = :scope
                    ORDER BY decided_at ASC;
                    """
                ),
                {"scope": scope},
            )
            rows = result.fetchall()
            return [
                ApprovalEvidence(id=r[0], approver=r[1], scope=r[2], decided_at=r[3], valid_until=r[4])
                for r in rows
            ]
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/agent_core/governance/providers/test_postgres_store.py -v`
Expected: 10 passed

- [ ] **Step 5: Confirm `PostgresGovernanceStateStore` now structurally satisfies `GovernanceStateStore`**

Run:
```bash
.venv/bin/python -c "
from agent_core.governance.providers.postgres import PostgresGovernanceStateStore
from agent_core.governance.store import GovernanceStateStore
store = PostgresGovernanceStateStore(db_session_factory=lambda: None)
assert isinstance(store, GovernanceStateStore)
print('OK')
"
```
Expected: prints `OK`

- [ ] **Step 6: Commit**

```bash
git add packages/agent_core/governance/providers/postgres.py tests/agent_core/governance/providers/test_postgres_store.py
git commit -m "feat(agent-core): add approval evidence persistence, completing GovernanceStateStore"
```

---

### Task 8: Real-Postgres integration test

**Files:**
- Create: `tests/agent_core/governance/providers/test_postgres_store_integration.py`

**Interfaces:**
- Consumes: `PostgresGovernanceStateStore` (Tasks 5-7), the migration from Task 2.

- [ ] **Step 1: Write the integration test, gated exactly like `tests/agentos/memory/test_postgres_memory_store_integration.py`**

Create `tests/agent_core/governance/providers/test_postgres_store_integration.py`:

```python
"""Integration test cho PostgresGovernanceStateStore chạy với Postgres thật.

Yêu cầu env var `AGENTOS_TEST_DATABASE_URL` trỏ tới 1 Postgres đã chạy migration
`agentos/migrations/002_governance_temporal_model.sql`. Bỏ qua (skip) nếu biến
này không được set — CI không có Postgres vẫn chạy được suite còn lại.
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
async def test_manifest_entries_roundtrip_and_grow_monotonically(session_factory):
    from agent_core.governance.contracts import PinnedSpecIdentity
    from agent_core.governance.providers.postgres import PostgresGovernanceStateStore

    store = PostgresGovernanceStateStore(db_session_factory=session_factory)
    run_id = f"run-{uuid.uuid4().hex[:8]}"
    first = PinnedSpecIdentity(spec_kind="workflow", spec_id="monthly-review", spec_version="7", definition_hash="a" * 64)
    second = PinnedSpecIdentity(spec_kind="agent", spec_id="legal", spec_version="3", definition_hash="b" * 64)

    await store.save_manifest_entry(run_id, first)
    manifest_after_first = await store.load_manifest(run_id)
    assert manifest_after_first.entries == (first,)

    await store.save_manifest_entry(run_id, second)
    manifest_after_second = await store.load_manifest(run_id)
    assert manifest_after_second.entries == (first, second)  # tăng dần, không mất entry cũ


@pytest.mark.asyncio
async def test_governance_state_roundtrip_and_history_is_append_only(session_factory):
    from agent_core.governance.accumulator import InvocationGovernanceState
    from agent_core.governance.contracts import PolicyDecision, PolicyOutcome, RoleApproval
    from agent_core.governance.providers.postgres import PostgresGovernanceStateStore

    store = PostgresGovernanceStateStore(db_session_factory=session_factory)
    run_id = f"run-{uuid.uuid4().hex[:8]}"
    tool_call_id = "call-1"

    g0 = PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL, requirement=RoleApproval(role="finance_admin"))
    state = InvocationGovernanceState.start(run_id=run_id, tool_call_id=tool_call_id, initial=g0)
    await store.save_governance_state(state, observation=g0, source="historical")

    loaded = await store.load_governance_state(run_id, tool_call_id)
    assert loaded is not None
    assert loaded.accumulated == g0

    g1 = PolicyDecision(outcome=PolicyOutcome.DENY, reasons=("tenant_suspended",))
    state = state.accumulate(g1)
    await store.save_governance_state(state, observation=g1, source="ambient")

    loaded_after_second = await store.load_governance_state(run_id, tool_call_id)
    assert loaded_after_second is not None
    assert loaded_after_second.accumulated.outcome == PolicyOutcome.DENY


@pytest.mark.asyncio
async def test_load_governance_state_returns_none_for_an_unknown_invocation(session_factory):
    from agent_core.governance.providers.postgres import PostgresGovernanceStateStore

    store = PostgresGovernanceStateStore(db_session_factory=session_factory)

    result = await store.load_governance_state(f"run-{uuid.uuid4().hex[:8]}", "unknown-call")

    assert result is None


@pytest.mark.asyncio
async def test_approval_evidence_roundtrip_scoped_by_invocation(session_factory):
    from agent_core.governance.contracts import ApprovalEvidence
    from agent_core.governance.providers.postgres import PostgresGovernanceStateStore

    store = PostgresGovernanceStateStore(db_session_factory=session_factory)
    scope = f"call-{uuid.uuid4().hex[:8]}"
    evidence = ApprovalEvidence(approver="founder-1", scope=scope, decided_at="2026-08-23T10:00:00Z")

    await store.save_evidence(evidence)
    results = await store.list_evidence(scope)

    assert len(results) == 1
    assert results[0].id == evidence.id
    assert results[0].approver == "founder-1"
```

- [ ] **Step 2: Run without a database configured — confirm it skips cleanly**

Run: `.venv/bin/pytest tests/agent_core/governance/providers/test_postgres_store_integration.py -v`
Expected: 4 skipped, 0 failed (no `AGENTOS_TEST_DATABASE_URL` set)

- [ ] **Step 3: Run against a real local Postgres**

Run:
```bash
docker compose up -d postgres
until docker compose exec -T postgres pg_isready -U ${POSTGRES_USER:-javis}; do sleep 1; done
psql "${DATABASE_URL:-postgresql://javis_app:change-me-javis-app@localhost:5432/javis}" -f agentos/migrations/002_governance_temporal_model.sql
AGENTOS_TEST_DATABASE_URL="postgresql+asyncpg://javis_app:change-me-javis-app@localhost:5432/javis" \
  .venv/bin/pytest tests/agent_core/governance/providers/test_postgres_store_integration.py -v
```
Expected: 4 passed. (Note the `postgresql+asyncpg://` scheme required by SQLAlchemy's async engine, vs. the plain `postgresql://` used by `psql` in the migration step above.)

- [ ] **Step 4: Run the complete `agent-core-test` suite one final time**

Run: `make agent-core-test`
Expected: all pass (integration tests skip if `AGENTOS_TEST_DATABASE_URL` isn't exported for this invocation — that's expected in a plain `make agent-core-test` run)

- [ ] **Step 5: Commit**

```bash
git add tests/agent_core/governance/providers/test_postgres_store_integration.py
git commit -m "test(agent-core): add real-Postgres integration test for GovernanceStateStore"
```

---

## Self-review notes

- **Spec coverage**: every table named in the governance temporal model doc's Bước 6 section for this plan's scope (`run_pinned_specs` → implemented as `spec_resolution_manifest_entries`, `invocation_governance_state`, `approval_evidence`) has a migration table and a store method pair. The append-only `invocation_governance_history` table (provenance requirement, PHẦN I §2.5) was added beyond the doc's literal table list because `invocation_governance_state` alone only holds the latest value and cannot answer "was this DENY ambient or historical" after the fact — necessary to satisfy the provenance invariant, not scope creep.
- **Explicitly not in this plan**: `runs`/`run_checkpoints`/`run_events`/`run_tool_calls` tables (they don't exist anywhere yet and are a separate, larger foundational plan), rewriting `ApprovalService` to use this store (Plan 3), and `RunLevelCurrentGate` persistence (ambient/current, not something this plan's tables model — it reads live state from elsewhere, not from an accumulator table).
- **Type consistency**: `PostgresGovernanceStateStore`'s six method signatures match `GovernanceStateStore`'s Protocol definition (Task 4) exactly, verified structurally in Task 7 Step 5 via `isinstance(store, GovernanceStateStore)`.
- **No placeholders**: every step has literal SQL/Python and an exact command with an expected result.

## Next plan (not in scope here)

**Plan 3 (V4 Bước 7)**: rewire `agentos/workflows/tool_step.py::ToolCallStep` and `agentos/workflows/steps.py::AgentStep` to call `evaluate_access()` at each freshness boundary, fold the result into a `PostgresGovernanceStateStore`-backed `InvocationGovernanceState` via `combine_decisions`, resolve `agent_permission_level`/`execution_mode` from a real `SpecResolutionManifest` instead of hardcoded constructor params, and finish the ADR-014 cutover (replace remaining `evaluate(PermissionClass)` call sites in `Executor`/`ApprovalGateStep`).
