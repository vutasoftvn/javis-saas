# COSA Phase 4 Visual Workflow Compiler and Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans task-by-task.

**Goal:** Upgrade the existing WorkflowDefinition/WorkflowVersion/WorkflowRun records and Flutter workflows module into a visual, deterministic workflow platform.

**Architecture:** `backend/app/integrations/workflows` remains the only workflow persistence/API/runtime owner; `frontend/lib/modules/workflows` remains the only workflow UI owner. A graph draft is untrusted authoring data. The server compiles it against node definitions, Extension Registry eligibility, ExecutionScope and Tool Invocation Pipeline; only immutable published versions run.

**Tech Stack:** FastAPI, SQLAlchemy/Alembic JSONB, Pydantic/JSON Schema, pytest, Flutter/GetX, graph canvas package selected after a focused dependency spike.

**Spec:** `docs/superpowers/plans/2026-08-20-cosa-extensible-harness-visual-workflows-rebuild.md` Phase 4; Phase 1–3 plans.

## Global Constraints

- Do not create a second workflow database model, router, runner, or Flutter canvas module.
- Published graph JSON, node versions, dependency versions and scope snapshot are immutable.
- Node metadata comes from core plus eligible Extension Registry metadata; Flutter cannot invent or enable nodes.
- Every Tool/Executor/Outcome node reaches Phase 3 ToolInvocationService; n8n remains an ExecutorProvider.
- Graph validation is deterministic: one entry, reachable terminals, typed ports, bounded cycles, approval before risky effects, scope/secret/extension eligibility, pinned acyclic subworkflows.
- Drafts may autosave with revision conflict detection; only authorized server publish can produce a runnable version.

## Tasks

### Task 1: Characterize current workflow migration base

**Files:** `backend/app/integrations/workflows/models.py`, `router.py`, `frontend/lib/modules/workflows/*`, `backend/app/tests/integrations/test_workflow_graph_baseline.py`.

- [ ] Write tests proving graph_jsonb/version/run/step/approval records and the existing UI module are the only migration base.
- [ ] Run `cd backend && pytest app/tests/integrations/test_workflow_graph_baseline.py -q`.
- [ ] Document current start-step behavior and every workflow API caller.
- [ ] Commit `test: characterize workflow graph migration base`.

### Task 2: Define graph wire contracts and node-definition registry

**Files:** Create `backend/app/integrations/workflows/graph/contracts.py`, `node_registry.py`, `backend/app/tests/integrations/test_workflow_graph_contracts.py`.

- [ ] RED test a v1 graph containing `nodes`, typed `ports`, `edges`, `entry_node_id`, `scope_requirements`, and pinned dependency versions.
- [ ] Implement Pydantic contracts for Trigger, Reasoning, Tool, Decision, Approval, Wait, Executor, Subworkflow and Outcome node definitions; each has input/output schemas, risk, scopes, permissions/secrets and compiler binding.
- [ ] Merge core definitions with eligible extension definitions server-side.
- [ ] GREEN test and commit `feat: define workflow graph contracts`.

### Task 3: Build deterministic compiler and validation report

**Files:** Create `graph/compiler.py`, `graph/schema_compatibility.py`, `graph/validation.py`, tests under `backend/app/tests/integrations/`.

- [ ] RED tests for missing/multiple entry, unreachable terminal, incompatible port schemas, unbounded cycle, disabled extension, missing secret, unsafe side effect without approval, and recursive subworkflow.
- [ ] Implement `compile_graph(graph, scope, registry) -> CompilationResult`, returning node/edge keyed diagnostics and a pinned execution plan.
- [ ] GREEN tests and commit `feat: compile governed workflow graphs`.

### Task 4: Add draft/validated/published/archived persistence lifecycle

**Files:** Modify workflow models/router, create Alembic migration, tests.

- [ ] RED tests that drafts mutate with revision token, publish requires valid compilation, published records reject mutation, archive blocks new runs but preserves history.
- [ ] Add nullable/additive lifecycle state, graph schema version, validation report, dependency snapshot, publish metadata and optimistic revision fields.
- [ ] GREEN migration/API tests and commit `feat: version publishable workflow graphs`.

### Task 5: Replace start-step initialization with resumable graph traversal

**Files:** Create `runtime/runner.py`, `runtime/state_machine.py`, `runtime/node_executors.py`; modify workflow router; tests.

- [ ] RED tests for a read-only Trigger→Tool→Outcome graph, approval pause/resume, wait/event pause, retry/idempotent resume, cancel and failure projection.
- [ ] Implement persisted node attempt transitions; invoke ToolInvocationService; store safe outputs/artifact refs; never re-execute an acknowledged side effect.
- [ ] GREEN integration tests and commit `feat: run compiled workflow graphs`.

### Task 6: Build Flutter Workflow Library and drag/drop Builder

**Files:** Modify existing workflows service/controller/view; create `models/graph_models.dart`, `widgets/canvas.dart`, `palette.dart`, `node_inspector.dart`, `validation_panel.dart`; Flutter tests.

- [ ] Run a dependency spike that compares two maintained Flutter graph-canvas packages against pan/zoom, typed ports, accessibility and license requirements; record selected package in an ADR before adding it.
- [ ] RED widget tests for eligible palette grouping, drag/drop, typed connection rejection, inspector edit, scope breadcrumb and server diagnostics.
- [ ] Implement draft load/save with revision token; render server node metadata only.
- [ ] GREEN tests/analyze and commit `feat: add visual workflow draft builder`.

### Task 7: Add Test/Publish and Run Inspector experiences

**Files:** Create workflow publish/run inspector widgets/controllers; modify service/routes; tests.

- [ ] RED tests for validation/risk/secret summary, dry-run input submission, publish confirmation, live node status, approval action, pause/cancel/retry and artifact links.
- [ ] Implement server-authorized actions and polling/event cursor updates; never render private reasoning/raw secret-bearing payloads.
- [ ] GREEN tests and commit `feat: inspect and publish governed workflows`.

### Task 8: Acceptance slice and documentation

**Files:** Create `docs/architecture/COSA_PHASE4_VISUAL_WORKFLOWS.md`; modify invariants/tests.

- [ ] Test an owner creating a low-risk read-only graph, validating, publishing, running and inspecting it under an Offering scope.
- [ ] Test backend rejection plus UI diagnostic for invalid edge/missing secret/disabled extension; test high-risk tool pause at approval.
- [ ] Run `cd backend && pytest -q`; `cd frontend && flutter test && flutter analyze`.
- [ ] Commit `docs: complete visual workflow compiler phase four`.

## Acceptance checklist

- [ ] Drag/drop graph is validated, versioned, published, executed and inspected through existing workflow ownership.
- [ ] A published run reproduces graph, scope and pinned dependencies.
- [ ] UI cannot bypass graph validation, extension eligibility, policy or approval.
- [ ] Graph runtime is deterministic, resumable and does not duplicate external actions.
