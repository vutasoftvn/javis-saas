# mCOSA Update Roadmap — Gap Analysis & Phased Plan

## Context

`mCOSA_Technology_Implementation_Blueprint_V10_Hybrid_Workforce.md` is a 172-section
aspirational architecture document (V1→V10) describing a full "Company Operating
System": Flutter+GetX client, FastAPI modular monolith, PostgreSQL system-of-record,
MCP tool gateway, Claude Code developer worker, local execution nodes, an
Outcome/Run/Artifact execution model, a Miva/mCOSA Hologram Hub ambient UI, and
eventually a Hybrid Workforce (Human + AI org chart) layer. It is not a spec for a
single change — it's a multi-quarter north star.

This plan's job is to turn that into an actionable, sequenced roadmap grounded in what
`backend/app` and `frontend/lib` **actually contain today** (verified by direct code
inventory, not assumption), so each phase builds on real code instead of re-deriving
the blueprint from scratch. The user has an image reference for the "trang chính"
(home page) — the Miva Hologram Hub layout (§98–110 of the blueprint) — and wants that
built as the first concrete phase, ahead of deeper governance/execution-domain work.

**This roadmap is a planning document, not implementation.** Implementation starts in
a future session, phase by phase, each following CLAUDE.md's migration method
(contract → tenant-scoped test → implementation → Flutter wiring → regression test).

## Current State Snapshot (verified, not aspirational)

**Backend (`backend/app`, FastAPI modular monolith, all routes under `/api/v1/*`)**
already implements a substantial slice of the blueprint's *technical* foundation:
- Strategy OS: canvases, PESTEL/SWOT/TOWS, OKRs, 12-week execution — extensive (~45+45 routes across `strategy/router.py`, `okrs_router.py`, `execution_router.py`).
- Marketing OS: ~65 endpoints (context, campaigns, experiments, learnings, skills, approvals, loops, decisions) — the most complete domain module.
- Vault: real hybrid RAG (`pgvector` cosine + Postgres FTS) in `vault/retrieval_service.py`, async chunking pipeline.
- MCP Hub: real, non-trivial implementation (`integrations/mcp/mcp_hub.py`, 1147 lines) — permission tiers, namespacing, audit, rate limiting.
- Workflow runtime: `workflows/workflow_runtime.py` — capability graph, checkpointing, canary; `workflow_approvals` table + `/steps/{id}/approve` endpoint already exist.
- Worker: `worker_main.py` — polling-based (no Celery/Redis, matches blueprint's "defer queue" guidance), runs chat loop, channel loop, chunking/schedule/task dispatch.
- Tenancy: `core/tenancy.py` has explicit scoped-lookup helpers; workspace_id enforcement is inconsistent across modules (workflows module lowest coverage: 1/6 files).

**Gaps that matter for this plan:**
- `platform.audit_logs` table exists but **nothing writes to it** — audit is effectively unimplemented despite being called "non-negotiable" throughout the blueprint (§39, §53, §120).
- No Outcome/Run/Step/Artifact/RunEvent domain (blueprint V9, §127–129) — only `workflow_runs`/`workflow_approvals` exist, which cover workflow execution but not the broader "outcome with artifacts" model.
- No Device Registry / Local Worker Runtime (V7/V9) — no concept of a desktop execution node.
- No Claude Code DeveloperJob orchestration (§58–74, §125).
- No Organization/Department/WorkforceMember/Team domain (V10, §141–171).
- No realtime event stream beyond chat SSE — no WS/SSE channel for agent/job/approval/system events (blueprint §106, §127).

**Frontend (`frontend/lib`, Flutter + GetX, 21 modules under `modules/`)**:
- `strategy` and `marketing` modules are fully wired to their backend counterparts and are the most mature.
- **6 modules are byte-identical empty stubs**: `approvals`, `audit`, `backup`, `branding`, `settings`, `workflows` — just an `isLoading` obs and a placeholder "`<Module>` View is working" text, despite `workflows`/`approvals` having real backend endpoints to bind to.
- No dedicated landing/home page — current `DashboardView` is a tab shell (`currentIndex` switch), not a Hub.
- `api_client.dart` uses plain `http` (not Dio), hardcoded `http://localhost:8000/api/v1` base URL, no interceptors/refresh logic.
- No typed models anywhere — all data is `Map<String,dynamic>`.
- `web_socket_channel` and `record`/`audioplayers` are declared in `pubspec.yaml` but **unused** — voice and realtime WS are dead dependencies, not started work.
- `core/database/database_helper.dart` (sqflite) defines an elaborate offline-sync schema but is **not imported anywhere** — dead code, consistent with CLAUDE.md's "no new SQLite state" rule (safe to ignore/remove later, not extend).
- No forbidden legacy references found (`:8888`, `backend/server`, `javis/`, `web_socket_channel` grep is clean) — runtime boundary is currently respected.

## Roadmap

### Phase 1 — Miva Hologram Hub Landing Page (frontend-led, next up)

**Goal:** Replace the current tab-shell `DashboardView` entry experience with a real
Hub home screen matching the reference image and blueprint §98.2 (Center Core,
Left Rail, Right Rail, Quick Commands, Bottom KPI Strip, Global Command Bar),
per blueprint §104–105's Flutter approach: state-driven `CustomPainter`/Canvas for
rings/waveform, no heavy 3D engine, low-power/accessibility mode from day one.

**Explicit constraint from the blueprint itself (§108, anti-pattern list):** no fake
telemetry. Every panel must bind to a real signal or be visibly marked
"coming soon" — not a hardcoded number. This directly affects scope:
- CPU/Memory/Audio-input hardware telemetry in the reference image is a *desktop
  execution node* concept (V7+, not built yet) — omit or clearly gate as N/A for MVP;
  do not fabricate.
- Activity Feed and the Approval notification badge want to read from audit events /
  workflow approvals — today `audit_logs` is unwritten and the Approvals frontend is a
  stub. Phase 1 will therefore bind the Activity Feed to what's real *now*
  (recent workflow_runs / chat sessions / vault ingests are queryable) and design the
  event contract so Phase 2's audit writes slot in without rework.

**Backend additions (small, additive — no breaking changes):**
- New aggregation endpoint, e.g. `GET /api/v1/workspaces/{workspace_id}/hub-summary`
  in `platform/router.py`, returning: system status (derived from DB reachability +
  last worker heartbeat/job timestamp — real, not fabricated), counts for
  projects/tasks/OKRs/active workflow runs/knowledge docs/automations (reuse existing
  repository queries already used by `strategy`, `tasks`, `okrs`, `vault`, `workflows`
  routers — do not duplicate query logic, call the existing service functions), and a
  bounded "recent activity" list sourced from `workflow_runs`/`chat_sessions`/
  `chunking_jobs` timestamps until real audit events exist.
- Tenant-scope this endpoint using the `core/tenancy.py` pattern (mirrors existing
  scoped-lookup helpers) — this module currently has good scoping discipline, keep it.
- Add a focused pytest in `backend/app/tests/test_platform_hub_summary.py` (no test
  file exists for `platform` today — first coverage for this module) verifying counts
  and workspace isolation (cross-tenant leak test, matching the pattern already
  documented in `core/tenancy.py`'s comments about prior cross-tenant bugs).

**Frontend additions:**
- New module `frontend/lib/modules/hologram_hub/` (bindings/controller/view, same
  structure as every other module) — `HubController` holds: system status, agents
  summary (reuse existing `/agents/` call, same as `AgentsController`), KPI counts,
  activity feed, and an orb `RuntimeState` enum (idle/listening/thinking/retrieving/
  acting/waitingApproval/success/warning/error/offline per blueprint §99).
- Orb state MVP wiring: drive it from `ChatController`'s existing SSE stream state
  (already parses stream events in `_applyStreamEvent`) — thinking during stream,
  success/error on completion — not a new subsystem. "Talk to Miva" voice button is
  present in the UI per the reference image but disabled/labeled "coming soon" (no STT
  exists yet — Phase 8); text command bar is fully functional today via existing chat
  endpoints.
- KPI Strip binds to `hub-summary`; "Dev Jobs" tile has no backing entity yet
  (DeveloperJob domain is Phase 5+) — render as a visibly disabled/"coming soon" tile,
  not a fake number.
- Reuse existing widgets in `core/widgets/` where shapes match (`empty_state.dart`,
  `floating_app_bar.dart`); new Hub-specific painters (rings/glow/waveform) live under
  `modules/hologram_hub/presentation/widgets/`.
- Wire Hub as the new post-login landing route; keep the existing per-module views
  reachable via "Open Dashboard" / KPI tile taps (Context-Aware Dashboard Router,
  blueprint §100) — do not delete the current `DashboardView` tab shell, route into it.

**Exit criteria:** logged-in user lands on Hub; all visible numbers/status are backed
by real queries; orb reflects real chat activity state; no panel displays fabricated
data; tapping a KPI tile or quick command navigates to the corresponding existing
module view.

**Note:** Because Activity Feed / Approval badge will be functionally thin until audit
events exist, Phase 2 should follow immediately after Phase 1, not be deferred long.

---

### Phase 2 — Governance Wiring: Approvals, Audit, Workflows

**Goal:** Turn the three empty stub modules that already have backend support into
real screens, and make `audit_logs` actually get written — closing the biggest
compliance gap relative to the blueprint's repeated "every consequential action must
be audited" principle (§39, §53, §120).

**Backend:**
- Add an audit-write helper (single place, e.g. `core/audit.py`) called from the
  workflow approval endpoint (`workflows/router.py`'s `/steps/{id}/approve`) and from
  other consequential write endpoints as they're touched — do not attempt a
  blanket retrofit of every endpoint in one pass; start with approvals since that's
  the highest-value/lowest-risk path already gated by human decision.
- Expose `GET /api/v1/admin/{workspace_id}/audit-events` (paginated, tenant-scoped)
  reading the now-populated `audit_logs` table.
- Expose the existing `workflow_approvals` list/approve/reject surface properly (the
  approve endpoint exists; confirm a list/pending endpoint exists or add one) for the
  Approvals inbox.

**Frontend:** implement `ApprovalsController`/`AuditController`/`WorkflowsController`
for real, following the exact pattern already used by `AgentsController`/
`TasksController` (list + loading + simple actions) — these are the smallest,
most mechanical wins in the whole roadmap.

**Feeds back into Phase 1:** once these land, Hub's Activity Feed and Approval badge
switch from "best-effort recent activity" to real audit-backed data with no rework.

---

### Phase 3 — Outcome/Run/Artifact Execution Domain (blueprint V9 minimal slice)

**Status (2026-08-11): done.** `backend/app/modules/outcomes/` (models/router/service),
`backend/app/tests/test_outcomes.py`, and the frontend
(`data/services/outcomes_service.dart`, `hologram_hub/presentation/widgets/artifact_card.dart`)
were already written in an earlier session, but two gaps were still open and are now
closed:
- No Alembic migration existed for the 5 new tables even though the ORM models were
  registered in `app/db/base.py` — `POST /api/v1/outcomes` etc. would have 500'd against
  a real Postgres instance despite the (mocked) unit tests passing. Added
  `alembic/versions/f4a8c1d9e3b7_add_outcomes_artifacts_schema.py` (head, on top of
  `mkt002b3c4d5e`) and documented it in `DEPLOYMENT.md`.
- `ArtifactCard` was defined but never imported/rendered anywhere — dead code, so the
  "rendered in Hub's activity feed" deliverable below was unmet. `hub_service.py` now
  returns a workspace-scoped `recent_artifacts` list (real, empty-when-empty, same
  pattern as `recent_activity`), and `system_health_panel.dart` renders it via
  `ArtifactCard` in a new "RECENT ARTIFACTS" card in the Hub's left rail.

(At the time this was written, `backend/app/modules/devices/` and
`backend/app/modules/organization/` — Phase 5 and Phase 7 — were likewise already
coded and router-registered but had no Alembic migration yet either; both were
subsequently closed out the same way, see their own Status blocks below. The "Current
State Snapshot" at the top of this document predates all of Phases 3, 5, 6, 7's actual
implementation work and should not be trusted for those phases — it describes an
earlier point in time, not current `backend/app`/`frontend/lib` state.)

**Goal:** Introduce the `Outcome → Run → Step → Artifact` model (blueprint §127–129)
as the generalization of today's workflow-only execution, so "finished work" (a
report, a diff, a document) becomes a first-class trackable/approvable entity instead
of being implicit in chat or workflow output.

**Schema (minimal, per blueprint's own MVP guidance in §129 — don't build all 13
tables at once), Alembic migration `add_outcomes_artifacts_schema`:**
- `outcomes` — outcome_id, workspace_id, project_id (nullable FK to `strategy.projects`),
  title, desired_result, acceptance_criteria, requested_by (FK `users`), status
  (draft/planning/running/waiting_approval/completed/failed/cancelled), created_at.
- `outcome_runs` — run_id, outcome_id, status (mirrors blueprint §132's job state
  machine: QUEUED/RUNNING/WAITING_APPROVAL/RETRY_SCHEDULED/SUCCEEDED/FAILED/CANCELLED),
  started_at, completed_at.
- `run_steps` — step_id, run_id, type, inputs (JSONB), expected_output, risk_level,
  depends_on (self-FK array or join table), status.
- `run_events` — event_id, run_id, event_type (run.created/step.started/step.completed/
  tool.requested/tool.completed/approval.requested/approval.resolved/artifact.created/
  run.completed/run.failed per §127), payload (JSONB), created_at — append-only, this
  is the durable source Phase 4's realtime stream broadcasts from.
- `artifacts` — artifact_id, run_id, outcome_id, workspace_id, type (document/
  spreadsheet/code/research_bundle/media/external_action_receipt/dashboard_snapshot),
  title, local_uri/object_storage_uri (reuse existing `s3_client.py` MinIO client),
  content_hash, status (draft/review/approved/published/superseded), created_by.
- Approval checkpoint reuses the existing `workflow_approvals` table/endpoint
  (`workflows/router.py`'s `/steps/{id}/approve`) rather than a parallel
  `approval_requests` table — `run_steps.risk_level` maps to the same L0–L4 policy
  already implied by that endpoint.

**Backend:** new module `backend/app/modules/outcomes/` (`router.py`, `service.py`,
`repository.py`), following the same three-file layout as `tasks/` and `vault/`.
Endpoints (blueprint §128, trimmed to MVP): `POST /api/v1/outcomes`,
`GET /api/v1/outcomes`, `POST /api/v1/outcomes/{id}/runs`,
`GET /api/v1/runs/{id}`, `GET /api/v1/runs/{id}/events`,
`GET /api/v1/artifacts/{id}`. Tenant-scope every query via `core/tenancy.py`
helpers (mirror the existing pattern, don't trust client-supplied `workspace_id`).
Add `backend/app/tests/test_outcomes.py` with a run-lifecycle test and a
cross-tenant isolation test (same shape as the tenancy tests implied by
`core/tenancy.py`'s existing comments).

**Frontend:** new `data/services/outcomes_service.dart` (same wrapper pattern as
the other 12 services in `data/services/`); an `ArtifactCard` widget under
`modules/hologram_hub/presentation/widgets/` (blueprint §118's RUNNING/
WAITING_APPROVAL/COMPLETED/FAILED card states) rendered in Hub's activity feed.

**Exit criteria:** creating an Outcome via API and stepping it through
QUEUED→RUNNING→SUCCEEDED produces a queryable run + at least one artifact; Hub's
"Automations" KPI tile switches from hidden/placeholder to a real count; "Dev Jobs"
tile stays placeholder until Phase 5 supplies real DeveloperJob-typed outcomes.

**Dependency:** builds on Phase 2's audit conventions (run_events double as the
audit trail for outcome-scoped actions); Hub's Automations tile becomes real once
this lands.

---

### Phase 4 — Realtime Event Stream (WS/SSE backbone)

**Status (2026-08-11): done.** `core/events.py`, `platform/events_router.py`
(`GET /api/v1/events/stream`), `write_audit_log()`'s single `publish_event` call site,
and the frontend `core/network/realtime_service.dart` (SSE-over-`http`, reconnect with
backoff) were already built in an earlier session, and `HubController`/
`ApprovalsController`/`OrganizationController`/`DeveloperController`/`VaultController`
already subscribed. Design deviation from this section's original text, kept
intentionally: it uses an in-process `asyncio.Queue`-based `EventBroker`, not Postgres
LISTEN/NOTIFY — correct and simpler for the current single-uvicorn-process deployment
(`docker-compose.yml` has no `--workers`/replicas); revisit only if `brain-api` is ever
scaled to multiple processes, since in-process pub/sub won't cross process boundaries.
Gaps found and closed in this session:
- `AuditController` never called `_realtimeService.addListener(...)` at all — the Audit
  screen was still load-once-on-init with no live updates. Added the same
  subscribe/unsubscribe pattern `ApprovalsController` already used, filtered on
  `audit.*` (every `write_audit_log()` action funnels through this prefix).
- No subscriber reconciled on reconnect: `system.connected` (sent by the backend on
  every connect, including reconnects after a dropped network) wasn't in any
  controller's event-type filter except Hub's (which has no filter at all). Added
  `|| eventType == 'system.connected'` to `ApprovalsController`, `AuditController`,
  `OrganizationController`, `DeveloperController`, `VaultController` so a reconnect
  always refetches from the durable tables per this section's own exit criterion,
  instead of only picking up whatever event happened to arrive next.
- Hub's `recent_activity` (Phase 1) only ever read `tasks`/`chat_sessions`, even though
  Phase 2's own text promised it would "feed back" once `audit_logs` was real — it
  never did. `hub_service.py` now also queries `audit_logs` (same
  `metadata_jsonb['workspace_id']` filter as `GET /admin/{workspace_id}/audit-events`)
  and maps the 12 actions actually written today (`workflow.step.approve`,
  `outcome.create`, `knowledge.promote`, etc.) to feed entries. Without this, "approving
  a workflow step updates the Hub's activity feed... within ~2s" (this phase's exit
  criterion) was only half true: the realtime push fired, but the feed's *content*
  didn't include the approval.
- `test_events.py` (this phase's own backend test) and `test_voice.py` were silently
  failing every run — `pytest-asyncio` was never added to `requirements.txt`, so
  `@pytest.mark.asyncio` tests errored with "async def functions are not natively
  supported" instead of being skipped or reported as missing coverage. Installed and
  pinned `pytest-asyncio>=0.23.0`; full backend suite is 200/200 passing now.

**Goal:** One event channel (blueprint §106 event envelope: `event_id`, `event_type`,
`workspace_id`, `actor_id`, `correlation_id`, `payload_ref`) carrying
`agent.*`/`job.*`/`approval.*`/`system.health.updated` events, replacing Hub's
polling of `hub-summary` with push updates, and giving chat's existing SSE pattern
(`chat/{brain_id}/sessions/{id}/stream`) a general-purpose sibling instead of a
one-off.

**Design:** the stream is a **transient notification layer**, not a new
source-of-truth — durable state stays in `run_events` (Phase 3), `audit_logs`
(Phase 2), and `workflow_runs`. This mirrors the blueprint's explicit rule (§83,
§127) that WebSocket/SSE only wakes clients and streams status; reconnect always
resumes from the durable tables, never from stream memory.

**Backend:** reuses the existing `sse-starlette`/`websockets` deps already in
`requirements.txt` (no new dependency) and the existing `asyncpg` LISTEN/NOTIFY
mechanism already used for chat streaming (per inventory: currently chat-only) —
generalize it to a shared `core/events.py` with a `publish_event(event_type,
workspace_id, payload)` helper that does a Postgres `NOTIFY` on a common channel.
New endpoint `GET /api/v1/events/stream?workspace_id=` in a new
`backend/app/modules/platform/events_router.py`, filtering NOTIFY payloads by the
caller's workspace membership before forwarding. Call `publish_event` from: the
Phase 2 audit-write helper, `run_events` inserts (Phase 3), and the workflow
approval endpoint — one call site per action, not a new event-emission framework.

**Frontend:** new `core/network/realtime_service.dart` wrapping `web_socket_channel`
(finally used) or SSE-over-`http` (consistent with the existing
`data/services/chat_service.dart` `streamSession` precedent — pick whichever
matches what the backend endpoint actually implements) with reconnect/backoff.
`HubController` (Phase 1) and `ApprovalsController`/`AuditController` (Phase 2)
subscribe instead of polling `hub-summary`/`audit-events` on a timer.

**Exit criteria:** approving a workflow step updates the Hub's activity feed and
approval badge within ~2s without a manual refresh; killing and restoring network
reconnects and reconciles against `run_events`/`audit_logs` rather than showing
stale state.

**Note:** after this phase, `web_socket_channel` usage in `frontend/lib` is
expected/legitimate — the Phase-by-phase legacy-boundary grep (see Verification
section) should no longer treat a match as a violation.

---

### Phase 5 — Claude Code Developer Worker + Device Registry (blueprint V7/V9, §58–74, §80–95)

**Status (2026-08-11): Cloud Control Plane done; Local Worker Plane not started (as
intended — see below).** `backend/app/modules/devices/` (models/router/service),
`backend/app/tests/test_devices.py`, `data/services/developer_service.dart`, and
`modules/developer/` were already written in an earlier session and registered in
`main.py`, but had the same "looks done, isn't wired to a real DB" gap as Phase 3, plus
one real security gap specific to this phase's own "new trust boundary" warning above.
Closed in this session:
- No Alembic migration for the 4 tables (`devices`, `device_credentials`,
  `developer_jobs`, `job_leases`) despite the ORM models being registered in
  `app/db/base.py` — added `alembic/versions/c7b3e9a1f6d2_add_devices_developer_jobs_schema.py`
  (head, on top of Phase 3's `f4a8c1d9e3b7`), documented in `DEPLOYMENT.md`.
- `POST /devices/enroll` issued an enrollment token and stored it **in plaintext** in
  `device_credentials.enrollment_token` — a DB leak would have handed out working
  device-impersonation tokens directly. Renamed the column to `token_hash` and store
  only `sha256(raw_token)`; the raw token is now returned exactly once, in the enroll
  response, matching how the roadmap text itself describes it ("per-device enrollment
  key, revocable").
- More significantly: **that token was never actually checked anywhere.** Every
  `/devices/*` endpoint — including `heartbeat`, `claim`, and `submit-results`, which
  are meant to be called by the desktop worker process, not a human — required a
  logged-in user's JWT (`get_current_workspace_member`), the same credential Flutter
  uses. That collapses exactly the two-plane trust boundary this section warns not to
  collapse: nothing distinguished "a human asked for this" from "a worker device
  performed this," and the enrollment flow was security theater. Added
  `get_current_device` (`core/auth.py`), a separate dependency that authenticates via
  `Authorization: Bearer mcosa_dev_...` against `device_credentials`, and switched the
  3 worker-facing endpoints to it; `submit_job_results` also now checks the caller
  device is the one the job was actually assigned to (`PermissionError` → 403), so one
  enrolled device can't overwrite another's job results.
- Downstream of that fix, Flutter's `DeveloperController.approveAndMerge()` was calling
  `submit-results` **as a human pretending to be a worker**, unconditionally writing
  `status: SUCCEEDED, diff_summary: "Merged into main branch"` regardless of whether
  any real work happened — because no real worker exists yet, this was pure fabricated
  state, the exact anti-pattern §108 forbids. It would have started failing closed
  (401) once the auth fix above landed anyway. Removed `claimJob`/`submitJobResults`
  from `developer_service.dart` (a human session structurally cannot call worker-only
  endpoints now) and rewrote `approveAndMerge()` to say plainly that merge requires the
  Local Worker Plane and isn't available yet, instead of faking success.
- The Developer nav item had no `Platform.isMacOS || isWindows || isLinux` gate as this
  section's own Frontend paragraph specifies — it rendered on every platform including
  web/mobile. Added the gate in `dashboard_view.dart` (`_isNativeDesktopPlatform`,
  `_NavItem.desktopOnly`).

**Still correctly not started, on purpose:** `desktop_worker/` (Local Worker Plane
process), the `javis-dev` Claude Code CLI plugin/skills, git worktree handling, and
sandboxing. These remain a dedicated future session per this section's own opening
warning — nothing in this pass built them, and the fixes above were chosen specifically
so they don't need to be revisited when that session happens (the device-auth
boundary, hashed credential, and desktop-only gating are the load-bearing pieces a real
worker will plug into, not throwaway scaffolding).

**Goal:** The largest and highest-risk phase — a local desktop execution node running
a Local FastAPI Worker Runtime + Claude Code CLI under the `javis-dev` plugin pattern,
with cloud-side `Device`/`Job`/`Lease` durable-command tables and mobile→desktop
routing. This is genuinely new infrastructure, not a wiring task like Phases 1–2, and
it introduces a **new trust boundary** the rest of the roadmap doesn't have — treat
the skeleton below as the shape of the work, but re-plan the credential/sandbox
details in a dedicated session when this phase is actually reached rather than
locking them in now.

**Two-plane split (blueprint §113 — do not collapse these):**
- **Cloud Control Plane** = `backend/app` (existing). Adds durable tables only:
  `devices` (device_id, workspace_id, platform, capabilities JSONB e.g.
  `["claude_code","git","browser","filesystem"]`, allowed_projects, trust_level,
  last_seen), `device_credentials` (per-device enrollment key, revocable),
  `jobs` (extends the Phase 3 `outcome_runs` shape with device routing: job_id,
  outcome_id, required_capabilities, assigned_device_id, status per blueprint §83's
  state machine QUEUED/WAITING_FOR_DEVICE/CLAIMED/RUNNING/WAITING_APPROVAL/SUCCEEDED/
  FAILED/CANCELLED), `job_leases` (job_id, device_id, worker_id, lease_until).
  Endpoints (blueprint §128): `POST /api/v1/devices/enroll`, `GET /api/v1/devices`,
  `POST /api/v1/devices/{id}/heartbeat`, `POST /api/v1/devices/{id}/jobs/{job_id}/claim`.
  New module `backend/app/modules/devices/`.
- **Local Worker Plane** = a **new, separate process/directory outside `backend/app`**
  (e.g. `desktop_worker/`), a minimal FastAPI app bound to `127.0.0.1` only, launched
  and supervised by the Flutter Desktop build (macOS/Windows/Linux targets already
  exist under `frontend/{macos,windows,linux}/`). It receives claimed jobs, creates a
  Git worktree, and invokes the Claude Code CLI with a `javis-dev` plugin (per
  blueprint §60–61: skills like `/javis-dev:implement-feature`,
  `/javis-dev:fastapi-feature`; hooks for policy/quality gates). This plane must never
  be reachable from the public internet and must never share a process/credential
  scope with the Cloud Control Plane.

**Frontend:** new `frontend/lib/modules/developer/` (Developer Dashboard per
blueprint §103 — job id, worktree, diff summary, test/build status, approve/merge
actions), desktop-only (gate on `Platform.isMacOS || isWindows || isLinux`); mobile
build only ever shows job status/approval via the existing Phase 3/4
outcome+realtime plumbing, never talks to the Local Worker Plane directly.

**Exit criteria (of the eventual dedicated pass):** a mobile/web-submitted "fix bug X"
outcome routes to an online desktop with `claude_code` capability, produces a
worktree diff + test results as a Phase-3 Artifact, and requires explicit approval
before merge — with the Local Worker Plane never exposed beyond loopback.

---

### Phase 6 — Knowledge Engine Upgrade (local Markdown workspace, Knowledge Studio)

**Status (2026-08-11): done.** `vault/knowledge_service.py`, `vault/knowledge_router.py`
(wikilink parsing, promotion lifecycle, audit-logged promote), and
`test_knowledge.py` were already written and correctly tenant-scoped. Two gaps closed
in this session:
- No Alembic migration for `knowledge_objects`/`knowledge_relations` despite the ORM
  models being registered in `app/db/base.py` (the now-familiar Phase-3-shaped gap) —
  added `alembic/versions/d2e5f8a4c9b1_add_knowledge_objects_and_relations.py`.
- The frontend half was dead code: `VaultController` already had
  `knowledgeObjects`/`selectedKnowledgeType`/`selectedKnowledgeStatus`/`promoteObject`/
  `loadBacklinks` and fetched on init and on `knowledge.*` realtime events, but
  `vault_view.dart` never rendered any of it — no type/status filter, no promote
  button, and `loadBacklinks` was never called from anywhere so the existing
  "Backlinks" panel silently always showed empty. Added a "Tri thức có cấu trúc
  (Knowledge Studio)" section to `vault_view.dart` (type/status filter chips, a
  horizontal Knowledge Object list with an inline "Duyệt" promote button on
  capture/candidate items, and a backlinks chip row driven by tapping an object) that
  wires every one of those previously-dead controller fields to something on screen.

**Goal:** `vault` already does real hybrid RAG over uploaded documents — extend it
toward blueprint §65–72's Knowledge Object model (typed objects: note/research/
decision/ADR/lesson, `[[wikilink]]` relations, promotion lifecycle
Capture→Candidate→Approved) and a lightweight Flutter Knowledge Studio, rather than
introducing Obsidian as a dependency (blueprint is explicit that Obsidian stays
optional/external, §72's decision table).

**Schema (extends `vault`, does not replace it) — Alembic migration
`add_knowledge_objects_and_relations`:**
- `knowledge_objects` — object_id, workspace_id, brain_id, vault_document_id (nullable
  FK to existing `vault_documents`, since a knowledge object is usually backed by a
  markdown doc already in the vault), object_type (note/research/fact/concept/
  decision/adr/requirement/lesson/architecture/skill_spec per §65), status
  (capture/candidate/approved/superseded/archived per §65's lifecycle), source_hash,
  generated_by (nullable — agent_id/run_id when AI-authored), confidence.
- `knowledge_relations` — relation_id, from_object_id, to_object_id, relation_type
  (SUPPORTS/IMPLEMENTS/SUPERSEDES/AFFECTS/RELATED_TO per §65), derived from parsing
  `[[wikilink]]` syntax in markdown content on ingest/chunking.

**Backend:** extend the existing `vault` module rather than create a parallel one —
add `vault/knowledge_service.py` (wikilink parsing on the existing
`chunking_service.py` pipeline, promotion state-machine transitions) and a
`vault/knowledge_router.py` mounted under the same `/api/v1/vault` prefix:
`GET /vault/{brain_id}/knowledge` (filterable by type/status),
`GET /vault/{brain_id}/knowledge/{id}/backlinks`,
`POST /vault/{brain_id}/knowledge/{id}/promote` (candidate→approved; call the
Phase 2 audit-write helper here — promotion is exactly the kind of
"AI output becomes truth" action the blueprint insists must be audited, §65's
"AI không được biến mọi hội thoại thành truth").

**Frontend:** extend the existing `VaultController`/`VaultView` (already has
document list/view/edit/search) rather than adding a new module — add a
knowledge-type filter, a backlinks panel, and a promote action button. Full
graph/wikilink visualization (blueprint §66's "interactive graph") is explicitly
desktop-only per the blueprint's own capability table — gate it behind
`Platform.isMacOS || isWindows || isLinux`, mobile gets read/search only.

**Exit criteria:** creating/uploading a markdown doc with `[[Other Doc]]` syntax
produces a queryable backlink; promoting a candidate object to approved is
audit-logged; no Obsidian runtime dependency is introduced anywhere in
`frontend/` or `backend/`.

---

### Phase 7 — Hybrid Workforce / Organization Domain (blueprint V10, §139–171)

**Status (2026-08-11): done.** `backend/app/modules/organization/` (models/router/
service, 6-department auto-bootstrap, Hire AI Employee, CEO Command Center, Daily
Briefing), `test_organization.py`, and the full Flutter `modules/organization/`
(dropdown-driven hire wizard sourced from real department data, not hardcoded) were
already written. Closed in this session:
- No Alembic migration for the 5 org tables, and the roadmap's own explicit
  `tasks` table extension (`assignee_member_id`, `owner_member_id`, `execution_mode`)
  didn't exist even in the model, let alone a migration — added both in one migration,
  `alembic/versions/e8f1a7c3d5b9_add_hybrid_workforce_schema.py`, matching this
  section's own "Migration name reference" (`add_hybrid_workforce_schema`, alters
  `tasks`).
- `get_ceo_command_center`'s pending-approvals count queried `WorkflowApproval` with
  **zero workspace scoping** (`.filter(status == "pending")` only) — a real
  cross-tenant leak: every workspace's CEO Command Center showed the pending-approval
  backlog of *every* tenant combined. Fixed to join through
  `WorkflowStep → WorkflowRun → WorkflowVersion → WorkflowDefinition.brain_id`, the
  same brain-scoped chain `hub_service.py` and `workflows/router.py` already use for
  this exact metric (this is the fourth time this shape of bug has shown up per
  `core/tenancy.py`'s own comments — still worth a shared helper if a fifth shows up).
- `hire_ai_employee` never verified the client-supplied `department_id` actually
  belongs to the caller's own organization — a member could pass a department UUID
  from a different workspace and `DepartmentMembership` would silently link the new
  hire into it. Added an ownership check (`Department.id == department_id,
  Department.organization_id == org.id`), 404 on mismatch.
- `health_status` in the CEO Command Center response was a hardcoded `"EXCELLENT"`
  constant — the exact fake-telemetry anti-pattern §108 forbids, in the one feature
  (CEO Command Center, §157) the roadmap explicitly names in that context. Replaced
  with a real derived signal (pending-approvals backlog size); `active_tasks` was also
  silently counting *all* tasks including done/cancelled ones, not just active — now
  filtered to non-terminal statuses.

**Goal:** Organization/Department/Role/WorkforceMember/Team + "Hire AI Employee" flow
+ CEO Command Center + Daily Briefing. This is the newest and most speculative part
of the blueprint (product-identity rename to "mCOSA" included) — sequence last since
Strategy OS and Marketing OS already deliver most of the underlying substance; this
phase is primarily an organizational/governance layer on top of work that already
exists.

**Schema (V10 MVP slice per §167, not all 16 tables in §164 at once) — Alembic
migration `add_hybrid_workforce_schema`:**
- `organizations` — one row per workspace initially (organization_id ≡ workspace_id
  1:1 for MVP; do not build multi-org-per-workspace yet, nothing in the current
  codebase needs it).
- `departments` — department_id, organization_id, name, is_ai_only (bool, but never
  hard-coded true — §171 anti-pattern), capability_domain (finance/legal/marketing/
  product_tech/operations/ceo_office). Auto-created (6 rows) on first login per §167.
- `workforce_members` — member_id, organization_id, member_type (HUMAN|AI_AGENT),
  human_user_id (nullable FK `users`), agent_id (nullable FK existing `agents` table
  — **critical: `agents` is extended-by-reference, not replaced**, so the existing
  `/api/v1/agents` CRUD used by `AgentsController` and the Phase 1 Hub keep working
  unmodified), status.
- `department_memberships`, `team_memberships` — member_id ↔ department_id/team_id
  join tables with role.
- `agent_relations` — agent_id, related_member_id, relation (owner/manager/operator/
  reviewer/approver per §145).
- `work_items` — **extends the existing `tasks` table rather than duplicating it**:
  add nullable columns `assignee_member_id`, `owner_member_id`,
  `execution_mode (HUMAN|AGENT|HYBRID)` to `tasks` in this migration instead of
  creating a parallel `work_items` table, per blueprint §150's explicit "don't split
  the task engine" rule and CLAUDE.md's aversion to duplicate systems for the same
  concept. `TasksController`/`tasks/router.py` keep working; new fields are additive.

**Backend:** new module `backend/app/modules/organization/` (`router.py` for
org/department/member/team CRUD, `service.py` for the Hire-AI-Employee flow's
10-step wizard backend per §147 and the 6-department auto-bootstrap per §167,
`repository.py`). CEO Command Center (§157) and Daily Briefing (§158) are read
endpoints aggregating Strategy OS (existing) + Phase 3 outcomes + Phase 2 approvals
— no new domain logic, just an aggregation query similar in shape to Phase 1's
`hub-summary` endpoint.

**Frontend:** new `frontend/lib/modules/organization/` — Org chart view (§159),
Hire AI Employee wizard (§147), CEO Command Center. Once this lands, Hub's "Open
Dashboard" default destination for founder-level queries becomes CEO Command Center
instead of the generic per-module views (Context-Aware Dashboard Router update,
§166's routing table).

**Exit criteria:** founder's first login auto-creates 6 departments +
mCOSA-as-Chief-of-Staff; existing `/agents` CRUD and `AgentsController` behavior is
unchanged; Hire AI Employee creates a `workforce_members` row + `agent_relations`
without touching the `agents` table's existing shape; CEO Command Center shows real
department/OKR/approval aggregates, not placeholders.

---

### Phase 8 — Voice (STT/TTS)

**Status (2026-08-11): done (push-to-talk STT; TTS still not started, as intended —
see this section's own "optional/later" note below).** `integrations/voice_client.py`,
`chat/router.py`'s `POST /chat/transcribe-voice`, `core/services/voice_service.dart`,
and the Hub/Chat mic buttons were already wired end-to-end — but the wiring carried
audio that was never real, closed in this session:
- `VoiceClient.transcribe()` returned a **hardcoded fake transcript**
  ("Tôi muốn kiểm tra tình trạng vận hành hệ thống COSA...") whenever
  `OPENAI_API_KEY` wasn't set, instead of an error. This is a more serious instance of
  the §108 anti-pattern than a fake UI number: a user records themselves saying
  something real, and the system fabricates unrelated text and feeds it into the chat
  pipeline as if it were genuine recognized speech. Now raises and the endpoint
  returns 503 instead.
- `VoiceService.startRecording()`/`stopRecordingAndTranscribe()` never actually used
  the already-declared `record` package — `startRecording` just flipped a boolean and
  recorded a timestamp, and `stopRecordingAndTranscribe` uploaded a **hardcoded dummy
  byte buffer** (`'RIFF....WAVEfmt '`) to the backend regardless of what the user said
  or whether they said anything at all. Rewrote it to use `AudioRecorder` for real
  AAC/M4A capture to a temp file (deleted after upload either way, per this section's
  own "raw audio is not persisted by default" rule), gated off on web for now
  (`record`'s web backend returns a blob URL, not a readable file path - failing
  honestly with `false` rather than faking capture there). Added the
  `NSMicrophoneUsageDescription` key (iOS + macOS Info.plist - macOS's sandbox
  entitlement was already present) and `RECORD_AUDIO` (Android manifest); without
  these the OS permission prompt this fix now actually triggers would never appear.
  Added `path_provider` as an explicit dependency (was only present transitively).
- Both `ChatController.toggleVoiceRecording()` and
  `HologramHubController.onTalkPressed()` set the "recording"/"listening" UI state
  *before* checking whether `startRecording()` actually succeeded, so a denied mic
  permission still showed a live listening indicator. Both now only flip to
  listening/recording state on a real `true` return, and the Hub shows an honest
  "Không thể ghi âm" error otherwise instead of a stuck fake-listening state.

**Goal:** Blueprint explicitly sequences voice *after* text core is solid (§34,
Phase 6 of §17's roadmap: "Voice nên được triển khai sau text core"). `record`/
`audioplayers` are already in `pubspec.yaml` unused — this phase activates them
behind a `VoiceService` interface (push-to-talk first, per §34), feeding the same
Intent Router/chat pipeline text does. Deliberately last because every earlier phase
(Hub orb states, approvals, audit) is designed to work correctly without it.

**Backend:** no new persistent domain table needed — voice input becomes a normal
chat message once transcribed, reusing the existing `chat/router.py` message-send
path (`chat_sessions`/`chat_messages`). Add an STT adapter under `integrations/`
(mirrors the existing `anthropic_client.py`/`openai_client.py`/`gemini_client.py`
pattern — e.g. `integrations/voice_client.py` wrapping OpenAI Whisper/Realtime or
another provider behind the same adapter shape) rather than hand-rolling a new
transport. Per blueprint §34: raw audio is **not persisted by default**; only the
resulting transcript is stored, as a normal chat message — no new retention policy
mechanism needed beyond what `chat_messages` already has. TTS (Miva speaking back)
is optional/later within this phase; push-to-talk transcription is the MVP slice.

**Frontend:** new `core/services/voice_service.dart` interface (so the STT/TTS
provider can be swapped without touching UI code, per blueprint §104's "voice
service nằm sau interface"), implemented using the already-declared `record`
package. Wire into two existing surfaces, not a new one: `ChatController` (mic
button sends the transcript through the existing `sendMessage` call — no new
endpoint) and the Phase 1 Hub's "Talk to Miva" button (currently disabled placeholder
— this phase is what turns it on, driving the orb's `listening`/`thinking` states
from real mic capture instead of only chat-stream state).

**Exit criteria:** press-and-hold mic on Hub or Chat produces a transcript that
flows through the existing chat pipeline identically to typed text; no raw audio
file is written to disk/object storage by default; text-only input continues to
work unchanged (voice is additive, not a replacement path).

## Sequencing Rationale

1→2 are tight (Hub needs governance data soon after launch). 3→4 build the general
execution/event backbone that 5, 6's promotion audit, and 7's CEO Command Center all
read from — treat 3→4 as the shared foundation, not optional. 5 additionally
introduces a new trust boundary (Local Worker Plane) that nothing else in the
roadmap depends on — it can slide later without blocking 6, 7, or 8. 6 extends
existing vault code and only needs Phase 2's audit helper, so it's low-risk and
flexible on timing. 7 is additive on top of Strategy + Agents + Phase 2/3 (approvals
and outcomes feed CEO Command Center) — the `tasks` table extension it makes must
happen after Phase 1/2 are stable since `TasksController` and the Hub both read
`tasks` today. 8 is intentionally last and touches only Chat + Hub's mic button, so
it has no downstream dependents.

**Migration name reference:** `add_outcomes_artifacts_schema` (3) →
`add_knowledge_objects_and_relations` (6, independent of 3) →
`add_hybrid_workforce_schema` (7, alters existing `tasks` table — review for
conflicts with any migrations landed between now and Phase 7). Phase 5's device
tables and Phase 4's event plumbing are additive/new-table-only, no existing-table
alterations, so they carry the least migration risk.

## Explicitly Out of Scope / Anti-Patterns to Avoid (from the blueprint's own lists)

- No 3D/WebGL hologram rendering, no fabricated telemetry (§108, §16).
- No Celery/Redis/Kafka until the current polling worker demonstrably can't keep up
  (§42, §96) — current `worker_main.py` approach stays.
- No forking OpenWorker or adopting `aisuite` as a mandatory core (§111, §136).
- No big-bang rename to "mCOSA" branding across code/DB (§169 — product/UI naming can
  move first, internal identifiers separately, if/when that's decided).
- No expanding `frontend/lib`'s architecture (typed models, Dio, repository
  interfaces) as a blanket rewrite — Phase 1 introduces these patterns only for the
  new Hub module; retrofitting all 21 existing modules is a separate, explicitly
  deferred cleanup, not bundled into this roadmap.

## Verification Approach (once phases move to implementation)

- Backend: pytest per CLAUDE.md's test-first rule, with a tenant-isolation test for
  every new endpoint (matches the existing `core/tenancy.py` pattern/comments).
- Frontend: run `flutter analyze` and existing widget/controller tests for touched
  modules; manually exercise the Hub against a running `backend/app` + `worker_main.py`
  per `DEPLOYMENT.md`'s startup sequence before calling a phase done.
- Re-run the legacy-boundary grep after each phase:
  `rg -n --glob '!build/**' '(:8888|backend/server|javis/|web_socket_channel)' frontend/lib`
  (note: after Phase 4, `web_socket_channel` usage becomes expected/legitimate — update
  this check's intent accordingly rather than treating a match as a violation).
- Don't stop at "migration file parses" — `alembic upgrade head` against a real Postgres
  is the only thing that actually proves a migration is correct, and it caught a real bug
  here: running the 4 new migrations (Phases 3/5/6/7) against the live dev DB on
  2026-08-11 hit `DuplicateTable`, because `app/main.py`'s startup hook
  (`Base.metadata.create_all`) had already silently created all 16 new tables with
  **stale schema** (pre-fix `device_credentials.enrollment_token` instead of
  `token_hash`, `tasks` missing the 3 new Phase 7 columns entirely) before Alembic ever
  ran. Confirmed all 16 tables were 0 rows, dropped them, re-ran `alembic upgrade head`
  clean, and confirmed via `\d device_credentials` / `\d tasks` that the live schema now
  exactly matches the migration files, then confirmed `GET /hub-summary` and
  `/events/stream` serve 200s against it with no `UndefinedColumn` errors. See
  `DEPLOYMENT.md`'s warning under "Bước 1" for the recovery procedure and the still-open
  root cause (`create_all()` racing ahead of `alembic upgrade head` on every fresh
  container start) — not fixed this session, needs a full audit of which existing tables
  have no formal migration at all before it's safe to remove.
