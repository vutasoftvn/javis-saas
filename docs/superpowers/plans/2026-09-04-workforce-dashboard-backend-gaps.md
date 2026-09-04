# Workforce Dashboard Backend Gaps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the 5 read-mostly Workforce Dashboard endpoints that
`docs/architecture/frontend-api-migration-register.md` flagged as
"unknown — BLOCKS RELEASE" (agents roster, work products, stage roster,
dashboard summary, escalations list — read-only), and migrate the
corresponding `AgentPlatformService` methods off raw `/workforce/...` calls
onto the canonical `MvpRequestClient`/`WorkforceMvpService` path, matching
the Task 7 pattern already used for approvals/org-chart/runs.

**Architecture:** All 5 endpoints mount on the existing `apps/cosa/api/workforce_routes.py`
router (`prefix=/agent/workforce`) and reuse data already computed elsewhere
(functional agent catalog + assignments, artifact repository, run repository,
Company `operating.tasks`) — no new Postgres tables. Phase 3 (stage roster) is
the one cross-plane piece: `apps/cosa` calls a new `services/company` handler
using the existing `resolveCosaTaskContext` delegation pattern. Frontend gets
5 new typed models + `WorkforceMvpService` methods, then `AgentPlatformService`
delegates to them (same shape as the Task 7 migration for `listApprovals`).

**Tech Stack:** Python 3.11 / FastAPI / Pydantic (`apps/cosa`), TypeScript /
Encore.ts (`services/company`), Dart / Flutter (`frontend`), pytest +
`httpx.ASGITransport` for backend tests, `flutter_test` + `http/testing.dart`
`MockClient` for frontend tests.

## Global Constraints

- No new Postgres tables/migrations in any task — every data source already
  exists (see spec `docs/superpowers/specs/2026-09-04-workforce-dashboard-backend-gaps-design.md`).
- Any field with no real data source uses a named constant with a comment
  explaining why — never an invented/derived-looking value (CLAUDE.md rule 7).
- `resolveEscalation` (the mutation) is explicitly OUT of scope — Task 12
  must make the FE "Resolve" button inert/hidden, not call a fake backend.
- Every new backend route: reuse `get_authenticated_identity` /
  `AuthenticatedIdentity.workspace_id` for tenant scoping — never trust a
  client-supplied workspace id without it.
- Every new frontend method: return `ApiResult<T>` via `WorkforceMvpService`
  (never swallow `ApiFailure` into `null`/`[]`), per the Task 7 precedent
  already enforced by `agent_platform_service_test.dart`.
- Run `make apps-cosa-test`, `cd services/company && encore test`, and
  `cd frontend && flutter test` (targeted files per task, full suite in the
  final task) — do not claim a task done without the test actually run and
  shown passing.

---

## Task 1: `ArtifactRepository.list_for_workspace` (foundation for Phase 2)

**Files:**
- Modify: `packages/agent/artifacts/repository.py` (add to `ArtifactRepository` Protocol + `InMemoryArtifactRepository`)
- Modify: `packages/agent/artifacts/postgres.py` (add to `PostgresArtifactRepository`)
- Test: `tests/agent/artifacts/test_repository.py` (create if it doesn't exist, else append)

**Interfaces:**
- Produces: `async def list_for_workspace(self, workspace_id: str, limit: int = 50, include_archived: bool = False) -> list[WorkspaceArtifact]` on both `InMemoryArtifactRepository` and `PostgresArtifactRepository`, and declared on the `ArtifactRepository` Protocol.

- [ ] **Step 1: Write the failing test (in-memory)**

```python
# tests/agent/artifacts/test_repository.py
from __future__ import annotations

import pytest

from agent.artifacts.models import WorkspaceArtifact
from agent.artifacts.repository import InMemoryArtifactRepository


@pytest.mark.asyncio
async def test_list_for_workspace_returns_artifacts_across_conversations_newest_first() -> None:
    repo = InMemoryArtifactRepository()
    older = WorkspaceArtifact(
        workspace_id="ws_1",
        conversation_id="conv_a",
        display_name="Older report",
        media_type="text/markdown",
        object_ref="object://a",
    )
    newer = WorkspaceArtifact(
        workspace_id="ws_1",
        conversation_id="conv_b",
        display_name="Newer report",
        media_type="text/markdown",
        object_ref="object://b",
    )
    other_workspace = WorkspaceArtifact(
        workspace_id="ws_2",
        conversation_id="conv_c",
        display_name="Other workspace",
        media_type="text/markdown",
        object_ref="object://c",
    )
    await repo.create(older)
    await repo.create(newer)
    await repo.create(other_workspace)

    result = await repo.list_for_workspace("ws_1", limit=50)

    assert [a.artifact_id for a in result] == [newer.artifact_id, older.artifact_id]


@pytest.mark.asyncio
async def test_list_for_workspace_excludes_archived_by_default() -> None:
    repo = InMemoryArtifactRepository()
    art = WorkspaceArtifact(
        workspace_id="ws_1",
        conversation_id="conv_a",
        display_name="Archived report",
        media_type="text/markdown",
        object_ref="object://a",
    )
    await repo.create(art)
    await repo.archive("ws_1", art.artifact_id)

    result = await repo.list_for_workspace("ws_1", limit=50)

    assert result == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/artifacts/test_repository.py -v`
Expected: FAIL with `AttributeError: 'InMemoryArtifactRepository' object has no attribute 'list_for_workspace'`

- [ ] **Step 3: Implement `list_for_workspace` on `InMemoryArtifactRepository`**

In `packages/agent/artifacts/repository.py`, add to the `ArtifactRepository` Protocol (after `list_for_conversation`):

```python
    async def list_for_workspace(
        self,
        workspace_id: str,
        limit: int = 50,
        include_archived: bool = False,
    ) -> list[WorkspaceArtifact]: ...
```

Add to `InMemoryArtifactRepository` (after `list_for_conversation`):

```python
    async def list_for_workspace(
        self,
        workspace_id: str,
        limit: int = 50,
        include_archived: bool = False,
    ) -> list[WorkspaceArtifact]:
        async with self._lock:
            results = [
                a.model_copy(deep=True)
                for a in self._artifacts.values()
                if a.workspace_id == workspace_id
                and (include_archived or a.status != "archived")
            ]
            results.sort(key=lambda x: x.created_at, reverse=True)
            return results[:limit]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/artifacts/test_repository.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Implement `list_for_workspace` on `PostgresArtifactRepository`**

In `packages/agent/artifacts/postgres.py`, add after `list_for_conversation`:

```python
    async def list_for_workspace(
        self,
        workspace_id: str,
        limit: int = 50,
        include_archived: bool = False,
    ) -> list[WorkspaceArtifact]:
        query = """
            SELECT artifact_id, workspace_id, conversation_id, run_id,
                   source_message_id, artifact_kind, display_name, media_type,
                   object_ref, checksum, size_bytes, status, input_artifact_ids,
                   created_at, archived_at
            FROM agent_artifact.workspace_artifacts
            WHERE workspace_id = :workspace_id
        """
        if not include_archived:
            query += " AND status != 'archived'"
        query += " ORDER BY created_at DESC LIMIT :limit"

        async with self._session_factory() as session:
            res = await session.execute(
                text(query),
                {"workspace_id": workspace_id, "limit": limit},
            )
            rows = res.mappings().all()
            return [self._row_to_artifact(r) for r in rows]
```

This is a plain read query against the existing `agent_artifact.workspace_artifacts`
table (no schema change) — no migration needed.

- [ ] **Step 6: Commit**

```bash
git add packages/agent/artifacts/repository.py packages/agent/artifacts/postgres.py tests/agent/artifacts/test_repository.py
git commit -m "feat(agent): thêm ArtifactRepository.list_for_workspace cho workforce work-products

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 2: Backend — `GET /agent/workforce/roster` (Phase 1: agents roster)

**Files:**
- Modify: `apps/cosa/api/workforce_schemas.py` (add `WorkforceRosterEntryOut`)
- Modify: `apps/cosa/api/workforce_routes.py` (add route)
- Test: `tests/apps/cosa/test_workforce_routes.py` (append)

**Interfaces:**
- Consumes: `FUNCTIONAL_AGENT_CATALOG` (`agent.workforce.catalog`, already imported in `workforce_routes.py`), `repo.list_assignments(workspace_id, status="ACTIVE")` (already used by `get_composition`).
- Produces: `GET /agent/workforce/roster` → `MvpSuccess[list[WorkforceRosterEntryOut]]`.

- [ ] **Step 1: Write the failing test**

Append to `tests/apps/cosa/test_workforce_routes.py`:

```python
@pytest.mark.asyncio
async def test_roster_lists_functional_catalog_with_default_available_status(test_app) -> None:
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        res = await client.get("/agent/workforce/roster")
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data) == 6  # FUNCTIONAL_AGENT_CATALOG has 6 entries today
        cashflow = next(e for e in data if e["key"] == "cashflow_planner")
        assert cashflow["name"] == "Cashflow Planner"
        assert cashflow["department"] == "Finance"
        assert cashflow["status"] == "available"
        assert cashflow["enabled"] is True


@pytest.mark.asyncio
async def test_roster_marks_assigned_entries_active(test_app) -> None:
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        create_res = await client.post(
            "/agent/workforce/assignments",
            json={"functional_key": "campaign_planner"},
        )
        assert create_res.status_code == 200

        res = await client.get("/agent/workforce/roster")
        assert res.status_code == 200
        entry = next(e for e in res.json()["data"] if e["key"] == "campaign_planner")
        assert entry["status"] == "active"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/test_workforce_routes.py -k roster -v`
Expected: FAIL with 404 (route doesn't exist yet)

- [ ] **Step 3: Add `WorkforceRosterEntryOut` schema**

In `apps/cosa/api/workforce_schemas.py`, add after `WorkforceCompositionEntry`:

```python
class WorkforceRosterEntryOut(BaseModel):
    id: int
    key: str
    name: str
    role_title: str
    department: str
    agent_type: str
    default_model_profile: str
    risk_level: int
    status: str
    enabled: bool
```

- [ ] **Step 4: Add the route**

In `apps/cosa/api/workforce_routes.py`, add after `get_composition` (after the
`# ─── Org Chart ───` marker's preceding blank line, i.e. right before it):

```python
@router.get("/roster")
async def get_roster(
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[list[WorkforceRosterEntryOut]]:
    """Danh sách functional agent thật (không phải `default12Agents` hard-code
    ở FE) — nguồn = FUNCTIONAL_AGENT_CATALOG + trạng thái assignment thật theo
    workspace. Xem docs/superpowers/specs/2026-09-04-workforce-dashboard-backend-gaps-design.md
    Phase 1 cho lý do dùng catalog này thay vì AgentSpec thô."""
    repo = _get_workforce_repo(request)
    assignments = await repo.list_assignments(identity.workspace_id, status="ACTIVE")
    assigned_keys = {a.functional_key for a in assignments}

    entries = [
        WorkforceRosterEntryOut(
            id=idx,
            key=entry.functional_key,
            name=entry.title,
            role_title=entry.description,
            department=entry.default_department,
            agent_type="specialist",
            default_model_profile="reasoning",
            # Hằng số — FunctionalAgentEntry chưa có autonomy_level; mọi entry
            # catalog hiện tại đều dạng "đề xuất, không tự thực thi" (medium).
            risk_level=2,
            status="active" if entry.functional_key in assigned_keys else "available",
            enabled=True,
        )
        for idx, entry in enumerate(FUNCTIONAL_AGENT_CATALOG.values(), start=1)
    ]
    return mvp_list(entries, [MvpSourceRef(kind="agent_db", ref="agent.workforce_assignments")])
```

And add `WorkforceRosterEntryOut` to the `from apps.cosa.api.workforce_schemas import (...)` block at the top of the file.

- [ ] **Step 5: Run test to verify it passes**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/test_workforce_routes.py -k roster -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add apps/cosa/api/workforce_schemas.py apps/cosa/api/workforce_routes.py tests/apps/cosa/test_workforce_routes.py
git commit -m "feat(cosa): thêm GET /agent/workforce/roster — Phase 1 workforce dashboard

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 3: Backend — `GET /agent/workforce/artifacts` (Phase 2: work products)

**Files:**
- Modify: `apps/cosa/api/workforce_schemas.py` (add `WorkforceWorkProductOut`)
- Modify: `apps/cosa/api/workforce_routes.py` (add route)
- Test: `tests/apps/cosa/test_workforce_routes.py` (append)

**Interfaces:**
- Consumes: `plane.artifact_repository.list_for_workspace(workspace_id, limit)` (Task 1), `plane.repository.list_runs(workspace_id, limit)` (existing, used by `list_runs` route).
- Produces: `GET /agent/workforce/artifacts?limit=` → `MvpSuccess[list[WorkforceWorkProductOut]]`.

- [ ] **Step 1: Write the failing test**

Append to `tests/apps/cosa/test_workforce_routes.py`:

```python
@pytest.mark.asyncio
async def test_work_products_maps_workspace_artifacts(test_app) -> None:
    from agent.artifacts.models import WorkspaceArtifact
    from agent.contracts.run import RunStatus
    from agent.runs.models import RunRecord

    plane = test_app.state.plane
    run = RunRecord(
        run_id="run_wp_1",
        workspace_id="ws_1001",
        principal="user:founder",
        root_executable_id="functional.market_research_specialist",
        status=RunStatus.COMPLETED,
    )
    await plane.repository.create_run(run)
    await plane.artifact_repository.create(
        WorkspaceArtifact(
            workspace_id="ws_1001",
            conversation_id="conv_1",
            run_id="run_wp_1",
            display_name="Market brief Q1",
            media_type="text/markdown",
            object_ref="object://brief-q1",
        )
    )

    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        res = await client.get("/agent/workforce/artifacts")
        assert res.status_code == 200
        items = res.json()["data"]
        assert len(items) == 1
        item = items[0]
        assert item["title"] == "Market brief Q1"
        assert item["product_type"] == "text/markdown"
        assert item["status"] == "READY"
        assert item["author_agent_key"] == "functional.market_research_specialist"
        assert item["object_ref"] == "object://brief-q1"


@pytest.mark.asyncio
async def test_work_products_author_unknown_when_run_outside_window(test_app) -> None:
    from agent.artifacts.models import WorkspaceArtifact

    plane = test_app.state.plane
    await plane.artifact_repository.create(
        WorkspaceArtifact(
            workspace_id="ws_1001",
            conversation_id="conv_1",
            run_id="run_not_seeded",
            display_name="Orphan artifact",
            media_type="text/markdown",
            object_ref="object://orphan",
        )
    )

    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        res = await client.get("/agent/workforce/artifacts")
        assert res.json()["data"][0]["author_agent_key"] == "unknown"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/test_workforce_routes.py -k work_products -v`
Expected: FAIL with 404

- [ ] **Step 3: Add `WorkforceWorkProductOut` schema**

In `apps/cosa/api/workforce_schemas.py`, add after `WorkforceRosterEntryOut`:

```python
_ARTIFACT_STATUS_MAP = {"available": "READY", "failed": "FAILED", "archived": "ARCHIVED"}


class WorkforceWorkProductOut(BaseModel):
    id: str
    title: str
    product_type: str
    status: str
    author_agent_key: str
    object_ref: str
    created_at: str
```

- [ ] **Step 4: Add the route**

In `apps/cosa/api/workforce_routes.py`, add after the `get_roster` route from Task 2:

```python
@router.get("/artifacts")
async def list_work_products(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[list[WorkforceWorkProductOut]]:
    """MVP "work products" = artifact ghi nhận trong workspace, workspace-wide
    (khác /runs/{run_id}/artifacts vốn theo từng run). Xem spec Phase 2 cho
    known gap (content_markdown chưa fetch được — FE dùng object_ref)."""
    plane = _get_plane(request)
    if plane.artifact_repository is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ArtifactRepository is not configured",
        )
    artifacts = await plane.artifact_repository.list_for_workspace(
        identity.workspace_id, limit=limit
    )
    runs = await plane.repository.list_runs(identity.workspace_id, limit=limit)
    run_author_map = {r.run_id: r.root_executable_id for r in runs}

    items = [
        WorkforceWorkProductOut(
            id=a.artifact_id,
            title=a.display_name,
            product_type=a.media_type,
            status=_ARTIFACT_STATUS_MAP.get(a.status, a.status.upper()),
            author_agent_key=run_author_map.get(a.run_id or "", "unknown"),
            object_ref=a.object_ref,
            created_at=a.created_at.isoformat(),
        )
        for a in artifacts
    ]
    return mvp_list(items, [MvpSourceRef(kind="agent_db", ref="agent_artifact.workspace_artifacts")])
```

Add `WorkforceWorkProductOut` to the schema import block at the top of the file.

- [ ] **Step 5: Run test to verify it passes**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/test_workforce_routes.py -k work_products -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add apps/cosa/api/workforce_schemas.py apps/cosa/api/workforce_routes.py tests/apps/cosa/test_workforce_routes.py
git commit -m "feat(cosa): thêm GET /agent/workforce/artifacts — Phase 2 workforce dashboard

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 4: Backend — `GET /agent/workforce/exceptions` (Phase 5: escalations list, read-only)

**Files:**
- Modify: `apps/cosa/api/workforce_schemas.py` (add `WorkforceExceptionOut`, `WorkforceExceptionListOut`)
- Modify: `apps/cosa/api/workforce_routes.py` (add route)
- Test: `tests/apps/cosa/test_workforce_routes.py` (append)

**Interfaces:**
- Consumes: `plane.repository.list_runs(workspace_id, limit)` (existing).
- Produces: `GET /agent/workforce/exceptions` → `MvpSuccess[WorkforceExceptionListOut]`. No `status` query param — pre-flight review (2026-09-04) decided against accepting a filter param the route can't honor (MVP has no persisted resolution state, so "OPEN vs RESOLVED" isn't a real distinction yet); add the param back only alongside the real escalation domain.

- [ ] **Step 1: Write the failing test**

Append to `tests/apps/cosa/test_workforce_routes.py`:

```python
@pytest.mark.asyncio
async def test_exceptions_lists_failed_runs_as_open(test_app) -> None:
    from agent.contracts.run import RunStatus
    from agent.runs.models import RunRecord

    plane = test_app.state.plane
    await plane.repository.create_run(
        RunRecord(
            run_id="run_failed_1",
            workspace_id="ws_1001",
            principal="user:founder",
            root_executable_id="functional.cashflow_planner",
            status=RunStatus.FAILED,
        )
    )
    await plane.repository.create_run(
        RunRecord(
            run_id="run_ok_1",
            workspace_id="ws_1001",
            principal="user:founder",
            root_executable_id="functional.cashflow_planner",
            status=RunStatus.COMPLETED,
        )
    )

    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        res = await client.get("/agent/workforce/exceptions")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["total"] == 1
        assert data["founder_gate_count"] == 0
        assert data["has_critical"] is False
        assert data["escalations"][0]["id"] == "run_failed_1"
        assert data["escalations"][0]["exception_type"] == "run_failed"
        assert data["escalations"][0]["tier"] == "LEAD_NOTIFY"
        assert data["escalations"][0]["status"] == "OPEN"


@pytest.mark.asyncio
async def test_exceptions_empty_when_no_failed_runs(test_app) -> None:
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        res = await client.get("/agent/workforce/exceptions")
        assert res.status_code == 200
        assert res.json()["data"]["total"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/test_workforce_routes.py -k exceptions -v`
Expected: FAIL with 404

- [ ] **Step 3: Add schemas**

In `apps/cosa/api/workforce_schemas.py`, add after `WorkforceWorkProductOut`:

```python
class WorkforceExceptionOut(BaseModel):
    id: str
    exception_type: str
    tier: str
    status: str
    agent_key: str
    created_at: str


class WorkforceExceptionListOut(BaseModel):
    total: int
    founder_gate_count: int
    lead_notify_count: int
    has_critical: bool
    escalations: list[WorkforceExceptionOut]
```

- [ ] **Step 4: Add the route**

In `apps/cosa/api/workforce_routes.py`, add after `list_work_products`:

```python
@router.get("/exceptions")
async def list_exceptions(
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[WorkforceExceptionListOut]:
    """MVP read-only "escalations" — KHÔNG có resolve endpoint (xem spec Phase 5).
    Định nghĩa "escalation" = run FAILED trong workspace. tier LUÔN
    "LEAD_NOTIFY" (chưa có phân loại rủi ro FOUNDER_GATE thật — không tự bịa,
    cần thiết kế domain riêng trước khi phân loại rủi ro cao/thấp)."""
    plane = _get_plane(request)
    runs = await plane.repository.list_runs(identity.workspace_id, limit=200)
    from agent.contracts.run import RunStatus

    failed = [r for r in runs if r.status == RunStatus.FAILED]

    items = [
        WorkforceExceptionOut(
            id=r.run_id,
            exception_type="run_failed",
            tier="LEAD_NOTIFY",
            status="OPEN",
            agent_key=r.root_executable_id,
            created_at=r.created_at.isoformat() if r.created_at else datetime.now(UTC).isoformat(),
        )
        for r in failed
    ]
    out = WorkforceExceptionListOut(
        total=len(items),
        founder_gate_count=0,
        lead_notify_count=len(items),
        has_critical=False,
        escalations=items,
    )
    return mvp_item(out, [MvpSourceRef(kind="agent_db", ref="agent.runs")])
```

Add `WorkforceExceptionOut`, `WorkforceExceptionListOut` to the schema import block.

Do not add a `status` query param or a `RESOLVED` branch here — MVP has no
persisted resolution state (every failed run is always "OPEN"); that
requires the excluded escalation domain (see spec Phase 5 / Global
Constraints).

- [ ] **Step 5: Run test to verify it passes**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/test_workforce_routes.py -k exceptions -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add apps/cosa/api/workforce_schemas.py apps/cosa/api/workforce_routes.py tests/apps/cosa/test_workforce_routes.py
git commit -m "feat(cosa): thêm GET /agent/workforce/exceptions (read-only) — Phase 5 workforce dashboard

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 5: Company — stage roster handler (Phase 3a)

**Files:**
- Modify: `services/company/operations/services/task.service.ts` (add `listStageRosterService`)
- Modify: `services/company/operations/handlers/task.handler.ts` (add `getStageRoster` endpoint)
- Test: `services/company/operations/tests/task-stage-roster.test.ts` (create)

**Interfaces:**
- Consumes: `resolveCosaTaskContext`, `WGA_CAP_TASK_LIST` (`../../shared/auth/cosa-task-delegation`, already imported in `task.handler.ts`); Drizzle `schema.projectOperatingSetups` (`shared/db/schema/strategy.ts:277`), `schema.tasks` / `schema.taskProjects` (`shared/db/schema/operations.ts:18` and `:225` — confirmed by direct grep, these 3 export names are correct and already re-exported through `services/company/operations/models/db.ts`'s `schema` barrel used elsewhere in `task.handler.ts`).
- Produces: `GET /operations/tasks/stage-roster/:stageCode` → `{ stage: {stageCode, taskCount}, roster: Array<{taskId, title, priority, status, projectId}>, summary: {total, highPriority, medium, locked} }`.

- [ ] **Step 1: Confirm Drizzle schema export names (already verified while writing this plan)**

Already confirmed by direct grep against the real schema files — no
placeholder guessing needed: `projectOperatingSetups` is exported from
`services/company/shared/db/schema/strategy.ts:277`; `tasks` and
`taskProjects` are exported from `services/company/shared/db/schema/operations.ts`
(lines 18 and 225 respectively — note the file is named `operations.ts`, not
`operating.ts`, even though the Postgres schema itself is named `operating`).
Sanity-check they're still current before Step 4 (schema files can drift):
`grep -n "export const projectOperatingSetups\|export const tasks\|export const taskProjects" services/company/shared/db/schema/strategy.ts services/company/shared/db/schema/operations.ts`

- [ ] **Step 2: Write the failing test**

```typescript
// services/company/operations/tests/task-stage-roster.test.ts
import { describe, it, expect } from "vitest";
import { listStageRosterService } from "../services/task.service";
import { createTaskService } from "../services/task.service";
import { db, schema } from "../models/db";
import { eq } from "drizzle-orm";

describe("listStageRosterService", () => {
  it("returns tasks only for projects whose selected_stage matches", async () => {
    // Seed: minimal workspace/project fixture is already available via the
    // shared test seeding helpers used by other operations tests in this
    // directory (see task.handler test setup) — reuse that same seeding
    // helper for workspaceId/projectId here instead of inserting by hand,
    // to stay consistent with existing tests in this file's sibling suite.
    const workspaceId = "test-ws-stage-roster";
    const projectId = "test-project-stage-roster";
    await db.insert(schema.projectOperatingSetups).values({
      projectId,
      workspaceId,
      status: "IN_PROGRESS",
      selectedStage: "P2",
    }).onConflictDoNothing();

    const task = await createTaskService(
      { title: "Ship pricing page", workspaceId, priority: "high" },
      undefined
    );
    await db.insert(schema.taskProjects).values({
      workspaceId,
      taskId: task.id,
      projectId,
    });

    const roster = await listStageRosterService(workspaceId, "P2");

    expect(roster.stage.stageCode).toBe("P2");
    expect(roster.roster.some((r) => r.taskId === task.id)).toBe(true);
    expect(roster.summary.total).toBe(roster.roster.length);
  });

  it("returns empty roster for a stage with no matching projects", async () => {
    const roster = await listStageRosterService("test-ws-stage-roster-empty", "P5");
    expect(roster.roster).toEqual([]);
    expect(roster.summary.total).toBe(0);
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd services/company && encore test operations/tests/task-stage-roster.test.ts`
Expected: FAIL with `listStageRosterService is not a function` / import error

- [ ] **Step 4: Implement `listStageRosterService`**

Add to `services/company/operations/services/task.service.ts` (near
`listAgentClaimableTasksService`, reusing the same `db`/`schema` imports
already at the top of that file):

```typescript
export interface StageRosterEntry {
  taskId: string;
  title: string;
  priority: string;
  status: string;
  projectId: string;
}

export interface StageRosterView {
  stage: { stageCode: string; taskCount: number };
  roster: StageRosterEntry[];
  summary: { total: number; highPriority: number; medium: number; locked: number };
}

export async function listStageRosterService(
  workspaceId: string,
  stageCode: string
): Promise<StageRosterView> {
  const projects = await db
    .select({ projectId: schema.projectOperatingSetups.projectId, status: schema.projectOperatingSetups.status })
    .from(schema.projectOperatingSetups)
    .where(
      and(
        eq(schema.projectOperatingSetups.workspaceId, workspaceId),
        eq(schema.projectOperatingSetups.selectedStage, stageCode)
      )
    );

  if (projects.length === 0) {
    return {
      stage: { stageCode, taskCount: 0 },
      roster: [],
      summary: { total: 0, highPriority: 0, medium: 0, locked: 0 },
    };
  }

  const lockedProjectIds = new Set(
    projects.filter((p) => p.status !== "IN_PROGRESS").map((p) => p.projectId)
  );
  const projectIds = projects.map((p) => p.projectId);

  const rows = await db
    .select({
      taskId: schema.tasks.id,
      title: schema.tasks.title,
      priority: schema.tasks.priority,
      status: schema.tasks.status,
      projectId: schema.taskProjects.projectId,
    })
    .from(schema.taskProjects)
    .innerJoin(schema.tasks, eq(schema.tasks.id, schema.taskProjects.taskId))
    .where(
      and(
        eq(schema.taskProjects.workspaceId, workspaceId),
        inArray(schema.taskProjects.projectId, projectIds)
      )
    );

  const roster: StageRosterEntry[] = rows.map((r) => ({
    taskId: r.taskId,
    title: r.title,
    priority: r.priority,
    status: r.status,
    projectId: r.projectId,
  }));

  return {
    stage: { stageCode, taskCount: roster.length },
    roster,
    summary: {
      total: roster.length,
      highPriority: roster.filter((r) => r.priority === "high").length,
      medium: roster.filter((r) => r.priority === "medium").length,
      // "locked" = task thuộc project chưa IN_PROGRESS — định nghĩa MVP tạm,
      // xem spec Phase 3.
      locked: roster.filter((r) => lockedProjectIds.has(r.projectId)).length,
    },
  };
}
```

Add `and`, `inArray` to the `drizzle-orm` import at the top of the file if not
already imported.

- [ ] **Step 5: Add the handler**

Add to `services/company/operations/handlers/task.handler.ts`, after
`listAgentClaimableTasks`:

```typescript
import { listStageRosterService } from "../services/task.service";

// Gọi bởi apps/cosa (GET /agent/workforce/stage-roster/{stage_code}) — cosa
// delegation, tái dùng đúng capability WGA_CAP_TASK_LIST (read-only, không
// cần capability riêng).
export const getStageRoster = api(
  { method: "GET", path: "/operations/tasks/stage-roster/:stageCode", expose: true },
  async ({
    stageCode,
    workspaceId,
    authorization,
  }: {
    stageCode: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }) => {
    resolveCosaTaskContext(authorization, {
      workspaceId,
      capabilityId: WGA_CAP_TASK_LIST,
    });
    return listStageRosterService(workspaceId, stageCode);
  }
);
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd services/company && encore test operations/tests/task-stage-roster.test.ts`
Expected: PASS (2 passed)

- [ ] **Step 7: Typecheck**

Run: `cd services/company && npm run typecheck`
Expected: no errors

- [ ] **Step 8: Commit**

```bash
git add services/company/operations/services/task.service.ts services/company/operations/handlers/task.handler.ts services/company/operations/tests/task-stage-roster.test.ts
git commit -m "feat(company): thêm GET /operations/tasks/stage-roster/:stageCode — Phase 3a workforce dashboard

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 6: apps/cosa — `GET /agent/workforce/stage-roster/{stage_code}` (Phase 3b, calls Task 5)

**Files:**
- Modify: `apps/cosa/api/workforce_schemas.py` (add `WorkforceStageRosterOut`, `WorkforceStageRosterEntryOut`)
- Modify: `apps/cosa/api/workforce_routes.py` (add route + a small Company HTTP client function)
- Test: `tests/apps/cosa/test_workforce_routes.py` (append, mocking the Company HTTP call)

**Interfaces:**
- Consumes: `mint_company_delegation` (`apps.cosa.auth.jwt`, same function used by `apps/cosa/compliance/resolver.py`), `require_internal_url("COMPANY_SERVICE_URL", ...)` (same pattern as `apps/cosa/worker/kickoff_suggestion_run.py::callback_kickoff_result`).
- Produces: `GET /agent/workforce/stage-roster/{stage_code}` → `MvpSuccess[WorkforceStageRosterOut]`.

- [ ] **Step 1: Write the failing test**

Append to `tests/apps/cosa/test_workforce_routes.py`:

```python
@pytest.mark.asyncio
async def test_stage_roster_proxies_company_and_reshapes(test_app, monkeypatch) -> None:
    async def fake_fetch_stage_roster(workspace_id: str, stage_code: str, principal: str):
        assert workspace_id == "ws_1001"
        assert stage_code == "P2"
        return {
            "stage": {"stageCode": "P2", "taskCount": 1},
            "roster": [
                {
                    "taskId": "t1",
                    "title": "Ship pricing page",
                    "priority": "high",
                    "status": "todo",
                    "projectId": "proj_1",
                }
            ],
            "summary": {"total": 1, "highPriority": 1, "medium": 0, "locked": 0},
        }

    import apps.cosa.api.workforce_routes as workforce_routes_mod

    monkeypatch.setattr(workforce_routes_mod, "_fetch_company_stage_roster", fake_fetch_stage_roster)

    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        res = await client.get("/agent/workforce/stage-roster/P2")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["stage"]["stage_code"] == "P2"
        assert data["roster"][0]["task_id"] == "t1"
        assert data["summary"]["high_priority"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/test_workforce_routes.py -k stage_roster -v`
Expected: FAIL — `AttributeError: module 'apps.cosa.api.workforce_routes' has no attribute '_fetch_company_stage_roster'` (or 404)

- [ ] **Step 3: Add schemas**

In `apps/cosa/api/workforce_schemas.py`, add after `WorkforceExceptionListOut`:

```python
class WorkforceStageRosterEntryOut(BaseModel):
    task_id: str
    title: str
    priority: str
    status: str
    project_id: str


class WorkforceStageRosterStageOut(BaseModel):
    stage_code: str
    task_count: int


class WorkforceStageRosterSummaryOut(BaseModel):
    total: int
    high_priority: int
    medium: int
    locked: int


class WorkforceStageRosterOut(BaseModel):
    stage: WorkforceStageRosterStageOut
    roster: list[WorkforceStageRosterEntryOut]
    summary: WorkforceStageRosterSummaryOut
```

- [ ] **Step 4: Add the Company HTTP client function + route**

In `apps/cosa/api/workforce_routes.py`, add near the top-level helpers (after
`_get_workforce_repo`):

```python
async def _fetch_company_stage_roster(
    workspace_id: str, stage_code: str, principal: str
) -> dict:
    import httpx

    from apps.cosa.auth.jwt import mint_company_delegation
    from apps.cosa.config.service_identity import require_internal_url

    company_base_url = require_internal_url(
        "COMPANY_SERVICE_URL", purpose="stage roster proxy", default_dev="http://127.0.0.1:4000"
    )
    token = mint_company_delegation(
        sub=principal,
        workspace_id=workspace_id,
        run_id=f"stage_roster_{workspace_id}_{stage_code}",
        capability_ids=["operations.task.list"],
    )
    url = f"{company_base_url}/operations/tasks/stage-roster/{stage_code}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            url,
            headers={"Authorization": f"Bearer {token}", "X-Workspace-Id": workspace_id},
        )
        resp.raise_for_status()
        return resp.json()
```

And the route, after `list_exceptions`:

```python
@router.get("/stage-roster/{stage_code}")
async def get_stage_roster(
    stage_code: str,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[WorkforceStageRosterOut]:
    raw = await _fetch_company_stage_roster(
        identity.workspace_id, stage_code, identity.principal_id
    )
    out = WorkforceStageRosterOut(
        stage=WorkforceStageRosterStageOut(
            stage_code=raw["stage"]["stageCode"], task_count=raw["stage"]["taskCount"]
        ),
        roster=[
            WorkforceStageRosterEntryOut(
                task_id=r["taskId"],
                title=r["title"],
                priority=r["priority"],
                status=r["status"],
                project_id=r["projectId"],
            )
            for r in raw["roster"]
        ],
        summary=WorkforceStageRosterSummaryOut(
            total=raw["summary"]["total"],
            high_priority=raw["summary"]["highPriority"],
            medium=raw["summary"]["medium"],
            locked=raw["summary"]["locked"],
        ),
    )
    return mvp_item(out, [MvpSourceRef(kind="company_db", ref="operating.tasks")])
```

Add the 4 new schema classes to the import block at the top of the file.

- [ ] **Step 5: Run test to verify it passes**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/test_workforce_routes.py -k stage_roster -v`
Expected: PASS (1 passed)

- [ ] **Step 6: Commit**

```bash
git add apps/cosa/api/workforce_schemas.py apps/cosa/api/workforce_routes.py tests/apps/cosa/test_workforce_routes.py
git commit -m "feat(cosa): thêm GET /agent/workforce/stage-roster/{stage_code} — Phase 3b workforce dashboard

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 7: Backend — `GET /agent/workforce/dashboard-summary` (Phase 4: aggregator)

**Files:**
- Modify: `apps/cosa/api/workforce_schemas.py` (add `WorkforceDashboardSummaryOut`)
- Modify: `apps/cosa/api/workforce_routes.py` (add route)
- Test: `tests/apps/cosa/test_workforce_routes.py` (append)

**Interfaces:**
- Consumes: `get_roster` (Task 2), `list_work_products` (Task 3), `list_exceptions` (Task 4) logic — call the underlying data directly (not HTTP self-calls) to avoid a network round-trip against itself; `repo.list_approvals` (existing, used by `list_approvals` route) and `repo.list_assignments` (existing).

- [ ] **Step 1: Write the failing test**

Append to `tests/apps/cosa/test_workforce_routes.py`:

```python
@pytest.mark.asyncio
async def test_dashboard_summary_aggregates_existing_counts(test_app) -> None:
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        await client.post("/agent/workforce/assignments", json={"functional_key": "campaign_planner"})

        res = await client.get("/agent/workforce/dashboard-summary")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["roster_total"] == 6
        assert data["roster_active"] == 1
        assert data["open_exceptions"] == 0
        assert data["pending_approvals"] == 0
        assert data["work_products_total"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/test_workforce_routes.py -k dashboard_summary -v`
Expected: FAIL with 404

- [ ] **Step 3: Add schema**

In `apps/cosa/api/workforce_schemas.py`, add after `WorkforceStageRosterOut`:

```python
class WorkforceDashboardSummaryOut(BaseModel):
    roster_total: int
    roster_active: int
    open_exceptions: int
    pending_approvals: int
    work_products_total: int
```

- [ ] **Step 4: Add the route**

In `apps/cosa/api/workforce_routes.py`, add after `get_stage_roster`. This
calls the same repository methods the other Phase routes use directly (not
an HTTP self-call), to stay a pure in-process aggregator per the spec:

```python
@router.get("/dashboard-summary")
async def get_dashboard_summary(
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[WorkforceDashboardSummaryOut]:
    """Aggregator mỏng — không logic nghiệp vụ mới, chỉ gộp số đã có ở
    /roster, /artifacts, /exceptions, /approvals."""
    plane = _get_plane(request)
    repo = _get_workforce_repo(request)

    assignments = await repo.list_assignments(identity.workspace_id, status="ACTIVE")
    roster_active = len({a.functional_key for a in assignments})

    approvals = await repo.list_approvals(identity.workspace_id, status="PENDING")

    from agent.contracts.run import RunStatus

    runs = await plane.repository.list_runs(identity.workspace_id, limit=200)
    open_exceptions = len([r for r in runs if r.status == RunStatus.FAILED])

    work_products_total = 0
    if plane.artifact_repository is not None:
        work_products_total = len(
            await plane.artifact_repository.list_for_workspace(identity.workspace_id, limit=200)
        )

    out = WorkforceDashboardSummaryOut(
        roster_total=len(FUNCTIONAL_AGENT_CATALOG),
        roster_active=roster_active,
        open_exceptions=open_exceptions,
        pending_approvals=len(approvals),
        work_products_total=work_products_total,
    )
    return mvp_item(out, [MvpSourceRef(kind="agent_db", ref="agent.workforce_assignments")])
```

Add `WorkforceDashboardSummaryOut` to the schema import block. Confirm
`repo.list_approvals(workspace_id, status=...)` is the exact existing method
name/signature by checking the `list_approvals` route above in this same
file before writing this call — reuse it verbatim, don't guess a new
signature.

- [ ] **Step 5: Run test to verify it passes**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/test_workforce_routes.py -k dashboard_summary -v`
Expected: PASS (1 passed)

- [ ] **Step 6: Commit**

```bash
git add apps/cosa/api/workforce_schemas.py apps/cosa/api/workforce_routes.py tests/apps/cosa/test_workforce_routes.py
git commit -m "feat(cosa): thêm GET /agent/workforce/dashboard-summary — Phase 4 workforce dashboard

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 8: Contracts — register all 5 endpoints in `mvp-surface.json`

**Files:**
- Modify: `shared/contracts/mvp-surface.json`
- Generated (do not hand-edit): `frontend/lib/core/network/mvp_endpoints.g.dart`, `apps/cosa/api/mvp_contracts_generated.py`, `services/company/shared/contracts/mvp-surface.generated.ts`

**Interfaces:**
- Produces: 5 new `MvpEndpoint` enum values in `mvp_endpoints.g.dart` — `workforceRosterList`, `workforceWorkProductList`, `workforceExceptionList`, `workforceStageRosterGet`, `workforceDashboardSummaryGet` (exact casing: `id` uses dot.case, generator derives the Dart enum member name from `id` the same way it did for `workforce.approval.list` → `workforceApprovalList` — follow that same casing rule).

- [ ] **Step 1: Add the 5 entries to `shared/contracts/mvp-surface.json`**

Insert alphabetically among the existing `workforce.*` entries (find the
`"id": "workforce.approval.list"` block and the others via
`grep -n '"id": "workforce\.' shared/contracts/mvp-surface.json` to place
each new entry in the right alphabetical slot, matching the file's existing
ordering convention):

```json
    {
      "id": "workforce.dashboard_summary.get",
      "enabled": true,
      "owner": "agent-platform",
      "plane": "agent",
      "method": "GET",
      "path": "/agent/workforce/dashboard-summary",
      "schema": "workforce.dashboard_summary.get.v1",
      "source_kind": "agent_db",
      "requires_workspace": true,
      "frontend_symbol": "WorkforceMvpService.getDashboardSummary",
      "backend_test": "tests/apps/cosa/test_workforce_routes.py",
      "flutter_test": "frontend/test/modules/workforce/services/workforce_mvp_service_test.dart",
      "integration_test": "tests/e2e/test_mvp_workforce_http.py"
    },
    {
      "id": "workforce.exception.list",
      "enabled": true,
      "owner": "agent-platform",
      "plane": "agent",
      "method": "GET",
      "path": "/agent/workforce/exceptions",
      "schema": "workforce.exception.list.v1",
      "source_kind": "agent_db",
      "requires_workspace": true,
      "frontend_symbol": "WorkforceMvpService.listExceptions",
      "backend_test": "tests/apps/cosa/test_workforce_routes.py",
      "flutter_test": "frontend/test/modules/workforce/services/workforce_mvp_service_test.dart",
      "integration_test": "tests/e2e/test_mvp_workforce_http.py"
    },
    {
      "id": "workforce.roster.list",
      "enabled": true,
      "owner": "agent-platform",
      "plane": "agent",
      "method": "GET",
      "path": "/agent/workforce/roster",
      "schema": "workforce.roster.list.v1",
      "source_kind": "agent_db",
      "requires_workspace": true,
      "frontend_symbol": "WorkforceMvpService.listRoster",
      "backend_test": "tests/apps/cosa/test_workforce_routes.py",
      "flutter_test": "frontend/test/modules/workforce/services/workforce_mvp_service_test.dart",
      "integration_test": "tests/e2e/test_mvp_workforce_http.py"
    },
    {
      "id": "workforce.stage_roster.get",
      "enabled": true,
      "owner": "agent-platform",
      "plane": "agent",
      "method": "GET",
      "path": "/agent/workforce/stage-roster/:stageCode",
      "schema": "workforce.stage_roster.get.v1",
      "source_kind": "agent_db",
      "requires_workspace": true,
      "frontend_symbol": "WorkforceMvpService.getStageRoster",
      "backend_test": "tests/apps/cosa/test_workforce_routes.py",
      "flutter_test": "frontend/test/modules/workforce/services/workforce_mvp_service_test.dart",
      "integration_test": "tests/e2e/test_mvp_workforce_http.py"
    },
    {
      "id": "workforce.work_product.list",
      "enabled": true,
      "owner": "agent-platform",
      "plane": "agent",
      "method": "GET",
      "path": "/agent/workforce/artifacts",
      "schema": "workforce.work_product.list.v1",
      "source_kind": "agent_db",
      "requires_workspace": true,
      "frontend_symbol": "WorkforceMvpService.listWorkProducts",
      "backend_test": "tests/apps/cosa/test_workforce_routes.py",
      "flutter_test": "frontend/test/modules/workforce/services/workforce_mvp_service_test.dart",
      "integration_test": "tests/e2e/test_mvp_workforce_http.py"
    },
```

Before writing this JSON in place, run
`grep -n '"path": ":stageCode"' shared/contracts/mvp-surface.json` for a
sibling entry that has a `:param` path segment (e.g.
`workforce.approval.decision`'s `/agent/workforce/approvals/:approvalId/decision`)
to confirm the exact path-param syntax the generator expects — reuse that
exact syntax for `:stageCode` rather than guessing.

- [ ] **Step 2: Regenerate**

Run: `make mvp-contracts-gen`

- [ ] **Step 3: Verify generation is clean**

Run: `make mvp-contracts-check`
Expected: no diff / exit 0

Run: `python scripts/mvp_surface_check.py --check`
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add shared/contracts/mvp-surface.json frontend/lib/core/network/mvp_endpoints.g.dart apps/cosa/api/mvp_contracts_generated.py services/company/shared/contracts/mvp-surface.generated.ts
git commit -m "feat(contracts): đăng ký 5 endpoint workforce dashboard mới vào mvp-surface.json

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 9: Frontend — Dart models for the 5 new endpoints

**Files:**
- Modify: `frontend/lib/modules/workforce/models/workforce_mvp_models.dart`
- Test: `frontend/test/modules/workforce/models/workforce_mvp_models_test.dart` (create)

**Interfaces:**
- Produces: `WorkforceRosterEntry.fromJson`, `WorkforceWorkProduct.fromJson`, `WorkforceException.fromJson`, `WorkforceExceptionSummary.fromJson`, `WorkforceStageRoster.fromJson`, `WorkforceDashboardSummary.fromJson` — all `@immutable` classes following the exact style of `WorkforceRun` in the same file (snake_case JSON keys, `as String? ?? ''` / `as int?` null-safety pattern, `DateTime.tryParse`).

- [ ] **Step 1: Write the failing test**

```dart
// frontend/test/modules/workforce/models/workforce_mvp_models_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/workforce/models/workforce_mvp_models.dart';

void main() {
  test('WorkforceRosterEntry.fromJson parses backend snake_case fields', () {
    final entry = WorkforceRosterEntry.fromJson({
      'id': 1,
      'key': 'cashflow_planner',
      'name': 'Cashflow Planner',
      'role_title': 'Đọc giao dịch, dự báo dòng tiền...',
      'department': 'Finance',
      'agent_type': 'specialist',
      'default_model_profile': 'reasoning',
      'risk_level': 2,
      'status': 'available',
      'enabled': true,
    });
    expect(entry.key, 'cashflow_planner');
    expect(entry.department, 'Finance');
    expect(entry.status, 'available');
    expect(entry.enabled, isTrue);
  });

  test('WorkforceWorkProduct.fromJson parses backend snake_case fields', () {
    final product = WorkforceWorkProduct.fromJson({
      'id': 'art_1',
      'title': 'Market brief Q1',
      'product_type': 'text/markdown',
      'status': 'READY',
      'author_agent_key': 'functional.market_research_specialist',
      'object_ref': 'object://brief-q1',
      'created_at': '2026-09-04T12:00:00.000Z',
    });
    expect(product.title, 'Market brief Q1');
    expect(product.objectRef, 'object://brief-q1');
  });

  test('WorkforceExceptionSummary.fromJson parses nested escalations list', () {
    final summary = WorkforceExceptionSummary.fromJson({
      'total': 1,
      'founder_gate_count': 0,
      'lead_notify_count': 1,
      'has_critical': false,
      'escalations': [
        {
          'id': 'run_1',
          'exception_type': 'run_failed',
          'tier': 'LEAD_NOTIFY',
          'status': 'OPEN',
          'agent_key': 'functional.cashflow_planner',
          'created_at': '2026-09-04T12:00:00.000Z',
        },
      ],
    });
    expect(summary.total, 1);
    expect(summary.escalations.single.id, 'run_1');
    expect(summary.escalations.single.tier, 'LEAD_NOTIFY');
  });

  test('WorkforceStageRoster.fromJson parses nested stage/roster/summary', () {
    final roster = WorkforceStageRoster.fromJson({
      'stage': {'stage_code': 'P2', 'task_count': 1},
      'roster': [
        {'task_id': 't1', 'title': 'Ship pricing page', 'priority': 'high', 'status': 'todo', 'project_id': 'proj_1'},
      ],
      'summary': {'total': 1, 'high_priority': 1, 'medium': 0, 'locked': 0},
    });
    expect(roster.stage.stageCode, 'P2');
    expect(roster.roster.single.taskId, 't1');
    expect(roster.summary.highPriority, 1);
  });

  test('WorkforceDashboardSummary.fromJson parses flat counts', () {
    final summary = WorkforceDashboardSummary.fromJson({
      'roster_total': 6,
      'roster_active': 1,
      'open_exceptions': 0,
      'pending_approvals': 0,
      'work_products_total': 0,
    });
    expect(summary.rosterTotal, 6);
    expect(summary.rosterActive, 1);
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && flutter test test/modules/workforce/models/workforce_mvp_models_test.dart`
Expected: FAIL — classes don't exist

- [ ] **Step 3: Add the models**

Append to `frontend/lib/modules/workforce/models/workforce_mvp_models.dart`:

```dart
@immutable
class WorkforceRosterEntry {
  final int id;
  final String key;
  final String name;
  final String roleTitle;
  final String department;
  final String agentType;
  final String defaultModelProfile;
  final int riskLevel;
  final String status;
  final bool enabled;

  const WorkforceRosterEntry({
    required this.id,
    required this.key,
    required this.name,
    required this.roleTitle,
    required this.department,
    required this.agentType,
    required this.defaultModelProfile,
    required this.riskLevel,
    required this.status,
    required this.enabled,
  });

  factory WorkforceRosterEntry.fromJson(Map<String, dynamic> json) {
    return WorkforceRosterEntry(
      id: json['id'] as int? ?? 0,
      key: json['key'] as String? ?? '',
      name: json['name'] as String? ?? '',
      roleTitle: json['role_title'] as String? ?? '',
      department: json['department'] as String? ?? '',
      agentType: json['agent_type'] as String? ?? '',
      defaultModelProfile: json['default_model_profile'] as String? ?? '',
      riskLevel: json['risk_level'] as int? ?? 0,
      status: json['status'] as String? ?? '',
      enabled: json['enabled'] as bool? ?? false,
    );
  }
}

@immutable
class WorkforceWorkProduct {
  final String id;
  final String title;
  final String productType;
  final String status;
  final String authorAgentKey;
  final String objectRef;
  final DateTime createdAt;

  const WorkforceWorkProduct({
    required this.id,
    required this.title,
    required this.productType,
    required this.status,
    required this.authorAgentKey,
    required this.objectRef,
    required this.createdAt,
  });

  factory WorkforceWorkProduct.fromJson(Map<String, dynamic> json) {
    return WorkforceWorkProduct(
      id: json['id'] as String? ?? '',
      title: json['title'] as String? ?? '',
      productType: json['product_type'] as String? ?? '',
      status: json['status'] as String? ?? '',
      authorAgentKey: json['author_agent_key'] as String? ?? '',
      objectRef: json['object_ref'] as String? ?? '',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

@immutable
class WorkforceException {
  final String id;
  final String exceptionType;
  final String tier;
  final String status;
  final String agentKey;
  final DateTime createdAt;

  const WorkforceException({
    required this.id,
    required this.exceptionType,
    required this.tier,
    required this.status,
    required this.agentKey,
    required this.createdAt,
  });

  factory WorkforceException.fromJson(Map<String, dynamic> json) {
    return WorkforceException(
      id: json['id'] as String? ?? '',
      exceptionType: json['exception_type'] as String? ?? '',
      tier: json['tier'] as String? ?? '',
      status: json['status'] as String? ?? '',
      agentKey: json['agent_key'] as String? ?? '',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

@immutable
class WorkforceExceptionSummary {
  final int total;
  final int founderGateCount;
  final int leadNotifyCount;
  final bool hasCritical;
  final List<WorkforceException> escalations;

  const WorkforceExceptionSummary({
    required this.total,
    required this.founderGateCount,
    required this.leadNotifyCount,
    required this.hasCritical,
    required this.escalations,
  });

  factory WorkforceExceptionSummary.fromJson(Map<String, dynamic> json) {
    final rawList = json['escalations'] as List? ?? const [];
    return WorkforceExceptionSummary(
      total: json['total'] as int? ?? 0,
      founderGateCount: json['founder_gate_count'] as int? ?? 0,
      leadNotifyCount: json['lead_notify_count'] as int? ?? 0,
      hasCritical: json['has_critical'] as bool? ?? false,
      escalations: rawList
          .whereType<Map<String, dynamic>>()
          .map(WorkforceException.fromJson)
          .toList(),
    );
  }
}

@immutable
class WorkforceStageRosterTask {
  final String taskId;
  final String title;
  final String priority;
  final String status;
  final String projectId;

  const WorkforceStageRosterTask({
    required this.taskId,
    required this.title,
    required this.priority,
    required this.status,
    required this.projectId,
  });

  factory WorkforceStageRosterTask.fromJson(Map<String, dynamic> json) {
    return WorkforceStageRosterTask(
      taskId: json['task_id'] as String? ?? '',
      title: json['title'] as String? ?? '',
      priority: json['priority'] as String? ?? '',
      status: json['status'] as String? ?? '',
      projectId: json['project_id'] as String? ?? '',
    );
  }
}

@immutable
class WorkforceStageRosterSummary {
  final int total;
  final int highPriority;
  final int medium;
  final int locked;

  const WorkforceStageRosterSummary({
    required this.total,
    required this.highPriority,
    required this.medium,
    required this.locked,
  });

  factory WorkforceStageRosterSummary.fromJson(Map<String, dynamic> json) {
    return WorkforceStageRosterSummary(
      total: json['total'] as int? ?? 0,
      highPriority: json['high_priority'] as int? ?? 0,
      medium: json['medium'] as int? ?? 0,
      locked: json['locked'] as int? ?? 0,
    );
  }
}

@immutable
class WorkforceStageRosterStage {
  final String stageCode;
  final int taskCount;

  const WorkforceStageRosterStage({required this.stageCode, required this.taskCount});

  factory WorkforceStageRosterStage.fromJson(Map<String, dynamic> json) {
    return WorkforceStageRosterStage(
      stageCode: json['stage_code'] as String? ?? '',
      taskCount: json['task_count'] as int? ?? 0,
    );
  }
}

@immutable
class WorkforceStageRoster {
  final WorkforceStageRosterStage stage;
  final List<WorkforceStageRosterTask> roster;
  final WorkforceStageRosterSummary summary;

  const WorkforceStageRoster({required this.stage, required this.roster, required this.summary});

  factory WorkforceStageRoster.fromJson(Map<String, dynamic> json) {
    final rawRoster = json['roster'] as List? ?? const [];
    return WorkforceStageRoster(
      stage: WorkforceStageRosterStage.fromJson(json['stage'] as Map<String, dynamic>? ?? const {}),
      roster: rawRoster
          .whereType<Map<String, dynamic>>()
          .map(WorkforceStageRosterTask.fromJson)
          .toList(),
      summary: WorkforceStageRosterSummary.fromJson(json['summary'] as Map<String, dynamic>? ?? const {}),
    );
  }
}

@immutable
class WorkforceDashboardSummary {
  final int rosterTotal;
  final int rosterActive;
  final int openExceptions;
  final int pendingApprovals;
  final int workProductsTotal;

  const WorkforceDashboardSummary({
    required this.rosterTotal,
    required this.rosterActive,
    required this.openExceptions,
    required this.pendingApprovals,
    required this.workProductsTotal,
  });

  factory WorkforceDashboardSummary.fromJson(Map<String, dynamic> json) {
    return WorkforceDashboardSummary(
      rosterTotal: json['roster_total'] as int? ?? 0,
      rosterActive: json['roster_active'] as int? ?? 0,
      openExceptions: json['open_exceptions'] as int? ?? 0,
      pendingApprovals: json['pending_approvals'] as int? ?? 0,
      workProductsTotal: json['work_products_total'] as int? ?? 0,
    );
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && flutter test test/modules/workforce/models/workforce_mvp_models_test.dart`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/modules/workforce/models/workforce_mvp_models.dart frontend/test/modules/workforce/models/workforce_mvp_models_test.dart
git commit -m "feat(frontend): thêm model cho 5 endpoint workforce dashboard mới

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 10: Frontend — `WorkforceMvpService` methods for the 5 new endpoints

**Files:**
- Modify: `frontend/lib/modules/workforce/services/workforce_mvp_service.dart`
- Test: `frontend/test/modules/workforce/services/workforce_mvp_service_test.dart` (create)

**Interfaces:**
- Consumes: `MvpEndpoint.workforceRosterList`, `.workforceWorkProductList`, `.workforceExceptionList`, `.workforceStageRosterGet`, `.workforceDashboardSummaryGet` (generated in Task 8 — confirm exact enum member names by reading `mvp_endpoints.g.dart` after Task 8's regeneration, since the generator's casing rule determines the final name).
- Produces: `listRoster()`, `listWorkProducts()`, `listExceptions()`, `getStageRoster(stageCode)`, `getDashboardSummary()` — all returning `ApiResult<T>`.

- [ ] **Step 1: Write the failing test**

```dart
// frontend/test/modules/workforce/services/workforce_mvp_service_test.dart
import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/modules/workforce/services/workforce_mvp_service.dart';

void main() {
  test('listRoster calls /agent/workforce/roster and decodes entries', () async {
    final mockHttp = MockClient((request) async {
      expect(request.url.path, '/agent/workforce/roster');
      return http.Response(
        jsonEncode({
          'data': [
            {
              'id': 1, 'key': 'cashflow_planner', 'name': 'Cashflow Planner',
              'role_title': 'x', 'department': 'Finance', 'agent_type': 'specialist',
              'default_model_profile': 'reasoning', 'risk_level': 2,
              'status': 'available', 'enabled': true,
            },
          ],
          'meta': {'data_state': 'populated', 'observed_at': '2026-09-04T12:00:00.000Z', 'sources': []},
        }),
        200,
      );
    });
    final service = WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp));

    final result = await service.listRoster();

    expect(result, isA<ApiSuccess<List<WorkforceRosterEntry>>>());
    final data = (result as ApiSuccess<List<WorkforceRosterEntry>>).data;
    expect(data.single.key, 'cashflow_planner');
  });

  test('getStageRoster calls /agent/workforce/stage-roster/:stageCode with path param', () async {
    final mockHttp = MockClient((request) async {
      expect(request.url.path, '/agent/workforce/stage-roster/P2');
      return http.Response(
        jsonEncode({
          'data': {
            'stage': {'stage_code': 'P2', 'task_count': 0},
            'roster': [],
            'summary': {'total': 0, 'high_priority': 0, 'medium': 0, 'locked': 0},
          },
          'meta': {'data_state': 'empty', 'observed_at': '2026-09-04T12:00:00.000Z', 'sources': []},
        }),
        200,
      );
    });
    final service = WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp));

    final result = await service.getStageRoster('P2');

    expect(result, isA<ApiSuccess<WorkforceStageRoster>>());
  });

  test('listExceptions propagates a 500 as ApiFailure, never a fabricated empty summary', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(jsonEncode({'detail': 'boom'}), 500);
    });
    final service = WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp));

    final result = await service.listExceptions();

    expect(result, isA<ApiFailure<WorkforceExceptionSummary>>());
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && flutter test test/modules/workforce/services/workforce_mvp_service_test.dart`
Expected: FAIL — methods don't exist

- [ ] **Step 3: Add the methods**

Append to the `WorkforceMvpService` class in
`frontend/lib/modules/workforce/services/workforce_mvp_service.dart` (before
the closing `}`), importing the new model classes at the top of the file
(they already live in `workforce_mvp_models.dart`, already imported):

```dart
  Future<ApiResult<List<WorkforceRosterEntry>>> listRoster() async {
    return _client.request<List<WorkforceRosterEntry>>(
      MvpEndpoint.workforceRosterList,
      decode: (json) => _asList(json).map(WorkforceRosterEntry.fromJson).toList(),
    );
  }

  Future<ApiResult<List<WorkforceWorkProduct>>> listWorkProducts() async {
    return _client.request<List<WorkforceWorkProduct>>(
      MvpEndpoint.workforceWorkProductList,
      decode: (json) => _asList(json).map(WorkforceWorkProduct.fromJson).toList(),
    );
  }

  Future<ApiResult<WorkforceExceptionSummary>> listExceptions() async {
    return _client.request<WorkforceExceptionSummary>(
      MvpEndpoint.workforceExceptionList,
      decode: (json) => WorkforceExceptionSummary.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<WorkforceStageRoster>> getStageRoster(String stageCode) async {
    return _client.request<WorkforceStageRoster>(
      MvpEndpoint.workforceStageRosterGet,
      pathParams: {'stageCode': stageCode},
      decode: (json) => WorkforceStageRoster.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<WorkforceDashboardSummary>> getDashboardSummary() async {
    return _client.request<WorkforceDashboardSummary>(
      MvpEndpoint.workforceDashboardSummaryGet,
      decode: (json) => WorkforceDashboardSummary.fromJson(json as Map<String, dynamic>),
    );
  }
```

If the generated enum member names from Task 8 differ from
`workforceRosterList` / `workforceWorkProductList` / `workforceExceptionList` /
`workforceStageRosterGet` / `workforceDashboardSummaryGet`, use the actual
generated names — check `frontend/lib/core/network/mvp_endpoints.g.dart`
after running `make mvp-contracts-gen` in Task 8, don't guess here.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && flutter test test/modules/workforce/services/workforce_mvp_service_test.dart`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/modules/workforce/services/workforce_mvp_service.dart frontend/test/modules/workforce/services/workforce_mvp_service_test.dart
git commit -m "feat(frontend): thêm WorkforceMvpService method cho 5 endpoint workforce dashboard mới

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 11: Frontend — migrate `AgentPlatformService` off raw `/workforce/...` calls

**Files:**
- Modify: `frontend/lib/modules/agents/services/agent_platform_service.dart`
- Test: `frontend/test/modules/agents/agent_platform_service_test.dart` (append)

**Interfaces:**
- Consumes: `WorkforceMvpService.listRoster/listWorkProducts/listExceptions/getStageRoster/getDashboardSummary` (Task 10).
- Produces: `getDashboardSummary()`, `listAgents()`, `listWorkProducts()`, `getStageRoster(stageCode)`, `listEscalations({status})` on `AgentPlatformService` now delegate to `_workforceMvpService`, keeping their existing external signatures (`Map<String, dynamic>?` / `List<Map<String, dynamic>>` / etc.) so `hub_control_plane_mixin.dart` call sites don't need to change — this mirrors exactly how Task 7 migrated `listApprovals`/`getOrgChart` (kept old signature, changed internals only) EXCEPT `listEscalations`, which must now return real data so its `resolveEscalation` caller can be told there's nothing to resolve (see Task 12).

- [ ] **Step 1: Write the failing test**

Append a new group to `frontend/test/modules/agents/agent_platform_service_test.dart`:

```dart
  group('AgentPlatformService — canonical workforce dashboard gaps (2026-09-04)', () {
    test('getDashboardSummary calls the canonical /agent/workforce/dashboard-summary path', () async {
      final mockHttp = MockClient((request) async {
        expect(request.url.path, '/agent/workforce/dashboard-summary');
        return http.Response(
          jsonEncode({
            'data': {
              'roster_total': 6, 'roster_active': 1, 'open_exceptions': 0,
              'pending_approvals': 0, 'work_products_total': 0,
            },
            'meta': {'data_state': 'populated', 'observed_at': '2026-09-04T12:00:00.000Z', 'sources': []},
          }),
          200,
        );
      });
      final service = AgentPlatformService(
        workforceMvpService: WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp)),
      );

      final result = await service.getDashboardSummary();

      expect(result, isNotNull);
      expect(result!['roster_total'], 6);
    });

    test('listAgents calls the canonical /agent/workforce/roster path, not /workforce/agents', () async {
      final mockHttp = MockClient((request) async {
        expect(request.url.path, '/agent/workforce/roster');
        return http.Response(
          jsonEncode({
            'data': [
              {
                'id': 1, 'key': 'cashflow_planner', 'name': 'Cashflow Planner',
                'role_title': 'x', 'department': 'Finance', 'agent_type': 'specialist',
                'default_model_profile': 'reasoning', 'risk_level': 2,
                'status': 'available', 'enabled': true,
              },
            ],
            'meta': {'data_state': 'populated', 'observed_at': '2026-09-04T12:00:00.000Z', 'sources': []},
          }),
          200,
        );
      });
      final service = AgentPlatformService(
        workforceMvpService: WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp)),
      );

      final result = await service.listAgents();

      expect(result.single['key'], 'cashflow_planner');
      expect(result.single['department'], 'Finance');
    });

    test('listEscalations calls the canonical /agent/workforce/exceptions path', () async {
      final mockHttp = MockClient((request) async {
        expect(request.url.path, '/agent/workforce/exceptions');
        return http.Response(
          jsonEncode({
            'data': {
              'total': 0, 'founder_gate_count': 0, 'lead_notify_count': 0,
              'has_critical': false, 'escalations': [],
            },
            'meta': {'data_state': 'empty', 'observed_at': '2026-09-04T12:00:00.000Z', 'sources': []},
          }),
          200,
        );
      });
      final service = AgentPlatformService(
        workforceMvpService: WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp)),
      );

      final result = await service.listEscalations();

      expect(result['total'], 0);
      expect(result['escalations'], isEmpty);
    });
  });
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && flutter test test/modules/agents/agent_platform_service_test.dart -N "workforce dashboard gaps"`
Expected: FAIL — paths still hit `/workforce/dashboard-summary` etc. (old code)

- [ ] **Step 3: Rewrite the 5 methods on `AgentPlatformService`**

In `frontend/lib/modules/agents/services/agent_platform_service.dart`,
replace the bodies of `getDashboardSummary`, `listAgents`, `getStageRoster`,
`listWorkProducts`, and `listEscalations` (find each by its current
`ApiClient.get('/workforce/...')` call) with:

```dart
  Future<Map<String, dynamic>?> getDashboardSummary() async {
    final result = await _workforceMvpService.getDashboardSummary();
    return result.when(
      success: (data, _) => {
        'roster_total': data.rosterTotal,
        'roster_active': data.rosterActive,
        'open_exceptions': data.openExceptions,
        'pending_approvals': data.pendingApprovals,
        'work_products_total': data.workProductsTotal,
      },
      failure: (failure) {
        debugPrint('[AgentPlatformService] getDashboardSummary failed: ${failure.message}');
        return null;
      },
    );
  }

  Future<List<Map<String, dynamic>>> listAgents({String? department}) async {
    final result = await _workforceMvpService.listRoster();
    return result.when(
      success: (data, _) {
        final filtered = department == null
            ? data
            : data.where((e) => e.department == department).toList();
        return filtered
            .map((e) => {
                  'id': e.id, 'key': e.key, 'name': e.name, 'role_title': e.roleTitle,
                  'department': e.department, 'agent_type': e.agentType,
                  'default_model_profile': e.defaultModelProfile, 'risk_level': e.riskLevel,
                  'status': e.status, 'enabled': e.enabled,
                })
            .toList();
      },
      failure: (failure) {
        debugPrint('[AgentPlatformService] listAgents error: ${failure.message}');
        return default12Agents;
      },
    );
  }

  Future<Map<String, dynamic>?> getStageRoster(String stageCode) async {
    final result = await _workforceMvpService.getStageRoster(stageCode);
    return result.when(
      success: (data, _) => {
        'stage': {'stage_code': data.stage.stageCode, 'task_count': data.stage.taskCount},
        'roster': data.roster
            .map((t) => {
                  'task_id': t.taskId, 'title': t.title, 'priority': t.priority,
                  'status': t.status, 'project_id': t.projectId,
                })
            .toList(),
        'summary': {
          'total': data.summary.total, 'high_priority': data.summary.highPriority,
          'medium': data.summary.medium, 'locked': data.summary.locked,
        },
      },
      failure: (failure) {
        debugPrint('[AgentPlatformService] Error loading stage roster: ${failure.message}');
        return null;
      },
    );
  }

  Future<List<Map<String, dynamic>>> listWorkProducts() async {
    final result = await _workforceMvpService.listWorkProducts();
    return result.when(
      success: (data, _) => data
          .map((p) => {
                'id': p.id, 'title': p.title, 'product_type': p.productType,
                'status': p.status, 'author_agent_key': p.authorAgentKey,
                'object_ref': p.objectRef,
              })
          .toList(),
      failure: (failure) {
        debugPrint('[AgentPlatformService] Error loading work products: ${failure.message}');
        return [];
      },
    );
  }

  // `status`/`exceptionType`/`tier`/`limit` kept on this method's own
  // signature (call sites in hub_control_plane_mixin.dart pass `status:
  // 'OPEN'` and must keep compiling) but NOT forwarded to
  // `_workforceMvpService.listExceptions()` anymore — the backend route has
  // no filter to honor yet (pre-flight decision, 2026-09-04; see spec Phase
  // 5 / Global Constraints). Every returned item is always effectively
  // "OPEN" today.
  Future<Map<String, dynamic>> listEscalations({
    String? status = 'OPEN',
    String? exceptionType,
    String? tier,
    int limit = 50,
  }) async {
    final result = await _workforceMvpService.listExceptions();
    return result.when(
      success: (data, _) => {
        'total': data.total,
        'founder_gate_count': data.founderGateCount,
        'lead_notify_count': data.leadNotifyCount,
        'has_critical': data.hasCritical,
        'escalations': data.escalations
            .map((e) => {
                  'id': e.id, 'exception_type': e.exceptionType, 'tier': e.tier,
                  'status': e.status, 'agent_key': e.agentKey,
                })
            .toList(),
      },
      failure: (failure) {
        debugPrint('[AgentPlatformService] listEscalations failed: ${failure.message}');
        return {
          'total': 0, 'founder_gate_count': 0, 'lead_notify_count': 0,
          'has_critical': false, 'escalations': [],
        };
      },
    );
  }
```

Note `listEscalations`'s `id` field changes type from the old fake int ids to
a real string `run_id` — check `hub_control_plane_mixin.dart`'s
`openEscalations.removeWhere((e) => (e['id'] as int?) == escalationId)` (in
`resolveEscalation`) and `resolveEscalation(int escalationId, ...)`'s
signature; Task 12 changes both to `String` to match. Don't fix that here —
Task 11 only changes `AgentPlatformService`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && flutter test test/modules/agents/agent_platform_service_test.dart`
Expected: PASS (all tests in the file, old + new groups)

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/modules/agents/services/agent_platform_service.dart frontend/test/modules/agents/agent_platform_service_test.dart
git commit -m "fix(frontend): migrate AgentPlatformService dashboard/roster/work-products/escalations sang WorkforceMvpService

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 12: Frontend — fix `id` type (`int`→`String`) now that escalations are real data

**⚠️ Re-scoped after checking current code (2026-09-04):** the "Resolve
button must not silently no-op" risk this task originally targeted was
**already fixed on 2026-09-02** ("Truthfulness fix" — see the doc-comment at
the top of `exception_escalation_inbox.dart` and the existing test
`frontend/test/modules/hologram_hub/exception_escalation_inbox_resolve_disabled_test.dart`).
The action buttons are already structurally disabled (no `GestureDetector`)
and an honest "chưa khả dụng" banner already shows. **Do not redo that
work.** What Task 11 actually breaks: the real `WorkforceException.id` is a
`run_id` **string** (Task 4/9), but `ExceptionEscalationInbox.onResolve`,
`_EscalationCard`'s internal closure, and
`hub_control_plane_mixin.dart::resolveEscalation`/`openEscalations` handling
still assume `int`. This task only fixes that type mismatch and retires the
now-dead call to `agentPlatformService.resolveEscalation` (a method that
still points at a route that will never exist per the spec's scope decision).

**Files:**
- Modify: `frontend/lib/modules/hologram_hub/views/widgets/exception_escalation_inbox.dart`
- Modify: `frontend/lib/modules/hologram_hub/controllers/mixins/hub_control_plane_mixin.dart`
- Modify: `frontend/test/modules/hologram_hub/exception_escalation_inbox_resolve_disabled_test.dart` (update fixture id to a string, keep every existing assertion)

**Interfaces:**
- Produces: `ExceptionEscalationInbox.onResolve` becomes `void Function(String id, String action, String? comment)`; `hub_control_plane_mixin.dart::resolveEscalation(String escalationId, String action, [String? comment])` (was `int`) becomes a no-op that shows an honest toast instead of calling `agentPlatformService.resolveEscalation`.

- [ ] **Step 1: Update the existing widget test's fixture to a string id**

In `frontend/test/modules/hologram_hub/exception_escalation_inbox_resolve_disabled_test.dart`,
change `_escalation()`'s `'id': 1` to `'id': 'run_failed_1'` (matches the
real `run_id` shape from `WorkforceException.id`). No other change needed in
this file — every existing assertion (banner text, disabled button, tap
producing zero `onResolve` calls) still holds regardless of the id's type,
since the button stays untappable either way. This keeps the test honest
about the real data shape it's guarding.

- [ ] **Step 2: Run the existing test to confirm it still passes with the string id**

Run: `cd frontend && flutter test frontend/test/modules/hologram_hub/exception_escalation_inbox_resolve_disabled_test.dart`
Expected: PASS (unchanged — confirms the disabled-button behavior doesn't
depend on `id`'s type, so this step is a safe refactor, not a behavior
change)

- [ ] **Step 3: Change `onResolve` and the internal `id` cast to `String`**

In `exception_escalation_inbox.dart`:

Change the class field and constructor param type:

```dart
  final void Function(String id, String action, String? comment) onResolve;
```

(2 occurrences: the `ExceptionEscalationInbox` class field/constructor and
the identical param in its `static void show({...})` — update both).

Change the internal extraction (currently `final id = esc['id'] as int?;`):

```dart
                    onResolve: (action, comment) {
                      final id = esc['id'] as String?;
                      if (id != null) onResolve(id, action, comment);
                    },
```

- [ ] **Step 4: Change `resolveEscalation` in the mixin to `String` + retire the dead backend call**

In `hub_control_plane_mixin.dart`, replace the whole method:

```dart
  /// MVP hiện tại chỉ có escalations LIST (read-only) — KHÔNG có backend
  /// resolve thật (xem docs/superpowers/specs/2026-09-04-workforce-dashboard-backend-gaps-design.md
  /// Phase 5). UI đã vô hiệu hoá nút bấm từ 2026-09-02 (xem
  /// exception_escalation_inbox.dart) nên đường này giờ không còn ai gọi
  /// được từ UI — giữ lại làm no-op tường minh (thay vì gọi
  /// agentPlatformService.resolveEscalation vào 1 route sẽ luôn 404) để bất
  /// kỳ caller nào khác (test, tương lai) cũng nhận được thông báo rõ ràng
  /// thay vì một lỗi mạng khó hiểu.
  Future<void> resolveEscalation(
    String escalationId,
    String action, [
    String? comment,
  ]) async {
    AppToast.error(
      'Chưa hỗ trợ resolve exception trong bản này — đang chờ thiết kế domain escalation riêng.',
      title: 'Chưa khả dụng',
      duration: const Duration(seconds: 4),
    );
  }
```

Check `frontend/lib/core/widgets/app_toast.dart` for the exact static method
name for an error-styled toast (confirmed present as `AppToast.error` at the
time of writing this plan — verify it's still there before using it) and
match its parameter names (`title`, `duration`) to the existing
`AppToast.success` call two lines above in the old version of this method.

The call site at (search for) `onResolve: (id, action, comment) =>
resolveEscalation(id, action, comment)` needs no change — `id`'s inferred
type follows the widget's now-`String` callback automatically.

- [ ] **Step 5: Run the full hologram_hub test directory to catch any other `int` id assumption**

Run: `cd frontend && flutter test test/modules/hologram_hub/`
Expected: PASS — if anything else in this directory still assumes `int`
escalation ids, fix it here rather than leaving a second inconsistent type
assumption behind (grep `openEscalations` and `escalation_action_disabled`
across `frontend/lib/modules/hologram_hub/` first if a failure points at a
file not already covered by Steps 3-4).

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/modules/hologram_hub/views/widgets/exception_escalation_inbox.dart frontend/lib/modules/hologram_hub/controllers/mixins/hub_control_plane_mixin.dart frontend/test/modules/hologram_hub/exception_escalation_inbox_resolve_disabled_test.dart
git commit -m "fix(frontend): đổi escalation id sang String khớp run_id thật + bỏ lệnh gọi resolveEscalation chết

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 13: Full verification gate

**Files:** none (verification only)

- [ ] **Step 1: Backend unit tests**

Run: `make apps-cosa-test`
Expected: all pass, coverage gate (78%) holds

- [ ] **Step 2: Company service tests + typecheck**

Run: `make services-test-company && cd services/company && npm run typecheck`
Expected: all pass, no type errors

- [ ] **Step 3: Frontend tests + analyze**

Run: `make frontend-test && make frontend-analyze`
Expected: all pass, no new analyzer warnings

- [ ] **Step 4: Contract + boundary gates**

Run: `make mvp-contracts-check && make mvp-surface-check && make frontend-api-contract-check && make company-boundary-check && make encore-handler-boundary-check`
Expected: all pass

- [ ] **Step 5: Manual smoke (optional but recommended)**

Run: `make dev-stack`, open the Flutter app, confirm:
- Founder Dashboard no longer logs `Connection refused` for `listWorkforcePacks`/`listApprovals`/`getDashboardSummary` (Tasks 8-11 fixed the routing).
- Workforce org-chart modal shows the 6 real functional agents, not the old 12 fake ones.
- Exception Escalation Inbox's "Resolve" control is visibly disabled with the "chưa hỗ trợ" label, not silently failing.

- [ ] **Step 6: Final commit (only if any fixups were needed above)**

```bash
git add -A
git commit -m "chore: fixups sau full verification gate — workforce dashboard backend gaps

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```
