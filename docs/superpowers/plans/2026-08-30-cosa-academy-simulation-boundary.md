# COSA Academy and Simulation Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Academy/Simulation as a separate learning product that can teach the 54-lesson lifecycle taxonomy and run synthetic scenarios, while making it structurally impossible for lesson completion, simulation output or synthetic evidence to affect a live project, its evidence ledger, gate recommendation or lifecycle state.

**Architecture:** Academy owns its own aggregate, storage schema, API namespace, UI routes and artifact namespace. A learner may manually export a clearly labelled template from Academy to a live workspace, but that creates a new live **artifact draft** with no evidence/gate linkage; a human must attach reviewed real-world sources before it can become live evidence. No Academy service imports Company Strategy evidence/gate/transition repositories and no live lifecycle service imports Academy types.

**Tech Stack:** TypeScript/Encore/Drizzle/PostgreSQL, Python/FastAPI/Pydantic/Pytest, Flutter/Dart.

**Spec:** `docs/architecture/plans/2026-08-30-cosa-lifecycle-skill-operating-model.md`

## Entry gate and scope

Academy is a product line, not a prerequisite to COSA operating. Start only after Tranche A has established the production evidence boundary. The curriculum may mirror the attached 6-stage/54-lesson framework, but week/module completion is never a project stage and course scores are never a metric, evidence strength, gate requirement or capability enablement signal.

**Out of scope:** copying Academy attempts into live evidence, automatic graduation, live customer/CRM/financial data use in a simulation, real-world task creation, public outreach, stage transition, gate pass, skill auto-publish or synthetic performance used in PMF/maturity scoring.

## Global constraints

- Academy uses the separate schema/name `academy`; production lifecycle data stays in Company `strategy` and Agent `agent` schemas.
- Academy identifiers are typed/prefixed `academy_*`; live `project_id`, `evidence_id`, `gate_evaluation_id`, `metric_contract_id`, `pilot_id` and live capability refs are rejected by Academy write APIs.
- Academy artifacts use `academy-artifact://`; production evidence accepts only approved live artifact/source references and rejects that scheme.
- Simulation inputs are curated synthetic fixtures or sanitized templates. Every response/artifact bears `synthetic: true`, scenario version and a disclaimer.
- Academy can read a published, public-safe **skill curriculum descriptor** (title/objectives/skills taxonomy) but never a runtime `SkillSpec`, pinned hash, capability list, prompts, workspace sources or connector grant.

## File map

| Path | Responsibility |
| --- | --- |
| `services/company/academy/*` | Independent Company service/API for programs, lessons, scenarios and attempts. |
| `services/company/shared/db/schema/academy.ts` | Academy-only tables and typed references. |
| `apps/cosa/academy/*` | Academy learning/simulation orchestration without capability gateway access. |
| `frontend/lib/modules/academy/*` | Academy route, progress and scenario UX. |
| `services/company/operations/strategy/*` | Explicit rejection of Academy artifact/evidence/gate inputs. |
| `docs/academy/*` | Curriculum mapping and safety copy; not a production skills registry. |

---

### Task 1: Establish compile-time and API-level separation rules

**Files:**
- Create: `services/company/shared/db/schema/academy.ts`
- Create: `services/company/academy/contracts.ts`
- Create: `services/company/academy/academy.service.ts`
- Create: `services/company/academy/handlers/index.ts`
- Modify: `services/company/shared/db/schema/index.ts`
- Modify: `services/company/operations/strategy/handlers/evidence.handler.ts`
- Test: `services/company/academy/tests/academy-boundary.test.ts`
- Test: `services/company/operations/strategy/tests/evidence-ingestion.test.ts`

**Interfaces:**
- Produces branded/type-distinct `AcademyProgramId`, `AcademyAttemptId`, `AcademyArtifactRef` and `SyntheticScenarioRef`.
- `assertNotAcademyReference(ref)` is called before production artifact/evidence/gate persistence and rejects `academy-artifact://` and `academy_*` references.

- [ ] **Step 1: Write failing boundary tests**

    await expect(recordEvidence({ artifactRef: 'academy-artifact://lesson/1' }))
      .rejects.toThrow(/academy|synthetic/i);
    await expect(createAcademyAttempt({ projectId: liveProject.id })).rejects.toThrow(/projectId/i);
    expect(academySchemaTables()).not.toContain('evidence');

Add a static import test: `services/company/academy/**` cannot import `operations/strategy` service/handler modules, and strategy cannot import `academy/**`.

- [ ] **Step 2: Run the tests**

    cd services/company && pnpm exec vitest run academy/tests/academy-boundary.test.ts operations/strategy/tests/evidence-ingestion.test.ts --no-file-parallelism

- [ ] **Step 3: Implement distinct contracts and rejection**

Create the Academy schema/container but no foreign keys into `strategy.projects`, evidence, gate evaluation, metric or task tables. Use account/workspace entitlement only where required for access; attempts link to an Academy learner profile, not a project. Add the production reject helper at every evidence create/ingest/review entry point and assert it before database writes.

- [ ] **Step 4: Verify and commit**

    cd services/company && pnpm typecheck && pnpm exec vitest run academy/tests/academy-boundary.test.ts operations/strategy/tests/evidence-ingestion.test.ts operations/strategy/tests/strategy-handlers.test.ts --no-file-parallelism
    git add services/company/shared/db/schema/academy.ts services/company/shared/db/schema/index.ts services/company/academy services/company/operations/strategy/handlers/evidence.handler.ts services/company/academy/tests/academy-boundary.test.ts services/company/operations/strategy/tests/evidence-ingestion.test.ts
    git commit -m "feat(academy): isolate learning domain from evidence"

### Task 2: Build Academy program, lesson and progress aggregates

**Files:**
- Create: `services/company/academy/migrations/001_academy_programs.up.sql`
- Create: `services/company/academy/migrations/001_academy_programs.down.sql`
- Create: `services/company/academy/handlers/program.handler.ts`
- Create: `services/company/academy/handlers/progress.handler.ts`
- Create: `services/company/academy/tests/academy-progress.test.ts`
- Create: `docs/academy/lifecycle-curriculum-map.md`

**Interfaces:**
- Produces `AcademyProgram`, `AcademyModule`, `AcademyLesson`, `AcademyEnrollment` and `AcademyLessonAttempt`.
- APIs are under `/academy/*`; completion is `NOT_STARTED|IN_PROGRESS|COMPLETED`, with no lifecycle/gate field.

- [ ] **Step 1: Write failing progress tests**

    const enrollment = await enroll(learner, program.id);
    await completeLesson(enrollment.id, lesson.id, { reflection: '...' });
    expect((await getEnrollment(enrollment.id)).progress.completedLessons).toBe(1);
    expect(await projectStageChanged(liveProject.id)).toBe(false);

Test idempotent lesson completion, tenant/learner access and an attempted payload containing `gateEvaluationId`, `lifecycleStage` or `evidenceId` rejection.

- [ ] **Step 2: Implement and verify**

Create the 6 modules/54 lessons as versioned content records or seed descriptors from `docs/academy/lifecycle-curriculum-map.md`; each map records a learning objective, practice type and related lifecycle topic, not a runtime stage requirement. Run focused tests, then commit with `feat(academy): add curriculum progress`.

### Task 3: Create a synthetic simulation engine with no live capability surface

**Files:**
- Create: `apps/cosa/academy/simulation/contracts.py`
- Create: `apps/cosa/academy/simulation/engine.py`
- Create: `apps/cosa/academy/simulation/scenario_store.py`
- Create: `apps/cosa/academy/simulation/scenarios/p0_discovery_v1.yaml`
- Create: `apps/cosa/academy/simulation/scenarios/p3_pilot_v1.yaml`
- Create: `tests/apps/cosa/academy/test_simulation_engine.py`
- Create: `tests/apps/cosa/academy/test_simulation_boundary.py`

**Interfaces:**
- Produces `SimulationAttempt`, `SyntheticArtifact` and `SimulationFeedback`; the engine accepts scenario fixtures and learner choices, returns deterministic/advisory scoring and never receives `CosaAgentPlane`, `CompanyServiceClient`, connector grant, live artifact repository or capability gateway.

- [ ] **Step 1: Write failing isolation tests**

    engine = SimulationEngine(scenario_store=store)
    result = await engine.start('p0_discovery_v1', learner_id='academy_l_1')
    assert result.artifact_ref.startswith('academy-artifact://')
    assert result.synthetic is True
    assert 'capability_gateway' not in inspect.signature(SimulationEngine).parameters

Test hostile text inside scenario material, random learner input and attempts to pass live workspace/project/connector IDs. The result must treat scenario text as data and reject live IDs.

- [ ] **Step 2: Implement, run and commit**

    .venv/bin/python -m pytest tests/apps/cosa/academy/test_simulation_engine.py tests/apps/cosa/academy/test_simulation_boundary.py -q

Use a closed scenario schema: version, synthetic dataset, decision checkpoints, expected reasoning rubric and permitted output fields. Ensure the response includes `synthetic=true`, scenario version and “không phải evidence sản xuất”. Commit with `feat(academy): add isolated synthetic simulations`.

### Task 4: Permit a one-way template export, never evidence export

**Files:**
- Create: `services/company/academy/handlers/template-export.handler.ts`
- Create: `apps/cosa/academy/template_export.py`
- Modify: `packages/agent/artifacts/models.py`
- Create: `tests/apps/cosa/academy/test_template_export.py`
- Test: `services/company/academy/tests/academy-boundary.test.ts`

**Interfaces:**
- Produces `AcademyTemplateExport` `{ templateKind, body, academySourceRef, disclaimer }` and a live `WorkspaceArtifact` of kind `academy_template_draft`.
- It does not produce an Evidence candidate, source ingestion record, gate input, metric snapshot or task.

- [ ] **Step 1: Write failing one-way tests**

    artifact = await exportTemplate(academyAttempt.id, workspaceA)
    assert artifact.kind == 'academy_template_draft'
    assert artifact.metadata['academy_source_ref'].startswith('academy-artifact://')
    await expect(createEvidenceFromArtifact(artifact.id)).rejects.toThrow(/academy_template_draft|real source/i)

Also assert the export requires an explicit human click/confirmation and no background export occurs on completion.

- [ ] **Step 2: Implement, verify and commit**

The export handler strips any simulation score, synthetic claim and model feedback from the artifact body except a permanent provenance/disclaimer block. Production evidence validation rejects artifact kind `academy_template_draft` until a human replaces it with independent real-world sources through the normal evidence intake. Run TypeScript/Python boundary tests and commit with `feat(academy): export labelled learning templates`.

### Task 5: Build a clearly separated Academy experience in Flutter

**Files:**
- Create: `frontend/lib/modules/academy/services/academy_service.dart`
- Create: `frontend/lib/modules/academy/models/academy_models.dart`
- Create: `frontend/lib/modules/academy/views/academy_view.dart`
- Create: `frontend/lib/modules/academy/views/widgets/{lesson_progress_card,simulation_workspace,synthetic_disclaimer_banner}.dart`
- Modify: `frontend/lib/core/routes/app_routes.dart`
- Test: `frontend/test/academy_service_test.dart`
- Test: `frontend/test/academy_view_test.dart`

**Interfaces:**
- Produces an `/academy` route with course progress and simulations visually labelled “Học tập / mô phỏng”, distinct from Project Navigator/Strategy views.

- [ ] **Step 1: Write widget/service tests**

Assert each scenario result carries a persistent synthetic banner, completion does not call any strategy/evidence/stage service, template export has a confirmation modal and the default route does not show a “pass stage” or “apply evidence” action.

- [ ] **Step 2: Implement, run and commit**

    cd frontend && flutter analyze && flutter test test/academy_service_test.dart test/academy_view_test.dart

Render practice feedback as a learning rubric, not an operational score. Commit with `feat(academy): add isolated learning experience`.

### Task 6: Add cross-domain safety gates and release evidence

**Files:**
- Create: `tests/integration/test_academy_production_firewall.py`
- Create: `services/company/academy/tests/academy-production-contract.test.ts`
- Create: `frontend/test/academy_production_firewall_test.dart`
- Modify: `.github/workflows/quality.yml`
- Modify: `docs/architecture/plans/2026-08-30-cosa-lifecycle-skill-operating-model.md`

- [ ] **Step 1: Write the firewall acceptance test**

Create an Academy completion/simulation/template export then assert no row/event exists in strategy evidence, ingestion, gate evaluation, stage transition, metric snapshot, pilot run, task, approval or capability-enablement repositories. Attempt all forbidden reference types from both API and UI. Run repository import/dependency checks and assert the separate `/academy` namespace.

- [ ] **Step 2: Enforce CI and commit**

    cd services/company && pnpm exec vitest run academy/tests/academy-boundary.test.ts academy/tests/academy-production-contract.test.ts --no-file-parallelism
    .venv/bin/python -m pytest tests/apps/cosa/academy tests/integration/test_academy_production_firewall.py -q
    cd frontend && flutter test test/academy_production_firewall_test.dart

Add the three commands to CI and record curriculum version, synthetic-data review owner and firewall acceptance evidence in the architecture spec. Commit with `test(academy): enforce production isolation`.

## Definition of Done

- [ ] Academy data, API, types, artifacts and UI live in a separate bounded context and namespace.
- [ ] Lesson completion and simulation output cannot be used as a live source/evidence/gate/metric/pilot/task/capability-enablement input.
- [ ] Synthetic scenario output is permanently labelled and has no live capability or connector access.
- [ ] The only export is an explicitly confirmed, labelled template draft; it remains ineligible for live evidence.
- [ ] API, static import, database/event and Flutter firewall tests are green in CI.

## Self-review

**Spec coverage:** Implements roadmap Order 7 and preserves the user’s key invariant: Academy/Simulation is a separate product line whose synthetic output never affects live gates.

**Intentional exclusions:** Adaptive coaching based on live customer data, scenario auto-generation from internal data, runtime production skills/capabilities and any Academy-to-project state synchronization are deliberately excluded.

**Type consistency:** Academy uses `AcademyArtifactRef`/`academy-artifact://`; production uses ordinary source/artifact provenance. The one-way export produces an `academy_template_draft`, never an Evidence object.
