# mCOSA V12.3 Implementation Plan (Part A + Part B + Part C)

## Context

`mCOSA_V12_3_Consolidated_Project_Portfolio_LiveKit_Agent_Memory.md` (repo root, 8127 lines) is the master implementation spec for three additive upgrades on top of the already-deployed V10 Hybrid Workforce runtime:

- **Part A** — V12 Project & Portfolio Operating System (classification, methodology routing, strategy frameworks, 12-Week-Year cycles, milestones/gates, portfolios, Next Best Action).
- **Part B** — V12.2 Hybrid LiveKit Local/Cloud realtime voice architecture (Flutter ↔ LiveKit ↔ Gemini Live ↔ mCOSA tool bridge).
- **Part C** — V12.3 Hierarchical Agent Memory (TencentDB Agent Memory as an optional local sidecar for cross-session recall/context offload).

This plan was produced by exploring the current codebase (backend, frontend, and the new `services/` directory) and cross-checking against `docs/architecture/MCOSA_V12_ROADMAP.md`, an existing audited status report dated 2026-08-11 (one day before this plan). That roadmap changes the picture substantially:

- **Part A is already fully implemented and audited "DONE" — backend *and* frontend**, including a resolved architecture decision to deliberately *not* build separate `modules/projects/`, `modules/portfolios/`, `modules/ceo/` Flutter modules (existing single-tab-dialog pattern in `strategy/views/tabs/projects_tab.dart` / `okrs_tab.dart` was judged functionally complete). Part A therefore needs **no new implementation work** in this plan — only a short verification pass, listed below.
- **Part B (LiveKit)** has substantial in-progress, uncommitted code (backend module, a separate `services/realtime_agent/` LiveKit worker process, and a Flutter `realtime_voice` module) with no prior roadmap doc — this is genuinely new, unaudited work with identifiable gaps.
- **Part C (Agent Memory)** does not exist anywhere in the codebase — genuinely greenfield, with no prior art beyond an explicitly out-of-bounds legacy file reader (`backend/server/main.py::_agent_memory()`).

The intended outcome of this plan is therefore: confirm Part A stays as-is (don't rebuild what's done and deliberately architected), finish Part B's already-started work (correctness fixes before its larger hybrid-transport lift), and stand up Part C strictly as the spec prescribes — a small, flaggable, PoC-gated side-track that never blocks A or B.

All file paths below are relative to `/Volumes/SSD/javis-saas`. Spec section refs (`§n`) point at the master spec file.

---

## 0. Cross-cutting rules (apply to every phase, not repeated per part)

From `CLAUDE.md` and spec §62/§90/§210 — already the established convention in this repo (confirmed by `MCOSA_V12_ROADMAP.md`'s "Organizing principles"):

1. **Snowflake IDs**: every new table uses `id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)` from `app.core.snowflake` — the pattern every existing module actually uses (`SnowflakeIDMixin` exists but is rarely used). Serialize as `str(id)` on every REST response (see `backend/app/modules/realtime/router.py`'s `"session_id": str(session.id)`).
2. **Tenancy**: filter every query by `workspace_id` in the query itself (`.filter(Model.id == id, Model.workspace_id == workspace_id)`), not via a post-hoc comparison — see `realtime/router.py::end_realtime_session` for the reference pattern (foreign-tenant ID 404s rather than leaking existence via 403). Part A's `test_portfolio_service.py::test_portfolio_acl_zero_trust_cross_tenant` is the reference test shape to copy for new tenancy tests.
3. **Feature flags**: every new module gets a `FLAG_<NAME>_V12` (or `_V12_2`/`_V12_3`) constant in `backend/app/core/feature_flags.py`, enforced server-side via `require_flag()`/`is_enabled()` — never only in Flutter. This repo's stated minimalism principle is "one table, one function, no LaunchDarkly/GrowthBook" — don't build a flag-admin UI/endpoint unless a real need appears (Part A deliberately left this as script/shell-only).
4. **No duplicate-concept tables**: before adding a new table, check whether an existing one with a nullable scoping column already covers the concept (Part A's portfolio SWOT/TOWS/PESTEL reuse `swot_items`/`tows_options`/`pestel_items` via nullable `portfolio_id` rather than new tables — the same instinct applies to Part B/C).
5. **Migrations + repositories + tests for every persisted entity** (spec §62.15): each new model gets an Alembic revision chained off the current head, service-layer data access (not router-layer), and at minimum a tenant-isolation test. This repo's established test convention (per `MCOSA_V12_ROADMAP.md` item 10) is calling router/service functions directly with a mocked `Session`, not a FastAPI `TestClient` — no real test-DB infra exists yet. Follow that convention for new tests rather than introducing a different style.
6. **No `javis/`/`backend/server/` reuse**: `rg -n --glob '!build/**' '(:8888|backend/server|javis/|web_socket_channel)' frontend/lib` must stay clean after every phase — this is already part of this repo's `make boundary-check` / verification routine. Relevant especially to Part C — the only prior art for "agent memory" in this repo is `backend/server/main.py::_agent_memory()` (a legacy file-based `MEMORY.md` reader), reference-only, must not be reused or ported.
7. **Test-first** for behavioral changes.
8. **`DEPLOYMENT.md`** gets updated whenever a new runtime process is introduced (Part B's `services/realtime_agent` worker; Part C's memory sidecar) or startup sequence changes — Part A's roadmap shows this already happened for the `v12_001`–`v12_011` migration chain, as the template to follow.

---

## Part A — Project/Portfolio OS: verification only, no new implementation

### Status: DONE (per `docs/architecture/MCOSA_V12_ROADMAP.md`, audited 2026-08-11)

All 10 planned sprints are implemented on both backend and frontend:

- **Backend**: ~50 model classes across `backend/app/modules/strategy/models.py`, full routers (`router.py`, `portfolio_router.py`, `execution_router.py`, `next_action_router.py`, `living_pestel_router.py`, `okrs_router.py`, plus `routers/{analysis,canvas,evidence}_router.py`), all 14 `FLAG_*_V12` flags seeded true and enforced, full R0→R1→R2 Next Best Action ranking pipeline (deterministic formula → rule bonuses → best-effort AI rerank via the `STRATEGIC_ANALYZER` logical profile with safe fallback on any provider error).
- **Frontend**: deliberately bolted onto existing tabs (`frontend/lib/modules/strategy/views/tabs/projects_tab.dart`, `okrs_tab.dart`) rather than split into new `modules/projects/`/`modules/portfolios/`/`modules/ceo/` — this was an explicit, resolved architecture decision (roadmap's "decision #4"), not an oversight or gap. `hologram_hub` already shows a Top-3 CEO Next Actions panel wired to `GET /ceo/next-actions`.
- **Verification last run 2026-08-11**: `pytest app/tests -q` → 284 passed; `alembic heads` → single head `v12_011_flags2`; `flutter analyze` → no issues; boundary-check clean.

**Do not**:
- Rebuild any of the backend routers/services/models listed above.
- Create new `frontend/lib/modules/projects/`, `modules/portfolios/`, or `modules/ceo/` — this was explicitly decided against; revisit only if one of these areas grows complex enough to justify its own nav entry, and treat that as a fresh product decision, not a default next step.
- Add a `GET /ceo/brief` composition endpoint speculatively — the roadmap's "Remaining items" explicitly judged that `hologram_hub` showing only Next Actions (not PESTEL signals / model run audits) is *correct*, because those are founder/admin configuration surfaces, not CEO-Brief-glance material. If Part B or Part C later need a genuinely new "brief" shape (e.g., for a voice summary), extend `backend/app/modules/platform/hub_service.py::get_hub_summary_data` (already consumed by the realtime voice tool `get_ceo_brief`) rather than inventing a parallel endpoint.

### A.1 — Recommended verification pass (before starting Part B/C work, ~half a day)

1. Re-run the roadmap's verification commands to confirm nothing has regressed since 2026-08-11 (one day before this plan):
   - `cd backend && .venv/bin/python -m pytest app/tests -q` → expect 284+ passed.
   - `cd backend && alembic heads` → expect single head (may have advanced past `v12_011_flags2` if Part B's migrations have landed — that's expected and fine, just confirm no branch conflicts).
   - `make boundary-check` (or the raw `rg` command in cross-cutting rule 6).
   - `cd frontend && flutter analyze`.
2. Confirm the two "Remaining items" from the roadmap are still deliberately open (not silently regressed into bugs): no flag-admin HTTP endpoint, `hologram_hub` still shows Next Actions only.
3. If any of the above fails, treat it as a regression to fix before starting Part B/C, not as new Part A feature work.

---

## Part B — LiveKit Realtime Voice: completion plan

No prior roadmap doc exists for this — unlike Part A, this is genuinely new, unaudited, currently-uncommitted work. Maps onto spec Phase LK-0 through part of LK-4 already done; this plan closes LK-2 through LK-9 and folds in the V12.2 hybrid local/cloud sections (§101-139).

### What already exists

- **Backend** `backend/app/modules/realtime/` (flat: `models.py`, `router.py`, `token_service.py`, `tools.py`): `RealtimeSession` model (workspace_id, user_id, device_type, transport default `livekit_cloud`, model_profile default `gemini_live`, room_name unique format `cosa-{workspace_id}-{user_id}-{snowflake}`, status `creating|active|ended|error`). `POST /sessions` creates + mints a LiveKit token; `POST /sessions/{id}/end`. `token_service.py` mints JWTs via `livekit.api`. `tools.py` exposes `get_ceo_brief`/`get_next_best_actions` to the agent (reusing `hub_service.get_hub_summary_data` and `NextBestActionService` — Part A's services, confirming Part A's backend is already being consumed correctly by Part B). Registered in `main.py` at `/api/v1/realtime`. Migration `f3a9c1e7b2d4_add_realtime_sessions`. Tests: `test_realtime_sessions_router.py`, `test_realtime_token_service.py`, `test_realtime_tools.py`.
- **Confirmed bug**: `RealtimeSession.status` is only ever written `"creating"` or `"ended"` — nothing ever sets `"active"` or `"error"`, and there's no agent-dispatch/health linkage field.
- **`services/realtime_agent/`** (separate deploy unit, own venv/requirements.txt, deliberately different `httpx` pin than backend): `main.py` (functional LiveKit Agents worker bootstrap, implicit/automatic dispatch — no `agent_name` set), `agent.py` (functional: `AgentSession` + `livekit.plugins.google.beta.realtime.RealtimeModel` "Puck"; publishes `HOLOGRAM_STATE` data-channel messages on state changes; `prewarm()` is a no-op stub), `tools.py` (in-process imports backend/app via `sys.path` hack + own `SessionLocal()`; hardcoded `NAVIGATION_TARGETS` whitelist), `session_context.py` (single static prompt string, not real per-session state). No `event_bridge.py` (spec names this file explicitly; currently missing — state/UI-command publishing is duplicated inline across `agent.py` and `tools.py`). No README/Dockerfile.
- **Frontend** `frontend/lib/modules/realtime_voice/` (4 files, no `bindings/`): `RealtimeSessionGateway` abstract contract + sealed events, `LiveKitRealtimeSessionGateway` impl (`package:livekit_client`), `RealtimeSessionApi` REST client, `VoiceSessionController` (constructor-injected gateway+api, tested via `frontend/test/voice_session_controller_test.dart`). **Not registered via GetX** — `HologramHubController` instantiates it as a plain field (`VoiceSessionController()`), and it imports `HologramRuntimeState` directly from `hologram_hub`'s `miva_hologram_core.dart` (cross-module coupling). `hologram_hub_binding.dart` was not touched.
- `pubspec.yaml` added `livekit_client: ^2.11.0`; `backend/requirements.txt` added only `livekit-api>=1.0` (heavier `livekit-agents`/`livekit-plugins-google` stay isolated in the service's own requirements).
- **Note**: `services/realtime_agent/.venv`, `__pycache__`, `.pytest_cache` are already covered by the root `.gitignore` — no gitignore work needed.

### B.0 — Session lifecycle correctness (do first)

1. Fix the status-transition bug. Add a small `services/realtime_agent/event_bridge.py` (the file the spec names but that's currently missing) that centralizes: (a) the `HOLOGRAM_STATE`/`UI_COMMAND` data-channel publish helpers currently duplicated in `agent.py` and `tools.py`, and (b) opens its own `SessionLocal()` to set `RealtimeSession.status = "active"` after `session.start()` succeeds and `"error"` in the session's `error` handler — consistent with the existing "no HTTP hop, direct DB access" pattern already used by `tools.py`.
2. Migration if new columns are needed beyond reusing `status` (chain off `f3a9c1e7b2d4`, following Part A's `v12_00X` sequential migration convention).
3. Test: extend `test_realtime_sessions_router.py` to assert a created session stays `"creating"` until something marks it active.
4. Keep `backend/app/modules/realtime/` flat for now — do **not** do the domain/application/infrastructure directory split from spec §91 yet; that's premature churn on a 4-file module (Part A's roadmap shows this repo consistently prefers "no new top-level modules, split by file within an existing module" — the same instinct applies here). Defer the literal restructuring to B.8, as its own no-behavior-change commit, once the module's surface area actually justifies it.

### B.1 — Centralize event publishing, extend tool bridge

1. Move the duplicated publish helpers into `event_bridge.py` (B.0); `agent.py` and `tools.py` both import from it.
2. Add `get_project_status(project_id)` / `get_portfolio_status(portfolio_id)` to `backend/app/modules/realtime/tools.py`, calling into existing `strategy/portfolio_service.py` functions (never raw repository queries). Wrap as `@function_tool`s in `services/realtime_agent/tools.py`. Gate behind `FLAG_PORTFOLIO_V12` (already seeded true — reuse Part A's flag, don't add a new one for read access to the same data).
3. Extend `test_realtime_tools.py` for the two new tools, tenant-scoped.

### B.2 — Hologram integration polish

1. Create `frontend/lib/modules/realtime_voice/bindings/realtime_voice_binding.dart`; register `VoiceSessionController` via `Get.lazyPut` in `hologram_hub_binding.dart` instead of the current inline instantiation (match `HologramHubBinding`'s existing conditional-`isRegistered` pattern).
2. Decouple `VoiceSessionController` from `hologram_hub`'s enum: define `RealtimeHologramState` in a new `frontend/lib/modules/realtime_voice/domain/hologram_state.dart`; have `HologramHubController` translate that into its own `HologramRuntimeState` at the consumption point, inverting the current dependency direction.
3. Update `voice_session_controller_test.dart` to assert against the new local enum.

### B.3 — Barge-in / turn-detection tuning

- Add a `turn_detection` config block to `AgentSession(...)` in `agent.py`; check the exact parameter names against the pinned `livekit-agents`/`livekit-plugins-google` version in `services/realtime_agent/requirements.txt` before wiring (do not guess). Make VAD sensitivity/silence-timeout configurable via env vars, not hardcoded (spec §93).
- Document a manual Vietnamese barge-in test checklist in the new README (B.8).

### B.4 — Work / Approval / Navigation

1. Add `get_developer_job_status(job_id)` / `request_developer_job(title, project_id)` tools calling into `backend/app/modules/devices` (reuse `Device`/`DeveloperJob`/`JobLease` — confirmed these already implement exactly the Desktop dispatch mechanism spec §27/§56/§121 wants; `DeveloperJob.status` already has `QUEUED→WAITING_FOR_DEVICE→CLAIMED→RUNNING→WAITING_APPROVAL→SUCCEEDED/FAILED/CANCELLED`). Do not build a parallel dispatch table.
2. Voice approval (spec §23/§55): there is no generic `Approval` entity by design — approvals are per-domain (`GateDecision`, `WorkflowApproval`). Add `request_voice_approval(action_type, target_id)` that routes to whichever of those two the action targets; do not invent a new realtime-specific approval table.
3. Extend `NAVIGATION_TARGETS` in `services/realtime_agent/tools.py`. Since Part A deliberately keeps Projects/Portfolios/CEO inside the existing `strategy` tabs and `hologram_hub` (not separate routes), the navigation targets should route into those same existing screens (`strategy`, `next_actions` already exist in the whitelist) rather than assuming new routes will appear — keep the whitelist-in-code pattern.
4. Tests: `test_realtime_tools.py` and `services/realtime_agent/tests/test_tools.py` additions, tenant-scoped.

### B.5 — Idempotency (spec §70, §90.11)

1. Reuse the exact pattern already in `backend/app/modules/tasks/models.py` (verified): `idempotency_key: Mapped[Optional[str]]` + `UniqueConstraint('workspace_id', 'idempotency_key', name='uix_..._workspace_idempotency_key')`. Apply to whatever row consequential voice actions create (`DeveloperJob`, `GateDecision`, `WorkflowApproval`).
2. `services/realtime_agent/tools.py`'s consequential-action tools generate/accept a `voice_command_id` (from the LiveKit tool-call id, or a client-generated UUID) and pass it through.
3. Test: same `voice_command_id` submitted twice must not create two rows.

### B.6 — Transcript & cost policy (spec §38-39, §46-48, §69)

1. Extend env-based config beyond `LIVEKIT_URL/API_KEY/API_SECRET`/`GOOGLE_API_KEY`: add `VOICE_SESSION_MAX_MINUTES`, `VOICE_IDLE_TIMEOUT_SECONDS` (spec §94). Check the existing settings module name in `backend/app/core/` before assuming `config.py`.
2. Add a lean `realtime_events` table (`session_id, event_type, payload JSONB, created_at`) — migration chained off B.0's head.
3. Idle-timeout enforcement lives inside `services/realtime_agent`'s session loop (spec §90.3 forbids long-lived audio processing inside FastAPI handlers) — verify the installed `livekit-agents` version's timeout/hook API before implementing.
4. Default transcript policy = `SAVE_SUMMARY` (spec §93/§157): never persist raw transcript by default; store only an end-of-session summary (new nullable `RealtimeSession.summary` column, or a related table if versioning is needed).
5. Test: reconnect scenario — a session ending abnormally and a new session for the same room/user must not duplicate any consequential action (ties to B.5).

### B.7 — Desktop/Mobile hybrid transport (spec §101-139)

Largest remaining chunk; sequence after B.0-B.6.

1. New `backend/app/modules/realtime/transport_resolver.py` — `RealtimeTransportResolver`: pure function of `device_type` + per-workspace/user `AUTO|LOCAL|CLOUD` setting → `livekit_local`/`livekit_cloud`. Only Desktop is eligible for local; Mobile always resolves to cloud (spec §106). Wire into `router.py::create_realtime_session` so `RealtimeSession.transport` is actually resolved instead of hardcoded.
2. LiveKit Local groundwork is infrastructure/deployment work (a local LiveKit server the Desktop shell launches), not `backend/app` code — document it as a distinct sub-task, feature-flagged off by default (`FLAG_DESKTOP_LOCAL_TRANSPORT_V12_2`), and don't let it block the rest of Part B.
3. Model Desktop voice profiles (Profile A "Local Efficient", B "Natural Realtime" = today's Gemini Live setup, C "Local Private") as a setting consumed by `session_context.py`/`agent.py`. Only implement the setting + resolver for A/C in this pass (stub as "not yet available"); do not half-build local STT/TTS.
4. Tests: resolver unit tests (Desktop+AUTO+no local available → falls back to cloud per §127; Mobile always → cloud regardless of setting).

### B.8 — Observability, docs, directory hygiene

1. Write `services/realtime_agent/README.md`: how to run the worker, the separate-venv rationale (pull from existing code comments), required env vars, relationship to `backend/.env`.
2. Add a `voice_usage_records` table (`session_id, duration_seconds, model_profile, estimated_cost`) written at `end_session`.
3. Add `GET /api/v1/realtime/health` reporting config sanity (LIVEKIT_URL/GOOGLE_API_KEY presence) — not a live worker ping.
4. Only now, if still desired, do the literal `backend/app/realtime/domain|application|infrastructure/api` split from spec §91, as its own isolated commit.
5. Update `DEPLOYMENT.md` with the `services/realtime_agent` process and any Desktop-local-transport process from B.7 — follow Part A's precedent of documenting the migration chain and any new startup requirement.
6. Once Part B stabilizes, write a `docs/architecture/MCOSA_V12_2_LIVEKIT_ROADMAP.md` mirroring Part A's roadmap doc format (mapping table, status-by-phase, actual API surface, feature flags, resolved/remaining items) so Part B gets the same audit trail Part A has.

### B.9 — Explicitly deferred

Multimodal (screen share/video) and telephony are spec non-goals for MVP (§96) — do not schedule until B.0-B.8 are in production with clear business need.

### Verification
- `pytest backend/app/tests/test_realtime_sessions_router.py backend/app/tests/test_realtime_token_service.py backend/app/tests/test_realtime_tools.py -q`
- `cd services/realtime_agent && python -m pytest tests/ -q` (its own venv — never run under backend's)
- `flutter test frontend/test/voice_session_controller_test.dart`
- Manual: two sessions from different workspaces confirming no cross-tenant tool-result leakage; a reconnect-without-duplicate-action run.

---

## Part C — Agent Memory (greenfield, PoC-gated)

Nothing exists yet in `backend/app`. Follow the spec's explicit MEM-0 → MEM-1 → go/no-go gate sequencing (§209) literally — do not build MEM-2+ speculatively.

### C.0 — ADRs first

Write `ADR-MEM-001` (AgentMemoryGateway boundary) and `ADR-MEM-002` (local sidecar, not a hard TencentDB dependency) before writing any gateway code — spec §210.22 explicitly requires an ADR for any design that makes TencentDB a hard dependency. `docs/adr/` already exists in this repo (currently empty) — use it, following whatever ADR template convention gets established there (or a simple `ADR-MEM-001-agent-memory-gateway.md` numbered-title format if none exists yet).

### C.1 — MEM-0: Adapter boundary only (no production prompt integration)

1. New `backend/app/modules/agent_memory/`:
   - `gateway.py` — abstract `AgentMemoryGateway` (spec §145's exact method list: `capture`, `recall`, `search`, `get_task_context`, `get_scenario`, `get_profile`, `end_session`, `promote_candidate`, `forget`, `export`).
   - `adapters/tencentdb_adapter.py` — first concrete implementation, local sidecar over `localhost` only (spec §146/§178: loopback-only, never publicly exposed).
   - `adapters/null_adapter.py` — no-op adapter returning empty/unavailable results; wired as default when the flag is off or the sidecar is unreachable, so graceful degradation (spec §181) exists from day one.
   - `health.py` — `agent_memory_health` (spec §180: `status/latency_ms/backend/index_status/last_compaction/last_backup/last_error`; states `HEALTHY|DEGRADED|UNAVAILABLE|REBUILDING`).
2. New flag `FLAG_AGENT_MEMORY_V12_3` in `backend/app/core/feature_flags.py`, default off.
3. Models (`backend/app/modules/agent_memory/models.py`, integration metadata only — never the sidecar's internal schema, spec §183): `AgentMemoryEngine`, `AgentMemoryScope`, `MemoryCandidate` (exact shape per spec §184), `MemoryPromotion`, `MemoryEvaluation`, `MemorySyncRecord`, `MemoryHealthSnapshot`. All Snowflake-ID'd, all `workspace_id`-scoped. Migration chained off whatever is Alembic head at implementation time (likely after Part B's additions).
4. API: `backend/app/modules/agent_memory/router.py` — only `GET /memory/status` and `GET /memory/health` in this phase. Don't expose `recall`/`search`/`forget`/`candidates`/`promote`/`compact` until the capture/recall behavior behind them actually exists (later MEM phases). Register in `main.py` at `/api/v1/memory`.
5. Tests: gateway contract test against the null adapter, health endpoint test, flag-off behavior test.

### C.2 — MEM-1: Claude Code task-continuation PoC (the only integration allowed before the gate)

1. Scope strictly to Claude Code (spec §148/§212) — do not touch DeepSeek chat, LiveKit voice, or founder profile yet.
2. Before inventing a capture hook, check whether `backend/app/modules/devices`' `DeveloperJob` lifecycle (worktree_path, diff_summary, test_results, status transitions) is the natural capture point — a `DeveloperJob` completing/failing is exactly the "tool output / test logs / errors / decisions" spec §148 wants captured.
3. Implement capture on `DeveloperJob` status transitions, calling `AgentMemoryGateway.capture(event)` with a redacted summary. Implement `redact.py` with the explicit secrets-exclusion pattern list from spec §179 (API keys, access/refresh tokens, passwords, private keys, seed phrases, session cookies, authorization headers, connection strings with credentials) and unit-test every pattern.
4. Implement recall via whatever tool-exposure mechanism Claude Code already uses in this repo (check for an existing MCP server config before building a new one), returning task status/changed files/tests/known issues/pending step/last artifact.
5. Run **PoC Benchmark A** (spec §174) literally on a real half-finished feature: end a Claude Code session, resume the next day, measure resume time / files reread / tokens / incorrect assumptions / tests passed / task success, with vs. without memory. Record results.
6. Run **PoC Benchmark C** (spec §176, isolation) even at this scope since it's cheap and catches leakage early: two fake projects with conflicting facts (DB=Postgres vs DB=SQLite), assert scoped recall never cross-contaminates.

### C.3 — Go/No-Go gate (spec §177) — hard stop

Evaluate against all of: zero cross-project leakage in the security test suite, acceptable recall quality, materially improved resume time, decreased context/token pressure, stable memory service, acceptable operational complexity, working backup/forget. **If it fails, swap the adapter behind `AgentMemoryGateway` without touching any domain code that calls it** — this is exactly why C.1's abstraction must be strict. Record an explicit decision (short ADR or decision doc, spec §215) before proceeding either way.

### C.4 — MEM-2 through MEM-7 (only if C.3 passes; each its own phase)

- **MEM-2**: large tool results → artifact refs + compact memory node + task canvas (extends C.2's capture to be selective).
- **MEM-3**: full isolation/security at the gateway's `recall`/`search` methods (not just the router), plus spec §159's five explicit adversarial leakage tests (org isolation, project isolation, agent-scope isolation, human-personal isolation, mobile-cloud vs desktop-local isolation). Treat as P0, gate before any multi-project use.
- **MEM-4**: DeepSeek chat selective recall — extend the existing chat context-assembly function (find it in `backend/app/modules/chat` first) to optionally pull budgeted `AgentMemoryGateway.recall()` results.
- **MEM-5**: Founder Memory + Memory Inspector UI (spec §205-207) — new Flutter screen for white-box inspection/confirm/dispute/forget, plus candidate-only Founder Operating Profile updates (never auto-write to the structured profile). Given Part A's precedent of preferring existing tabs/dialogs over new modules, evaluate whether this fits as a dialog inside an existing settings/strategy screen before defaulting to a new top-level module.
- **MEM-6**: LiveKit voice summary/candidate memory only — do this after Part B's B.6 transcript-summary work lands (natural dependency).
- **MEM-7**: Memory → Improvement Proposal → SOP/Skill/Playbook governance loop — reuse whichever "governed candidate" mechanism the Knowledge Engine already has for AI-generated updates (spec §62.14) rather than inventing a new one.

### Verification
- `pytest backend/app/tests/test_agent_memory_*.py -q`, with the MEM-3 leakage suite treated as security-critical and run in CI on every subsequent change to the module.
- `rg -n --glob '!build/**' '(:8888|backend/server|javis/|web_socket_channel)' frontend/lib` stays clean.
- Confirm the local memory sidecar is not reachable from outside `127.0.0.1` (integration test or documented manual check).

---

## Overall sequencing and priority

1. **Part A.1 verification pass** first (half a day) — confirm the audited "DONE" state still holds before building anything else on top of it (Part B's tool bridge already depends on Part A's services, so a silent Part A regression would surface as a confusing Part B bug otherwise).
2. **Part B.0 → B.6** next — closes correctness gaps in code that already exists and is uncommitted; land before B.7's larger infrastructure lift. This is the highest-leverage *new* work in this plan, since B is furthest along of the two remaining parts and already has real tests and a working voice loop.
3. **Part B.7 → B.9** after B.0-B.6 — genuinely new infrastructure (local LiveKit server, Desktop profiles) with deployment implications; don't let it block B.0-B.6 from shipping.
4. **Part C.0 → C.3** can start anytime after Part B.0-B.6 are staffed — intentionally small (adapter + PoC only) with an explicit stop condition, safe as a single-engineer side-track. Never staffed at the expense of B's correctness fixes.
5. **Part C.4+** only after the go/no-go gate passes **and** Part B.6 (transcript/cost policy) has landed (MEM-6 depends on it) — keep last regardless of gate outcome.

**Non-blocking rule**: Part C's PoC failing or being slow must never delay Part B releases (Part A needs no further releases from this plan). This is architecturally enforced by the `AgentMemoryGateway` abstraction (swap adapters, not domain code) and product-enforced by spec §181's graceful degradation and §215's "no System-of-Record responsibility."

---

## Critical files to open first

- `docs/architecture/MCOSA_V12_ROADMAP.md` — read this before touching anything under `backend/app/modules/strategy/` or `frontend/lib/modules/strategy/`; it is the authoritative status record for Part A and documents *why* certain things (like the module-split) were deliberately not done.
- `backend/app/modules/realtime/router.py` + `services/realtime_agent/agent.py` — the two halves of Part B's session lifecycle that must stay in sync (B.0/B.1).
- `backend/app/modules/tasks/models.py` — the idempotency-key pattern to replicate verbatim for B.5.
- `backend/app/modules/devices/models.py` — `Device`/`DeveloperJob`/`JobLease`: Part B's Claude Code dispatch mechanism (B.4) *and* Part C's most natural memory-capture hook (C.2) — read once, reuse twice.
- `backend/app/core/feature_flags.py` — every new flag across Part B/C registers here; follow the naming convention of the 14 flags Part A already defined.
