# COSA Phase 6 Runtime Events, Hologram Projections and Local-First Sessions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans task-by-task.

**Goal:** Deliver replayable operational visibility for workflows and agents through one canonical event stream and safe Hologram projections.

**Architecture:** Decide and record one authority before coding: Postgres append-only runtime events are the primary server event log; SQLite is an optional local cache/offline projection, not a competing server authority. Existing audit records and OpenTelemetry are projections/telemetry linked by correlation/causation IDs. Hologram and Run Inspector read server-built projections, never raw model reasoning or arbitrary logs.

**Tech Stack:** PostgreSQL/SQLAlchemy/Alembic, FastAPI, existing agent event/audit models, OpenTelemetry, Flutter/GetX, pytest.

**Spec:** Master rebuild plan Phase 6; Phase 1 ExecutionScope, Phase 3 Invocation Pipeline and Phase 4 Workflow Runtime plans.

## Global Constraints

- Event records are append-only facts; corrections are later events, never in-place event mutation.
- Every event has schema version, event ID, occurred time, scope snapshot/reference, correlation ID, causation ID, actor/source and redacted payload.
- No private reasoning, secret, raw credential, provider request/response, or unbounded tool output enters the event log/projection/UI.
- Audit and tracing remain projections; neither creates a second session authority.
- Pause/resume uses persisted workflow version, scope snapshot and event cursor; it must not infer a new scope.
- SQLite implementation, if enabled, is cache/projection only and must tolerate deletion/rebuild from server cursor.

## Tasks

### Task 1: Record the event-authority ADR and characterize existing stores

- [ ] Create `docs/architecture/adr/ADR-006-runtime-event-authority.md` and tests inventorying AgentEventRecord, AgentToolCall, workflow steps, audit log, OTel and SQLite scaffold.
- [ ] Document Postgres primary/SQLite cache ruling, retention, payload redaction and recovery rule.
- [ ] Run characterization tests; commit `docs: select runtime event authority`.

### Task 2: Define canonical event contracts and append-only store

- [ ] Create `backend/app/workforce/events/{contracts.py,event_store.py,redaction.py}` and tests.
- [ ] RED tests for versioned event serialization, immutable payload, correlation/causation/scope fields and recursive secret redaction.
- [ ] Implement `append(event)` and cursor-based `read(scope, after_cursor, limit)` against Postgres; no update/delete API.
- [ ] GREEN tests; commit `feat: add canonical runtime event store`.

### Task 3: Emit events from one compiled workflow path

- [ ] Modify Phase 4 runner/node executors and Phase 3 invocation projections.
- [ ] RED integration test for run.created, node.started, tool.requested, tool.completed or approval.requested, artifact.created and run terminal event with one correlation ID.
- [ ] Implement event emission after durable state transition; retry must not create duplicate external action events.
- [ ] GREEN test; commit `feat: emit workflow lifecycle events`.

### Task 4: Build deterministic projections

- [ ] Create `backend/app/workforce/events/projections/{workflow_run.py,task.py,approval.py,agent_health.py,artifact.py}` and read-model tests.
- [ ] RED tests replaying ordered events into same Run/Task/Approval state, including pause/resume/failure.
- [ ] Implement idempotent projection cursor/checkpoint per projection; record schema upgrade failures as observable projection errors.
- [ ] GREEN tests; commit `feat: project runtime events into operating state`.

### Task 5: Add event cursor APIs and reconnect behavior

- [ ] Create events router/service under canonical workforce/platform event ownership and tests.
- [ ] RED tests for tenant/scope tampering, cursor continuation, redacted response and stale cursor recovery.
- [ ] Implement scope-authorized event/projection endpoints and optional SSE/WebSocket stream with cursor acknowledgement; REST polling remains fallback.
- [ ] GREEN tests; commit `feat: expose replayable runtime projections`.

### Task 6: Implement optional SQLite local projection cache

- [ ] Create `frontend` or local-worker cache adapter only after server replay works; do not promote old SQLite scaffold to authority.
- [ ] RED tests for cache rebuild from cursor, offline read of safe projection, cursor gap detection and cache deletion recovery.
- [ ] Implement cache schema storing projection/cursor only; never raw event payload containing secrets/private reasoning.
- [ ] GREEN tests; commit `feat: cache safe runtime projections locally`.

### Task 7: Build Hologram and Run Inspector projection consumers

- [ ] Modify existing `frontend/lib/modules/hologram_hub` and workflow Run Inspector services/controllers/widgets.
- [ ] RED widget tests for scope/current node/progress/risk/approval/verification/artifact cards, reconnect cursor and no private reasoning rendering.
- [ ] Implement projection-driven cards and timeline; render event status/summary only.
- [ ] GREEN Flutter tests/analyze; commit `feat: render hologram from runtime projections`.

### Task 8: Verify pause/resume and operating runbook

- [ ] Test a workflow pauses for approval, process reconnects, resumes exact published version/scope, and Hologram reconstructs state from cursor.
- [ ] Test audit and OTel share correlation ID without duplicating secret payload.
- [ ] Run backend and Flutter suites; write `docs/architecture/COSA_PHASE6_RUNTIME_EVENTS.md` plus operational replay/runbook guidance.
- [ ] Commit `docs: complete runtime events and hologram phase six`.

## Acceptance checklist

- [ ] One server event authority is explicit and append-only.
- [ ] Paused run resumes exact version/scope and emits deterministic lifecycle state.
- [ ] Hologram/Run Inspector use projections, not raw reasoning/log inference.
- [ ] Reconnect by cursor is safe and local cache can be rebuilt.
- [ ] Audit, trace and event records correlate without secrets.
