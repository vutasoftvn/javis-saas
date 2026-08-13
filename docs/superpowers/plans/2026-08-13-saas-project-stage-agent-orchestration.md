# SaaS Project Stage and Agent Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert a confirmed, tenant-scoped Project into an editable MVP-stage roadmap, stage-specific OKRs/12WY, approved capability-routed agent work, Vault Markdown evidence, and a Week 13 gate.

**Architecture:** Postgres is the source of truth for lifecycle, tenant access, configuration, state, versions and audit events. Existing Vault revision storage holds editable Markdown artefacts. System seed definitions are copied into workspace-local templates; an active stage snapshots the local template version so later edits and resets cannot mutate historical execution.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PostgreSQL/JSONB, existing Vault/MinIO, pytest, Flutter/GetX.

**Spec:** `docs/superpowers/specs/2026-08-13-saas-project-stage-agent-orchestration-design.md`

## Global Constraints

- Flutter only calls versioned `/api/v1` endpoints implemented in `backend/app`; do not add legacy references.
- Every new entity has `workspace_id` and relevant `brain_id`; every read/write verifies both server side.
- All primary keys use Snowflake IDs and every REST/Dart ID is a string.
- Runtime state is Postgres; Markdown artefacts use the existing Vault/MinIO revision lifecycle, never local files or SQLite.
- Generated outputs remain drafts until founder confirmation. Legal/Compliance never self-approves and high-risk services cannot be autonomous.
- Preserve unrelated dirty/staged work; stage exact paths for every commit.

## File Structure

- `backend/app/modules/strategy/models.py`: Project brief, MVP stages, revisions, local templates/versions, capabilities, agents, assessments, assignments and audit entities.
- `backend/alembic/versions/<revision>_project_stage_orchestration.py`: constraints, tenant indexes and stage-cycle links.
- `backend/app/core/tenancy.py`: scoped accessors for stage/template/agent/assessment/assignment.
- `backend/app/modules/strategy/{template_service,routing_service,project_orchestration_service,vault_artifact_service,seed_templates}.py`: separated domain services.
- `backend/app/modules/strategy/routers/{template_router,project_orchestration_router}.py`: thin `/api/v1/strategy` handlers.
- `backend/app/modules/strategy/schemas/project_orchestration_schemas.py`: strict input/output contracts.
- `backend/app/tests/test_{project_orchestration,template,routing,vault_artifact}_*.py`: service and API regression coverage.
- `frontend/lib/data/services/strategy_service.dart`: API client methods.
- `frontend/lib/modules/strategy/controllers/project_orchestration_controller.dart`: isolated GetX state.
- `frontend/lib/modules/strategy/views/{project_kickoff_view,project_stage_workspace_view,template_library_view}.dart`: founder and admin experiences.
- `frontend/test/project_{orchestration_controller,kickoff_view}_test.dart`: Flutter tests.

### Task 1: Add the tenant-safe stage and template data model

**Files:** modify `backend/app/modules/strategy/models.py`, `backend/app/db/base.py`, `backend/app/core/tenancy.py`; create migration and `backend/app/tests/test_project_orchestration_models.py`.

**Interfaces produced:** `MvpStage`, `StageRevision`, `WorkspaceTemplate`, `WorkspaceTemplateVersion`, `CapabilityDefinition`, `WorkspaceAgent`, `StageServiceAssessment`, `StageAssignment`, `StrategyAuditEvent`; `get_mvp_stage_scoped()`.

- [ ] Write the failing invariants.

```python
def test_only_one_active_stage_is_allowed_per_project(db):
    create_stage(status="ACTIVE")
    with pytest.raises(IntegrityError):
        create_stage(status="ACTIVE")

def test_cross_tenant_stage_lookup_is_not_found(db):
    with pytest.raises(HTTPException, match="MVP stage not found"):
        get_mvp_stage_scoped(db, foreign_stage_id, ws_id, brain_id)
```

- [ ] Run `cd backend && pytest app/tests/test_project_orchestration_models.py -v`; expect failure because models/getter are absent.
- [ ] Implement models using `generate_snowflake_id`, a `(project_id, sequence_no)` unique constraint, PostgreSQL partial unique index `status = 'ACTIVE'`, and `workspace_id, project_id, status` indexes. Add `Project.description` and nullable `Project.active_stage_id`; add nullable `mvp_stage_id` (not `stage_id` — `WeeklyPlan`, `Milestone` and `GateDecision` already use `stage_id` as a foreign key to the unrelated `CycleStage`) to `OkrCycle` and `TwelveWeekCycle`, with an explicit foreign key to `mvp_stages.id`.
- [ ] Implement `get_mvp_stage_scoped(db, stage_id, workspace_id, brain_id)` with all three filters and HTTP 404.
- [ ] Create and inspect migration: `cd backend && alembic revision --autogenerate -m "project stage orchestration"`; ensure it includes no unrelated changes.
- [ ] Run `pytest app/tests/test_project_orchestration_models.py -v && alembic upgrade head`; expect pass.
- [ ] Commit only these paths with `git commit -m "feat: add project stage orchestration models"`.

### Task 2: Provision editable workspace-local templates and agent catalog

**Files:** create `seed_templates.py`, `template_service.py`, `routers/template_router.py`, `schemas/project_orchestration_schemas.py`; modify router registration; add `test_template_service.py`, `test_template_endpoints.py`.

**Interfaces produced:** `TemplateService.provision_workspace_templates()`, `reset_template()`, `create_local_version()` and `/api/v1/strategy/workspace-templates` admin endpoints.

- [ ] Write failing tests.

```python
def test_provision_is_idempotent_and_creates_six_local_templates(service):
    assert len(service.provision_workspace_templates(ws_id, brain_id)) == 6
    assert service.provision_workspace_templates(ws_id, brain_id) == []

def test_reset_archives_local_version_without_changing_stage_snapshot(service):
    before = activate_stage_with_template_version(2)
    reset = service.reset_template(template_id, user_id)
    assert before.template_version_no == 2
    assert reset.active_version_no == 3
```

- [ ] Run `cd backend && pytest app/tests/test_template_service.py -v`; expect fail.
- [ ] Define six system seeds: Core Startup, Technology & Security, Finance & Unit Economics, Legal & Compliance, Growth & GTM, Operations. Copy them into `WorkspaceTemplate` + version 1 rows; never expose seeds as tenant-editable records.
- [ ] Store local `config_jsonb`, optional Vault playbook document ID, version number, source seed key, default flag and archive status. Admin-only reset archives the active local version and creates a new local version from a seed.
- [ ] Add Pydantic enums: stage statuses, service disposition (`REQUIRED`, `RECOMMENDED`, `OPTIONAL`) and execution mode (`MANUAL`, `AI_ASSISTED`, `AUTONOMOUS`). IDs parse from string and serialize back to string.
- [ ] Add endpoint test asserting a non-admin receives 403 on reset; run both template test files; expect pass.
- [ ] Commit: `git commit -m "feat: add workspace local capability templates"`.

### Task 3: Create Vault Markdown stage artefacts and roadmap confirmation

**Files:** create `vault_artifact_service.py`, `project_orchestration_service.py`, `routers/project_orchestration_router.py`; register router; add vault/roadmap service and endpoint tests.

**Interfaces produced:** `POST /projects/{project_id}/mvp-roadmap:generate`, `PUT .../mvp-roadmap`, `POST .../mvp-roadmap:confirm`; `create_stage_artifact()`.

- [ ] Write failing tests.

```python
def test_roadmap_generation_only_returns_drafts(service):
    result = service.generate_roadmap(project_id, user_id)
    assert all(s["status"] == "DRAFT" for s in result["stages"])
    assert query_mvp_stages(project_id) == []

def test_confirmation_persists_ordered_stages_and_markdown(service):
    result = service.confirm_roadmap(project_id, valid_three_stage_draft, user_id)
    assert [s.sequence_no for s in result.stages] == [1, 2, 3]
    assert result.roadmap_document_id
```

- [ ] Run roadmap tests; expect fail.
- [ ] Reuse `VaultRepository`, not a new object-store client. Stage artefact paths must be `projects/{project_id}/stages/{stage_id}/{kind}.md` (no leading slash - `VaultRepository` builds its object key as `f"{brain_id}/{path}/{sha256}"`, and a leading slash there produces a double slash that MinIO rejects); store Vault document links with workspace/brain/project/stage scope and create revisions for edits.
- [ ] Build AI context from scoped Foundation plus `Project.description`. Validate provider output before returning/persisting it:

```python
class RoadmapDraft(BaseModel):
    stages: list[RoadmapStageDraft] = Field(min_length=2, max_length=4)
class RoadmapStageDraft(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    hypothesis: str = Field(min_length=20)
    scope: list[str] = Field(min_length=1)
    non_goals: list[str]
    exit_criteria: list[str] = Field(min_length=1)
```

- [ ] On AI schema failure return 422 and persist nothing. Confirmation replaces only unconfirmed roadmap drafts, writes a Vault roadmap revision, and adds an audit event.
- [ ] Run roadmap/vault endpoint tests including a foreign-workspace 404; expect pass.
- [ ] Commit: `git commit -m "feat: add AI MVP roadmap confirmation"`.

### Task 4: Generate reviewed stage-only OKR, 12WY and capability-routing plans

**Files:** create `routing_service.py`; modify orchestration service, `okrs_router.py`, `execution_router.py`; add orchestration/routing tests.

**Interfaces produced:** `POST /projects/{project_id}/stages/{stage_id}:plan`, `POST ...:activate`, `POST .../service-assessment:generate`, `POST .../service-assessment:confirm`.

- [ ] Write failing transactional tests.

```python
def test_activation_creates_one_stage_cycle_and_twelve_week_rows(service):
    result = service.activate_stage(project_id, stage_id, approved_plan, user_id)
    assert result.stage.status == "ACTIVE"
    assert result.okr_cycle.stage_id == stage_id
    assert len(result.weekly_plans) == 12

def test_regulated_service_is_required_but_never_autonomous(service):
    item = service.generate_assessment(regulated_stage_id, user_id).by_capability("legal_compliance")
    assert item.disposition == "REQUIRED"
    assert item.professional_review_required and item.execution_mode == "MANUAL"
```

- [ ] Run test files; expect fail.
- [ ] `:plan` returns only a validated preview: 1–3 objectives, 2–5 measurable KRs each, exactly 12 weekly focus rows. It must never call the old destructive `/okrs/generate-ai` behaviour.
- [ ] `:activate` writes in one transaction: mark one `CONFIRMED` stage active; snapshot its local template version; create OkrCycle, TwelveWeekCycle and exactly 12 WeeklyPlan rows; link generated commitments to a KR; set `Project.active_stage_id`. Reject a second active stage with HTTP 409.
- [ ] Routing first validates workspace-enabled capabilities and deterministic policy, then validates AI recommendations. Required/recommended/optional service assessment includes reason, risk, expected output and unavailable capabilities. Confirmation creates only founder-approved assignment drafts; no external work is dispatched.

```python
if capability.professional_review_required:
    assessment.execution_mode = "MANUAL"
if capability.risk_level in {"HIGH", "REGULATED"} and assessment.execution_mode == "AUTONOMOUS":
    raise HTTPException(422, "High-risk capability cannot run autonomously")
```

- [ ] Run tests for plan preview (no persisted cycle), second-stage conflict, unavailable capability and approval filtering; expect pass.
- [ ] Commit: `git commit -m "feat: activate stages with routed agent work"`.

### Task 5: Add active-stage revision preview and Week 13 gate

**Files:** modify orchestration service/router/execution router; add focused tests.

**Interfaces produced:** `POST /stages/{stage_id}:preview-revision`, `POST ...:apply-revision`, `POST .../week-13:generate`, `POST .../week-13:confirm`.

- [ ] Write failing tests.

```python
def test_material_revision_preserves_checked_in_evidence(service):
    impact = service.preview_stage_revision(stage_id, changed_scope)
    assert str(approved_evidence_id) in impact.preserve_evidence_document_ids
    assert str(unstarted_plan_id) in impact.supersede_weekly_plan_ids

def test_advance_completes_current_stage_but_does_not_activate_next(service):
    result = service.confirm_week13(stage_id, "GO", user_id)
    assert result.current_stage.status == "COMPLETED"
    assert result.next_stage.status == "CONFIRMED"
```

- [ ] Run tests; expect fail.
- [ ] Persist a `StageRevision` containing before/after snapshots and impact preview. Material changes to hypothesis, scope or exit criteria supersede only unstarted generated plans/assignments; completed commitments and approved Vault revisions remain immutable. Apply requires the exact pending-preview ID and appends audit events.
- [ ] Week 13 aggregate explicitly separates calculated facts (KR check-ins, completed commitments, approved evidence, missing evidence) from AI recommendation. Record the outcome through the existing `GateDecision` model and `CycleGovernanceService.record_gate_decision` — add a nullable `mvp_stage_id` column rather than a parallel table. Valid decisions are `GO` (advance), `ITERATE`, `HOLD` (continue), `STOP`, `PIVOT`. Confirming a decision closes/archives the existing cycle; it never activates the next stage without a later founder confirmation.
- [ ] Run service and endpoint tests; expect pass.
- [ ] Commit: `git commit -m "feat: add audited stage revisions and week 13 gates"`.

### Task 6: Deliver founder and workspace-admin Flutter flows

**Files:** modify `frontend/lib/data/services/strategy_service.dart`, `strategy_binding.dart`, `strategy_view.dart`; create controller and three views; create controller/widget tests.

**Interfaces consumed:** every Task 2–5 endpoint; all Snowflake IDs remain `String`.

- [ ] Write failing tests.

```dart
test('roadmap draft does not activate a stage', () async {
  await controller.generateRoadmap('100');
  expect(controller.roadmapDraft['stages'], hasLength(3));
  expect(controller.activeStage.value, isNull);
});

testWidgets('legal review requirement is visible before activation', (tester) async {
  await tester.pumpWidget(buildKickoff(legalAssessmentController));
  expect(find.text('Cần chuyên gia phê duyệt'), findsOneWidget);
});
```

- [ ] Run `cd frontend && flutter test test/project_orchestration_controller_test.dart test/project_kickoff_view_test.dart`; expect failure.
- [ ] Implement typed service calls and an injected `ProjectOrchestrationController`; failed calls keep the last reviewed draft and set an actionable error.
- [ ] Build a short founder flow: brief → editable roadmap → service-plan confirmation → reviewed execution plan → activate. `ProjectStageWorkspaceView` defaults to current-week commitments, KR link and evidence state. All edits open impact preview before apply.
- [ ] Put `TemplateLibraryView` in workspace settings, not kickoff. It edits local template versions and has a reset confirmation explaining that stage snapshots are unchanged.
- [ ] Run Flutter tests, `flutter analyze lib`, and forbidden-reference scan; expect all pass and zero `rg` matches.
- [ ] Update `DEPLOYMENT.md`: Alembic migration before traffic, idempotent backend provisioning of local template seeds, Vault/MinIO required, and no direct Flutter object-storage access.
- [ ] Commit: `git commit -m "feat: add SaaS project stage workflow"`.

## Final Verification

- [ ] Run backend: `cd backend && pytest app/tests/test_project_orchestration_models.py app/tests/test_template_service.py app/tests/test_template_endpoints.py app/tests/test_project_orchestration_service.py app/tests/test_project_orchestration_endpoints.py app/tests/test_routing_service.py -v`.
- [ ] Run migration round-trip: `cd backend && alembic upgrade head && alembic downgrade -1 && alembic upgrade head`.
- [ ] Run frontend: `cd frontend && flutter test test/project_orchestration_controller_test.dart test/project_kickoff_view_test.dart && flutter analyze lib`.
- [ ] Run boundary scan: `cd frontend && rg -n --glob '!build/**' '(:8888|backend/server|javis/|web_socket_channel)' lib` and expect no output.
- [ ] Run `git diff --check`, then request code review before merge.
