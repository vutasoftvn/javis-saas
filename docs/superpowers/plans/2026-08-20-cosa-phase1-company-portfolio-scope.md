# COSA Phase 1 Company Portfolio Scope Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a workspace operate as one Company with multiple Operating Units, Offerings, Initiatives, and WorkItems, and make every Harness execution use an authorized, server-derived scope.

**Architecture:** `Workspace` remains COSA's canonical Company/tenant; Phase 1 must not introduce a duplicate `companies` table. Add `OperatingUnit` and `Offering` to the Business Core, attach the existing `Initiative` to an Offering, and retain the existing `Task.initiative_id` WorkItem path. The canonical runtime receives an immutable `ExecutionScope` resolved from authenticated membership and verified hierarchy records; client IDs can only request narrower scope and never grant it.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, Alembic/PostgreSQL, Pydantic, pytest, Flutter/Dart, GetX.

**Spec:** `docs/superpowers/plans/2026-08-20-cosa-extensible-harness-visual-workflows-rebuild.md` (Phase 1), `markdown/plan1.md`, `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`.

## Global Constraints

- `Workspace` is the Company identifier. In API and `ExecutionScope`, `company_id == workspace_id` until a separately approved tenant migration introduces a distinct company identity.
- Do not create `backend/agent_runtime/runtime`, root `backend/tools`, root `backend/skills`, root `backend/workflows`, or root `backend/executors` production code.
- Put new portfolio domain models in `backend/core/organization/`; expose compatibility imports only if a verified consumer requires them.
- Keep `Project` as the existing strategy/planning record. Do not replace it with a second initiative or work-item engine.
- Keep `Initiative` as the operational unit below Offering; `Task` remains the WorkItem table through `Task.initiative_id`.
- All database changes are nullable/additive first; no destructive migration, backfill rewrite, or inferred offering assignment in this phase.
- Every endpoint derives membership from `get_current_workspace_member`; it must reject a mismatched `workspace_id` query parameter before returning data.
- Every write to organization hierarchy, workflow scope binding, or scope snapshot requires `owner` or `admin`; read access follows current workspace membership until per-unit membership is deliberately designed.
- `ExecutionScope` must be immutable, JSON-safe, and assembled on the server. Never accept `principal`, `grants`, `profile`, or a scope snapshot from a client/model as authoritative input.
- Existing workflow persistence remains under `backend/app/integrations/workflows`; Flutter workflow UI remains under `frontend/lib/modules/workflows`.
- Do not add MCP, extension registry, tool-pipeline migration, graph compiler, or DeepSeek Harness behavior in this phase.

---

## Target domain and API contract

```text
Workspace (canonical Company)
  └─ OperatingUnit
       └─ Offering (product | service | hybrid)
            └─ Initiative
                 └─ Task (existing WorkItem)

Project (existing strategy/planning record) ── optional link from Initiative
```

```python
@dataclass(frozen=True)
class ExecutionScope:
    workspace_id: int
    company_id: int                 # always workspace_id in Phase 1
    principal_user_id: int
    principal_member_id: int
    principal_role: str
    operating_unit_id: int | None
    offering_id: int | None
    initiative_id: int | None
    profile_id: str | None
    session_id: str | None
    grants: tuple[str, ...]

    def snapshot(self) -> dict[str, object]:
        return {
            "workspace_id": self.workspace_id,
            "company_id": self.company_id,
            "principal_user_id": self.principal_user_id,
            "principal_member_id": self.principal_member_id,
            "principal_role": self.principal_role,
            "operating_unit_id": self.operating_unit_id,
            "offering_id": self.offering_id,
            "initiative_id": self.initiative_id,
            "profile_id": self.profile_id,
            "session_id": self.session_id,
            "grants": list(self.grants),
        }
```

Public routes added by this phase, all under existing `platform.organization` ownership:

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/v1/organization/portfolio` | Authorized hierarchy and selectable scope tree |
| POST | `/api/v1/organization/operating-units` | Create unit |
| PATCH | `/api/v1/organization/operating-units/{id}` | Rename/archive unit |
| POST | `/api/v1/organization/offerings` | Create offering below unit |
| PATCH | `/api/v1/organization/offerings/{id}` | Update/archive offering |
| PATCH | `/api/v1/organization/initiatives/{id}/offering` | Attach existing initiative to offering |
| GET | `/api/v1/organization/scope-options` | Flattened, authorized selector data |

Workflow routes retain their paths. They gain optional `operating_unit_id`, `offering_id`, and `initiative_id` inputs for definition/version/run creation, which are resolved by the server and persisted only as validated scope binding/snapshot data.

## File structure

| File | Responsibility |
|---|---|
| `backend/core/organization/models.py` | `OperatingUnit` and `Offering` SQLAlchemy models and constraints |
| `backend/core/organization/__init__.py` | Deliberate exports for canonical organization models |
| `backend/core/strategy/initiative.py` | Add nullable `offering_id` to existing Initiative |
| `backend/app/db/base.py` | Import new canonical models into SQLAlchemy metadata |
| `backend/alembic/versions/v13_058_company_portfolio_scope.py` | Additive schema migration and indexes |
| `backend/app/workforce/agents/runtime/execution_scope.py` | Immutable `ExecutionScope` contract and serialization |
| `backend/app/workforce/agents/runtime/scope_resolver.py` | Parent-child validation and server-derived scope resolution |
| `backend/app/platform/organization/portfolio_schemas.py` | Request/response DTOs only |
| `backend/app/platform/organization/portfolio_service.py` | Hierarchy writes, reads, and authorization-friendly queries |
| `backend/app/platform/organization/portfolio_router.py` | Thin REST adapter for portfolio endpoints |
| `backend/app/platform/organization/router.py` | Mount new portfolio router without duplicating organization routes |
| `backend/app/integrations/workflows/models.py` | Scope binding/snapshot columns on existing workflow records |
| `backend/app/integrations/workflows/router.py` | Resolve scope for workflow definition, version, run, approvals |
| `backend/app/founder_os/outcomes/models.py` | Scope snapshot on governed artifacts |
| `backend/app/tests/organization/`, `backend/app/tests/agents/runtime/`, `backend/app/tests/integrations/` | Unit, migration, integration and scope-tampering regressions |
| `frontend/lib/core/scope/company_scope.dart` | Immutable UI scope value object |
| `frontend/lib/core/scope/company_scope_controller.dart` | Authorized selector state; no authority decisions |
| `frontend/lib/core/scope/company_scope_service.dart` | Calls scope-options endpoint; does not store grants |
| `frontend/lib/core/widgets/company_scope_switcher.dart` | Shared dropdown/breadcrumb component |
| `frontend/lib/modules/workflows/services/workflows_service.dart`, `controllers/workflows_controller.dart`, `views/workflows_view.dart` | Add scope context to list/run calls and display it |
| `frontend/test/core/` and `frontend/test/modules/workflows/` | Controller/service/widget tests for selector and workflow scope rendering |

### Task 1: Characterize the current Company-to-WorkItem graph

**Files:**
- Create: `backend/app/tests/organization/test_portfolio_scope_baseline.py`
- Modify: `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`
- Verify: `backend/app/platform/auth/models.py`, `backend/core/strategy/project.py`, `backend/core/strategy/initiative.py`, `backend/core/tasks/models.py`

**Consumes:** Phase 0 ownership map and existing Workspace/Project/Initiative/Task models.
**Produces:** A characterization test and ADR-quality decision that `Workspace` is Company, `Initiative` is retained, and `Task` is WorkItem.

- [ ] **Step 1: Write the failing characterization test**

```python
def test_company_portfolio_uses_existing_workspace_initiative_and_task_anchors():
    assert Workspace.__tablename__ == "workspaces"
    assert Initiative.__tablename__ == "initiatives"
    assert "initiative_id" in Task.__table__.c
    assert "company_id" not in Workspace.__table__.c
```

- [ ] **Step 2: Run the test to capture current behavior**

Run: `cd backend && pytest app/tests/organization/test_portfolio_scope_baseline.py -q`

Expected: PASS. If the final assertion fails, stop Phase 1 and record the existing company authority before making schema changes; do not create a second company model.

- [ ] **Step 3: Add the scope decision to the ownership map**

Add a `Company portfolio scope` row stating:

```text
Workspace is the Company/tenant in Phase 1. OperatingUnit and Offering are Business Core entities.
Initiative remains the existing operational record and Task remains the WorkItem engine.
Project is a linked strategy record, not a replacement hierarchy level.
```

- [ ] **Step 4: Run the architectural and baseline tests**

Run: `cd backend && pytest app/tests/organization/test_portfolio_scope_baseline.py app/tests/test_architectural_invariants.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the baseline decision**

```bash
git add docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md backend/app/tests/organization/test_portfolio_scope_baseline.py
git commit -m "docs: define company portfolio scope anchors"
```

### Task 2: Add Operating Unit and Offering as additive Business Core entities

**Files:**
- Create: `backend/core/organization/__init__.py`
- Create: `backend/core/organization/models.py`
- Modify: `backend/core/strategy/initiative.py`
- Modify: `backend/app/db/base.py`
- Create: `backend/app/tests/organization/test_portfolio_models.py`

**Consumes:** `Workspace`, `Initiative`, `generate_snowflake_id`.
**Produces:** `OperatingUnit` and `Offering` models; `Initiative.offering_id` is nullable.

- [ ] **Step 1: Write failing model tests**

```python
def test_offering_must_belong_to_an_operating_unit_in_the_same_workspace(db_session):
    unit = OperatingUnit(workspace_id=100, slug="saas", name="SaaS")
    offering = Offering(workspace_id=100, operating_unit_id=unit.id, slug="cosa", name="COSA", kind="product")
    db_session.add_all([unit, offering])
    db_session.commit()
    assert offering.operating_unit_id == unit.id

def test_initiative_offering_link_is_optional_for_legacy_rows():
    assert Initiative.__table__.c.offering_id.nullable is True
```

- [ ] **Step 2: Verify RED**

Run: `cd backend && pytest app/tests/organization/test_portfolio_models.py -q`

Expected: FAIL with `ImportError` for `OperatingUnit` / `Offering` and missing `offering_id`.

- [ ] **Step 3: Implement the canonical models**

Create `backend/core/organization/models.py` with this shape:

```python
class OperatingUnit(Base):
    __tablename__ = "operating_units"
    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", name="uq_operating_unit_workspace_slug"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    slug: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Offering(Base):
    __tablename__ = "offerings"
    __table_args__ = (
        UniqueConstraint("operating_unit_id", "slug", name="uq_offering_unit_slug"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    operating_unit_id: Mapped[int] = mapped_column(ForeignKey("operating_units.id"), index=True)
    slug: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(24))  # product | service | hybrid
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

Add `offering_id: Mapped[Optional[int]] = mapped_column(ForeignKey("offerings.id"), nullable=True, index=True)` to `Initiative`; do not add `operating_unit_id` there because it is derived through Offering. Export both models in `core/organization/__init__.py` and import them in `app/db/base.py`.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && pytest app/tests/organization/test_portfolio_models.py -q`

Expected: PASS.

- [ ] **Step 5: Commit model ownership**

```bash
git add backend/core/organization backend/core/strategy/initiative.py backend/app/db/base.py backend/app/tests/organization/test_portfolio_models.py
git commit -m "feat: add company portfolio hierarchy models"
```

### Task 3: Ship a reversible additive schema migration

**Files:**
- Create: `backend/alembic/versions/v13_058_company_portfolio_scope.py`
- Create: `backend/app/tests/organization/test_portfolio_scope_migration.py`
- Verify: `backend/alembic/versions/v13_057_learning_review_and_memory.py`

**Consumes:** Task 2 models and Alembic head revision.
**Produces:** New `operating_units`, `offerings`, nullable `initiatives.offering_id`, indexes and uniqueness constraints.

- [ ] **Step 1: Write migration contract tests**

```python
def test_company_portfolio_migration_is_additive_and_reversible():
    source = migration_path.read_text()
    assert 'create_table("operating_units"' in source
    assert 'create_table("offerings"' in source
    assert 'add_column("initiatives", sa.Column("offering_id"' in source
    assert 'drop_table("initiatives")' not in source
    assert "def downgrade()" in source
```

- [ ] **Step 2: Verify RED**

Run: `cd backend && pytest app/tests/organization/test_portfolio_scope_migration.py -q`

Expected: FAIL because the migration does not exist.

- [ ] **Step 3: Implement `v13_058_company_portfolio_scope.py`**

Use the actual current Alembic head as `down_revision`. In `upgrade()`:

```python
op.create_table(
    "operating_units",
    sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
    sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False),
    sa.Column("slug", sa.String(length=100), nullable=False),
    sa.Column("name", sa.String(length=255), nullable=False),
    sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
    sa.Column("created_at", sa.DateTime(), nullable=False),
    sa.Column("updated_at", sa.DateTime(), nullable=False),
    sa.UniqueConstraint("workspace_id", "slug", name="uq_operating_unit_workspace_slug"),
)
op.create_index("ix_operating_units_workspace_status", "operating_units", ["workspace_id", "status"])
op.create_table(
    "offerings",
    sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
    sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False),
    sa.Column("operating_unit_id", sa.BigInteger(), sa.ForeignKey("operating_units.id"), nullable=False),
    sa.Column("slug", sa.String(length=100), nullable=False),
    sa.Column("name", sa.String(length=255), nullable=False),
    sa.Column("kind", sa.String(length=24), nullable=False),
    sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
    sa.Column("created_at", sa.DateTime(), nullable=False),
    sa.Column("updated_at", sa.DateTime(), nullable=False),
    sa.UniqueConstraint("operating_unit_id", "slug", name="uq_offering_unit_slug"),
)
op.create_index("ix_offerings_workspace_unit_status", "offerings", ["workspace_id", "operating_unit_id", "status"])
with op.batch_alter_table("initiatives") as batch_op:
    batch_op.add_column(sa.Column("offering_id", sa.BigInteger(), sa.ForeignKey("offerings.id"), nullable=True))
    batch_op.create_index("ix_initiatives_offering_id", ["offering_id"])
```

`downgrade()` must drop only the new index/column/tables in reverse order. It must refuse neither legacy Initiative rows nor attempt a guessed data backfill.

- [ ] **Step 4: Verify migration from a fresh test database**

Run: `cd backend && alembic upgrade head && pytest app/tests/organization/test_portfolio_scope_migration.py app/tests/organization/test_portfolio_models.py -q`

Expected: migration completes and tests PASS.

- [ ] **Step 5: Commit migration**

```bash
git add backend/alembic/versions/v13_058_company_portfolio_scope.py backend/app/tests/organization/test_portfolio_scope_migration.py
git commit -m "feat: migrate company portfolio scope schema"
```

### Task 4: Build the server-derived ExecutionScope resolver

**Files:**
- Create: `backend/app/workforce/agents/runtime/execution_scope.py`
- Create: `backend/app/workforce/agents/runtime/scope_resolver.py`
- Create: `backend/app/tests/agents/runtime/test_execution_scope.py`

**Consumes:** `WorkspaceMember`, `OperatingUnit`, `Offering`, `Initiative`; canonical runtime ownership under `app/workforce/agents/runtime`.
**Produces:** `ExecutionScope`, `ScopeRequest`, `resolve_execution_scope()` and `ScopeResolutionError`.

- [ ] **Step 1: Write failing scope tests**

```python
def test_resolver_rejects_offering_from_another_workspace(db, member, foreign_offering):
    with pytest.raises(ScopeResolutionError, match="offering is outside workspace"):
        resolve_execution_scope(db, member, ScopeRequest(offering_id=foreign_offering.id))

def test_resolver_rejects_initiative_that_is_not_under_requested_offering(db, member, offering_a, initiative_b):
    with pytest.raises(ScopeResolutionError, match="initiative is outside offering"):
        resolve_execution_scope(db, member, ScopeRequest(offering_id=offering_a.id, initiative_id=initiative_b.id))

def test_resolver_derives_company_and_principal_from_member(db, owner_member, offering_a):
    scope = resolve_execution_scope(db, owner_member, ScopeRequest(offering_id=offering_a.id, grants=("workflow.run",)))
    assert scope.company_id == owner_member.workspace_id
    assert scope.principal_user_id == owner_member.user_id
    assert scope.offering_id == offering_a.id
    assert scope.snapshot()["grants"] == ["workflow.run"]
```

- [ ] **Step 2: Verify RED**

Run: `cd backend && pytest app/tests/agents/runtime/test_execution_scope.py -q`

Expected: FAIL because the resolver module does not exist.

- [ ] **Step 3: Implement immutable scope contracts**

Implement:

```python
@dataclass(frozen=True)
class ScopeRequest:
    operating_unit_id: int | None = None
    offering_id: int | None = None
    initiative_id: int | None = None
    profile_id: str | None = None
    session_id: str | None = None
    grants: tuple[str, ...] = ()

class ScopeResolutionError(ValueError):
    pass

def resolve_execution_scope(db: Session, member: WorkspaceMember, request: ScopeRequest) -> ExecutionScope:
    workspace_id = member.workspace_id
    unit = db.query(OperatingUnit).filter(OperatingUnit.id == request.operating_unit_id, OperatingUnit.workspace_id == workspace_id).first() if request.operating_unit_id else None
    if request.operating_unit_id and unit is None:
        raise ScopeResolutionError("operating unit is outside workspace")
    offering = db.query(Offering).filter(Offering.id == request.offering_id, Offering.workspace_id == workspace_id).first() if request.offering_id else None
    if request.offering_id and offering is None:
        raise ScopeResolutionError("offering is outside workspace")
    if unit and offering and offering.operating_unit_id != unit.id:
        raise ScopeResolutionError("offering is outside operating unit")
    initiative = db.query(Initiative).filter(Initiative.id == request.initiative_id, Initiative.workspace_id == workspace_id).first() if request.initiative_id else None
    if request.initiative_id and initiative is None:
        raise ScopeResolutionError("initiative is outside workspace")
    if offering and initiative and initiative.offering_id != offering.id:
        raise ScopeResolutionError("initiative is outside offering")
    return ExecutionScope(
        workspace_id=workspace_id, company_id=workspace_id,
        principal_user_id=member.user_id, principal_member_id=member.id,
        principal_role=member.role, operating_unit_id=unit.id if unit else None,
        offering_id=offering.id if offering else None,
        initiative_id=initiative.id if initiative else None,
        profile_id=request.profile_id, session_id=request.session_id,
        grants=tuple(sorted(set(request.grants))),
    )
```

`ExecutionScope.snapshot()` returns only JSON-safe IDs and names: `workspace_id`, `company_id`, `operating_unit_id`, `offering_id`, `initiative_id`, `principal_user_id`, `principal_member_id`, `principal_role`, `profile_id`, `session_id`, and a sorted list of grants. It must not contain access tokens, secret IDs, raw permission objects, or model-generated fields.

- [ ] **Step 4: Verify GREEN and tamper resistance**

Run: `cd backend && pytest app/tests/agents/runtime/test_execution_scope.py -q`

Expected: PASS. Include test cases for foreign unit, foreign offering, foreign initiative, unit/offering mismatch, and an Initiative with `offering_id is None` requested under an offering.

- [ ] **Step 5: Commit scope authority**

```bash
git add backend/app/workforce/agents/runtime/execution_scope.py backend/app/workforce/agents/runtime/scope_resolver.py backend/app/tests/agents/runtime/test_execution_scope.py
git commit -m "feat: add server-derived execution scope"
```

### Task 5: Add portfolio hierarchy service and authorized REST API

**Files:**
- Create: `backend/app/platform/organization/portfolio_schemas.py`
- Create: `backend/app/platform/organization/portfolio_service.py`
- Create: `backend/app/platform/organization/portfolio_router.py`
- Modify: `backend/app/platform/organization/router.py`
- Modify: `backend/app/core/authz.py`
- Create: `backend/app/tests/organization/test_portfolio_router.py`

**Consumes:** Tasks 2–4; existing `authorize()` and `get_current_workspace_member`.
**Produces:** CRUD-lite organization hierarchy APIs and scope-options output suitable for UI.

- [ ] **Step 1: Write failing integration tests**

```python
def test_member_cannot_create_operating_unit(client, member_auth):
    response = client.post("/api/v1/organization/operating-units?workspace_id=101", json={"slug": "services", "name": "Services"}, headers=member_auth)
    assert response.status_code == 403

def test_owner_can_create_hierarchy_and_read_scope_options(client, owner_auth):
    unit = client.post("/api/v1/organization/operating-units?workspace_id=101", json={"slug": "services", "name": "Services"}, headers=owner_auth)
    offering = client.post("/api/v1/organization/offerings?workspace_id=101", json={"operating_unit_id": unit.json()["id"], "slug": "advisory", "name": "Advisory", "kind": "service"}, headers=owner_auth)
    options = client.get("/api/v1/organization/scope-options?workspace_id=101", headers=owner_auth)
    assert options.status_code == 200
    assert options.json()["operating_units"][0]["offerings"][0]["id"] == offering.json()["id"]

def test_workspace_parameter_tampering_is_forbidden(client, owner_auth):
    assert client.get("/api/v1/organization/scope-options?workspace_id=999", headers=owner_auth).status_code == 403
```

- [ ] **Step 2: Verify RED**

Run: `cd backend && pytest app/tests/organization/test_portfolio_router.py -q`

Expected: FAIL with 404 because portfolio routes are unmounted.

- [ ] **Step 3: Implement schemas, service, and authorization action names**

Add `organization.manage` to `PROTECTED_ACTIONS`. In `portfolio_router.py`, require both `member.workspace_id == workspace_id` and `authorize(member, "organization.manage")` for POST/PATCH. Do not depend on the client only hiding controls.

Use Pydantic constraints:

```python
class OfferingCreate(BaseModel):
    operating_unit_id: int
    slug: Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{1,98}$")]
    name: Annotated[str, StringConstraints(min_length=1, max_length=255)]
    kind: Literal["product", "service", "hybrid"]
```

`portfolio_service.py` must query the unit with both `id` and `workspace_id` before creating an Offering. `attach_initiative_to_offering()` must query Initiative and Offering in the caller workspace, then set only `initiative.offering_id`; it must not change the legacy `project_id` link.

`GET /scope-options` returns:

```json
{
  "company": {"id": "101", "name": "MIVA"},
  "operating_units": [
    {"id": "201", "name": "SaaS", "offerings": [
      {"id": "301", "name": "COSA", "kind": "product", "initiatives": [{"id": "401", "title": "Q4 GTM"}]}
    ]}
  ]
}
```

Mount the new router below the existing `platform.organization.router` rather than adding a new domain master router.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && pytest app/tests/organization/test_portfolio_router.py -q`

Expected: PASS, including cross-workspace and role tests.

- [ ] **Step 5: Commit portfolio API**

```bash
git add backend/app/platform/organization backend/app/core/authz.py backend/app/tests/organization/test_portfolio_router.py
git commit -m "feat: expose authorized company portfolio scope API"
```

### Task 6: Persist validated scope bindings and start snapshots on existing workflow records

**Files:**
- Modify: `backend/app/integrations/workflows/models.py`
- Modify: `backend/app/integrations/workflows/router.py`
- Modify: `backend/app/founder_os/outcomes/models.py`
- Create: `backend/alembic/versions/v13_059_workflow_scope_snapshots.py`
- Create: `backend/app/tests/integrations/test_workflow_scope_snapshots.py`

**Consumes:** `ExecutionScope` resolver, existing WorkflowDefinition/Version/Run/Step/Approval and Artifact records.
**Produces:** Validated scope binding on definitions/versions and immutable start snapshots on runs, approvals, and artifacts.

- [ ] **Step 1: Write failing workflow scope tests**

```python
def test_workflow_run_persists_server_resolved_scope_not_client_snapshot(client, owner_auth, definition):
    response = client.post(
        f"/api/v1/workflows/definitions/{definition.id}/run?workspace_id=101",
        json={"offering_id": 301, "scope_snapshot": {"workspace_id": 999, "grants": ["admin"]}},
        headers=owner_auth,
    )
    assert response.status_code == 201
    assert response.json()["scope_snapshot"]["workspace_id"] == 101
    assert "admin" not in response.json()["scope_snapshot"]["grants"]

def test_workflow_run_cannot_start_in_foreign_offering(client, owner_auth, definition):
    response = client.post(f"/api/v1/workflows/definitions/{definition.id}/run?workspace_id=101", json={"offering_id": 9999}, headers=owner_auth)
    assert response.status_code == 403
```

- [ ] **Step 2: Verify RED**

Run: `cd backend && pytest app/tests/integrations/test_workflow_scope_snapshots.py -q`

Expected: FAIL because request DTOs and scope persistence do not exist.

- [ ] **Step 3: Add only these nullable JSON columns**

| Table/model | Column | Meaning |
|---|---|---|
| `workflow_definitions` | `scope_binding_jsonb` | Saved authoring default, validated at write time |
| `workflow_versions` | `scope_requirements_jsonb` | Immutable copy of compatible scope requirement at version creation |
| `workflow_runs` | `scope_snapshot_jsonb` | Exact scope resolved when the run starts |
| `workflow_approvals` | `scope_snapshot_jsonb` | Copy of the run scope at approval creation |
| `artifacts` | `scope_snapshot_jsonb` | Scope of artifact creation, not a replacement for workspace_id |

The v13_059 migration adds the fields as nullable PostgreSQL JSONB and adds no inferred data. `downgrade()` removes only these fields.

- [ ] **Step 4: Resolve scope inside workflow routes**

Extend `WorkflowDefinitionCreate`, `WorkflowVersionCreate`, and `WorkflowRunCreate` with optional `operating_unit_id`, `offering_id`, `initiative_id`, `profile_id`, and `session_id`. Do **not** add `company_id`, `principal_*`, `grants`, or `scope_snapshot` fields to their public request schemas.

Before create/version/run, call:

```python
scope = resolve_execution_scope(
    db,
    member,
    ScopeRequest(
        operating_unit_id=data.operating_unit_id,
        offering_id=data.offering_id,
        initiative_id=data.initiative_id,
        profile_id=data.profile_id,
        session_id=data.session_id,
        grants=("workflow.author",) if is_authoring else ("workflow.run",),
    ),
)
```

Translate `ScopeResolutionError` to HTTP 403. Store `scope.snapshot()`; return it in create/run responses. When creating a `WorkflowApproval`, copy `run.scope_snapshot_jsonb` rather than recalculating scope. Artifact producers in this phase must accept an optional `scope_snapshot` supplied only by a resolved execution path; direct user artifact routes continue to persist `workspace_id` until migrated by a later task.

- [ ] **Step 5: Verify GREEN**

Run: `cd backend && pytest app/tests/integrations/test_workflow_scope_snapshots.py app/tests/test_tenancy.py -q`

Expected: PASS. Verify a request can narrow a definition to an Offering, a run snapshots it, and a foreign/tampered scope is rejected.

- [ ] **Step 6: Commit workflow scope snapshots**

```bash
git add backend/app/integrations/workflows backend/app/founder_os/outcomes/models.py backend/alembic/versions/v13_059_workflow_scope_snapshots.py backend/app/tests/integrations/test_workflow_scope_snapshots.py
git commit -m "feat: persist validated workflow execution scopes"
```

### Task 7: Make existing portfolio queries and run inspection scope-aware

**Files:**
- Modify: `backend/app/integrations/workflows/router.py`
- Modify: `backend/app/founder_os/strategy/portfolio_router.py`
- Create: `backend/app/tests/integrations/test_scope_filtered_workflow_queries.py`
- Create: `backend/app/tests/organization/test_scope_filtered_portfolio_queries.py`

**Consumes:** Scope snapshot fields from Task 6 and existing portfolio APIs.
**Produces:** Optional scope filters that can only narrow results; no endpoint trusts a filter as authorization.

- [ ] **Step 1: Write failing data-isolation tests**

```python
def test_workflow_run_list_filters_to_selected_offering_without_leaking_other_offering(client, owner_auth):
    response = client.get("/api/v1/workflows/runs?workspace_id=101&offering_id=301", headers=owner_auth)
    assert [item["id"] for item in response.json()["runs"]] == ["run-for-301"]

def test_run_detail_returns_404_when_scope_filter_does_not_match_its_snapshot(client, owner_auth):
    response = client.get("/api/v1/workflows/runs/run-for-302?workspace_id=101&offering_id=301", headers=owner_auth)
    assert response.status_code == 404
```

- [ ] **Step 2: Verify RED**

Run: `cd backend && pytest app/tests/integrations/test_scope_filtered_workflow_queries.py app/tests/organization/test_scope_filtered_portfolio_queries.py -q`

Expected: FAIL because scope filters are ignored.

- [ ] **Step 3: Implement narrowing-only filters**

Add optional `operating_unit_id`, `offering_id`, and `initiative_id` query fields to workflow list/detail endpoints. First validate them through `resolve_execution_scope`; then filter JSONB snapshot fields using PostgreSQL containment or a derived predicate suitable for the existing database dialect. A missing snapshot is legacy workspace-wide data and must appear only when no narrower filter was requested.

For portfolio views, filter Projects through their linked Initiatives and Offerings. Preserve all existing `workspace_id` predicates; scope filtering is an additional `AND`, never a replacement.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && pytest app/tests/integrations/test_scope_filtered_workflow_queries.py app/tests/organization/test_scope_filtered_portfolio_queries.py -q`

Expected: PASS, including one workspace with two offerings and a request that tampers with another offering ID.

- [ ] **Step 5: Commit scope filtering**

```bash
git add backend/app/integrations/workflows/router.py backend/app/founder_os/strategy/portfolio_router.py backend/app/tests/integrations/test_scope_filtered_workflow_queries.py backend/app/tests/organization/test_scope_filtered_portfolio_queries.py
git commit -m "feat: filter portfolio and workflow views by scope"
```

### Task 8: Add the frontend Company scope state and application-shell switcher

**Files:**
- Create: `frontend/lib/core/scope/company_scope.dart`
- Create: `frontend/lib/core/scope/company_scope_service.dart`
- Create: `frontend/lib/core/scope/company_scope_controller.dart`
- Create: `frontend/lib/core/widgets/company_scope_switcher.dart`
- Modify: the actual authenticated application-shell widget found by `rg -n "Scaffold|NavigationRail|Drawer" frontend/lib/modules frontend/lib/core`
- Create: `frontend/test/core/scope/company_scope_controller_test.dart`
- Create: `frontend/test/core/widgets/company_scope_switcher_test.dart`

**Consumes:** Task 5 `GET /organization/scope-options`; existing `ApiClient` and GetX conventions.
**Produces:** UI selection state that drives requests but does not assert permission/grants locally.

- [ ] **Step 1: Write failing controller and widget tests**

```dart
test('selectOffering clears initiative when it belongs to another offering', () async {
  final controller = CompanyScopeController(service: FakeScopeService(twoOfferings));
  await controller.load();
  controller.selectInitiative('initiative-a');
  controller.selectOffering('offering-b');
  expect(controller.scope.value.initiativeId, isNull);
});

testWidgets('scope switcher renders company, unit, offering and initiative breadcrumb', (tester) async {
  await tester.pumpWidget(testApp(const CompanyScope(
    workspaceId: '101',
    operatingUnitId: '201',
    offeringId: '301',
    initiativeId: '401',
  )));
  expect(find.text('MIVA'), findsOneWidget);
  expect(find.text('COSA'), findsOneWidget);
});
```

- [ ] **Step 2: Verify RED**

Run: `cd frontend && flutter test test/core/scope/company_scope_controller_test.dart test/core/widgets/company_scope_switcher_test.dart`

Expected: FAIL because scope classes and widget do not exist.

- [ ] **Step 3: Implement narrow UI contracts**

`CompanyScope` contains only `workspaceId`, `operatingUnitId`, `offeringId`, and `initiativeId`; no role, grant, secret, profile, or policy field. `CompanyScopeService.fetchOptions()` calls `/organization/scope-options?workspace_id=<cached-workspace-id>`. `CompanyScopeController` keeps selection in memory plus `SharedPreferences` only as UX restoration; it reloads scope options after login/startup and clears an unavailable stored selection.

`CompanyScopeSwitcher` uses four cascading selectors and an always-visible breadcrumb. It must render `All company` when a lower level is absent. It must not hide or enable actions based on a guessed permission; backend response remains authoritative.

- [ ] **Step 4: Verify GREEN**

Run: `cd frontend && flutter test test/core/scope/company_scope_controller_test.dart test/core/widgets/company_scope_switcher_test.dart && flutter analyze lib/core/scope lib/core/widgets/company_scope_switcher.dart`

Expected: PASS and no analyzer issues.

- [ ] **Step 5: Commit shared UI scope**

```bash
git add frontend/lib/core/scope frontend/lib/core/widgets/company_scope_switcher.dart frontend/test/core
git commit -m "feat: add company portfolio scope switcher"
```

### Task 9: Apply scope context to workflow library, runs, tasks, and Hologram entry points

**Files:**
- Modify: `frontend/lib/modules/workflows/services/workflows_service.dart`
- Modify: `frontend/lib/modules/workflows/controllers/workflows_controller.dart`
- Modify: `frontend/lib/modules/workflows/views/workflows_view.dart`
- Modify: existing task and Hologram service/controller files identified by `rg -n "class .*Controller|/tasks|Hologram" frontend/lib/modules/tasks frontend/lib/modules/hologram_hub`
- Create: `frontend/test/modules/workflows/workflows_scope_test.dart`

**Consumes:** Task 8 controller and Task 7 narrowing filters.
**Produces:** Existing UI surfaces include scope query parameters and show scope breadcrumb/chips; no new workflow UI module.

- [ ] **Step 1: Write failing workflow UI test**

```dart
test('workflow service sends current offering and initiative as narrowing query parameters', () async {
  final service = WorkflowsService(scope: const CompanyScope(workspaceId: '101', offeringId: '301', initiativeId: '401'));
  await service.getRuns();
  expect(fakeClient.lastPath, contains('offering_id=301'));
  expect(fakeClient.lastPath, contains('initiative_id=401'));
});

testWidgets('workflow view displays the active scope breadcrumb', (tester) async {
  await tester.pumpWidget(workflowsTestApp(scope: cosaScope));
  expect(find.textContaining('COSA'), findsOneWidget);
});
```

- [ ] **Step 2: Verify RED**

Run: `cd frontend && flutter test test/modules/workflows/workflows_scope_test.dart`

Expected: FAIL because `WorkflowsService` reads only `workspace_id`.

- [ ] **Step 3: Implement scope-aware calls and presentation**

Inject `CompanyScopeController` (or an explicit `CompanyScope` in testable service constructors) instead of making a second preferences lookup. Append only non-null scope identifiers to list/run/detail URLs. On a 403/404 scope response, reload selector options, clear invalid lower selection, and show a neutral `Scope is no longer available` message; do not retry under a wider scope automatically.

Add the shared switcher to the authenticated shell and compact breadcrumb/chip display to existing Workflow Library, task list, and Hologram run cards. Do not build the drag/drop builder in Phase 1.

- [ ] **Step 4: Verify GREEN**

Run: `cd frontend && flutter test test/modules/workflows/workflows_scope_test.dart && flutter analyze lib/modules/workflows lib/modules/tasks lib/modules/hologram_hub`

Expected: PASS and no analyzer issues.

- [ ] **Step 5: Commit frontend propagation**

```bash
git add frontend/lib/modules/workflows frontend/lib/modules/tasks frontend/lib/modules/hologram_hub frontend/test/modules/workflows
git commit -m "feat: apply company scope to operating views"
```

### Task 10: Verify the Phase 1 vertical slice and publish operating guidance

**Files:**
- Modify: `docs/architecture/COSA_HARNESS_CONTRIBUTOR_EXTENSION_MAP.md`
- Create: `docs/architecture/COSA_PHASE1_COMPANY_PORTFOLIO_SCOPE.md`
- Modify: `backend/app/tests/test_architectural_invariants.py`

**Consumes:** Tasks 1–9.
**Produces:** A reproducible acceptance walkthrough and an invariant preventing a second scope authority.

- [ ] **Step 1: Write the final invariant before documentation**

```python
def test_phase1_scope_uses_canonical_company_and_runtime_locations():
    root = Path(__file__).resolve().parents[3]
    scope = (root / "backend/app/workforce/agents/runtime/execution_scope.py").read_text()
    assert "class ExecutionScope" in scope
    assert "company_id" in scope
    assert not (root / "backend/agent_runtime/runtime/execution_scope.py").exists()
    organization = (root / "backend/core/organization/models.py").read_text()
    assert "class OperatingUnit" in organization
    assert "class Offering" in organization
```

- [ ] **Step 2: Verify RED or characterization state**

Run: `cd backend && pytest app/tests/test_architectural_invariants.py::test_phase1_scope_uses_canonical_company_and_runtime_locations -q`

Expected: PASS after Tasks 2 and 4. If it fails, fix the ownership breach before documenting Phase 1 as complete.

- [ ] **Step 3: Write the Phase 1 completion document**

Document:

1. Exact hierarchy and the explicit `Workspace == Company` decision.
2. Existing legacy rows behavior: null Offering means company-wide/legacy and cannot be returned under a narrower filter.
3. Scope resolution algorithm and the list of rejected tampering cases.
4. API request/response examples for unit, offering, initiative assignment, scope options, and workflow run.
5. UI behavior when retained scope becomes unavailable.
6. Deferred work: per-unit membership grants, bulk portfolio migration, extension visibility, graph palette filtering, and plugin/tool capability policy.

Update the contributor map with: `Need a scope? Call resolve_execution_scope in app/workforce/agents/runtime; never trust a client scope snapshot or create a scope resolver in Business Core.`

- [ ] **Step 4: Run full backend verification**

Run: `cd backend && pytest -q`

Expected: PASS with the existing skipped tests only.

- [ ] **Step 5: Run full relevant Flutter verification**

Run: `cd frontend && flutter test test/core/scope test/modules/workflows && flutter analyze lib/core/scope lib/core/widgets/company_scope_switcher.dart lib/modules/workflows lib/modules/tasks lib/modules/hologram_hub`

Expected: PASS with no new analyzer errors.

- [ ] **Step 6: Perform the manual vertical slice**

1. Sign in as an owner of one workspace.
2. Create `SaaS` Operating Unit and `COSA` Offering through the organization UI/API.
3. Attach an existing Initiative to COSA; leave a second Initiative unassigned or attach it to another Offering.
4. Choose COSA in the switcher; create/version/run a low-risk workflow.
5. Confirm its response and persisted run show `workspace_id`, `offering_id`, and no client-supplied privileges.
6. Confirm workflow list/run inspection excludes the other Offering under this narrowed selection.
7. Change the request offering ID to the other offering with the browser/network client; confirm backend returns 403 or 404 and no data.
8. Disable/reload a selected Offering in a second session; confirm UI clears the stale selection without widening it.

- [ ] **Step 7: Commit and tag the phase boundary**

```bash
git add docs/architecture/COSA_HARNESS_CONTRIBUTOR_EXTENSION_MAP.md docs/architecture/COSA_PHASE1_COMPANY_PORTFOLIO_SCOPE.md backend/app/tests/test_architectural_invariants.py
git commit -m "docs: complete company portfolio scope phase one"
git tag -a cosa-phase1-company-scope -m "Phase 1 company portfolio scope accepted"
```

## Phase 1 acceptance checklist

- [ ] One Workspace is demonstrably one Company; no duplicate Company table exists.
- [ ] Company can contain multiple Operating Units and Offerings; Offering kind is product, service, or hybrid.
- [ ] Existing Initiative and Task retain their identity and continue to work for legacy rows.
- [ ] A foreign or mismatched unit/offering/initiative cannot be resolved into `ExecutionScope`.
- [ ] Workflow run, approval, and artifact records preserve server-derived scope data at the relevant lifecycle point.
- [ ] Narrow workflow/portfolio filters never widen data visibility.
- [ ] The scope switcher is a UI convenience only; all authority is verified by backend membership/hierarchy resolution.
- [ ] Backend and relevant Flutter suites pass before Phase 2 begins.

## Phase 2 handoff

Phase 2 may consume only `ExecutionScope`, the portfolio scope API, and workflow snapshots from this phase. Extension manifests must declare supported scope levels and use this resolver; they must not add their own company/offering fields or trust a UI-selected scope. Do not start MCP discovery or PluginHost replacement until this phase's acceptance checklist is complete.
