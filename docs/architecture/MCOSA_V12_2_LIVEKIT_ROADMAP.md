# mCOSA V12.1/V12.2 — LiveKit Realtime Voice Roadmap

## Status: LK-0 through LK-7 done for the Cloud MVP; LK-8/LK-9 explicitly deferred (audited 2026-08-12)

`mCOSA_V12_3_Consolidated_Project_Portfolio_LiveKit_Agent_Memory.md` (repo root) Part B
describes a hybrid LiveKit Local/Cloud realtime voice architecture on top of V10. Unlike
Part A (see `docs/architecture/MCOSA_V12_ROADMAP.md`), there was no prior audit for this
part — this is the first one, written the same session the work completed.

This document is the mapping table + status-by-phase + actual API surface + feature flag
state for Part B, matching the format of the V12 Project/Portfolio roadmap.

---

## Two-process architecture (as implemented)

```
Flutter (livekit_client)
      │
      ▼
LiveKit (Cloud today; Local infra not built yet)
      │
      ▼
services/realtime_agent          backend/app/modules/realtime
(separate deploy unit, own venv)  (/api/v1/realtime, in brain-api)
      │                                  │
      ├── Gemini Live                    ├── session create/end + token mint
      └── Tool Bridge ──── SessionLocal() directly, no HTTP hop ──┘
```

- `backend/app/modules/realtime/` — Control Plane only: `models.py`, `router.py`,
  `token_service.py`, `tools.py`, `transport_resolver.py`. Flat, not split into the
  spec's suggested `domain/application/infrastructure/api` layout — deliberately deferred
  (see Remaining items) since the module is still small enough that the split would be
  pure churn.
- `services/realtime_agent/` — the actual LiveKit Agents worker process: `main.py`,
  `agent.py`, `tools.py`, `event_bridge.py`, `session_guards.py`, `session_context.py`.
  See `services/realtime_agent/README.md` for how to run it and its separate-venv
  rationale (different `httpx` pin than `backend/` because `google-genai` needs a newer
  version).

---

## Status by phase (spec §89 Phase LK-0..LK-9)

### LK-0 — Contracts: DONE
`RealtimeSession` model, `POST /sessions`, `POST /sessions/{id}/end`, `token_service.py`
(LiveKit JWT via `livekit.api`). Migration `f3a9c1e7b2d4`.

### LK-1 — Flutter Connection: DONE
`frontend/lib/modules/realtime_voice/`: `RealtimeSessionGateway` abstract contract,
`LiveKitRealtimeSessionGateway` (package:livekit_client), `RealtimeSessionApi`,
`VoiceSessionController`. Registered via `RealtimeVoiceBinding` in `hologram_hub_binding.dart`
(previously constructed inline, bypassing GetX DI — fixed same session as this audit).

### LK-2 — Voice Agent: DONE
`services/realtime_agent/agent.py`: `AgentSession` + `livekit.plugins.google.beta.realtime.RealtimeModel`
("Puck" voice), hologram-state event handlers, barge-in via built-in interruption handling.

### LK-3 — Tool Bridge: DONE
`backend/app/modules/realtime/tools.py` / `services/realtime_agent/tools.py` — full set:
`get_ceo_brief`, `get_next_best_actions`, `get_project_status`, `get_portfolio_status`,
`get_developer_job_status`, `request_developer_job`, `get_pending_approvals`,
`approve_action`, `reject_action`, `open_navigation`. All call into existing Part A/V10
application services (`hub_service`, `NextBestActionService`, `PortfolioService`,
`devices.create_developer_job`, `workflows.router.approve_workflow_step`/
`reject_workflow_step`) — no raw repository access, no parallel execution path.

### LK-4 — Hologram Integration: DONE
`event_bridge.py` centralizes `HOLOGRAM_STATE`/`UI_COMMAND` data-channel publishing
(previously duplicated inline in `agent.py` and `tools.py`). `VoiceSessionController` owns
a module-local `RealtimeHologramState` enum (`realtime_voice/domain/hologram_state.dart`)
instead of importing `hologram_hub`'s `HologramRuntimeState` directly — `HologramHubController`
translates via an `ever()` worker, inverting the previous cross-module dependency.

### LK-5 — Interruption: DONE (tuning knobs only, not a Vietnamese benchmark)
`agent.py::_build_turn_handling()` wires `turn_handling` (this repo's pinned
`livekit-agents==1.6.9` already deprecated the old `min_endpointing_delay`/`allow_interruptions`
kwargs in favor of `TurnHandlingOptions` — confirmed by inspecting the installed package
before wiring, not guessed) via `VOICE_MIN_ENDPOINTING_DELAY`, `VOICE_MAX_ENDPOINTING_DELAY`,
`VOICE_INTERRUPTION_ENABLED`, `VOICE_INTERRUPTION_MIN_DURATION` env vars. Defaults match the
SDK's own defaults exactly (verified by a test asserting `_build_turn_handling()` with no
env vars set reproduces `EndpointingOptions`/`InterruptionOptions` defaults byte-for-byte).
No automated Vietnamese latency benchmark exists — manual checklist in `services/realtime_agent/README.md`.

### LK-6 — Work / Approval / Navigation: DONE
- Work: `get_developer_job_status`/`request_developer_job` reuse `Device`/`DeveloperJob`/
  `JobLease` (`backend/app/modules/devices`) — confirmed this is already the Desktop
  Claude Code dispatch mechanism, no second one built.
- Approval: `get_pending_approvals`/`approve_action`/`reject_action` reuse
  `workflows.router.list_workflow_approvals`/`approve_workflow_step`/`reject_workflow_step`
  — there is no generic `Approval` entity by design in this repo, and none was added.
- Navigation: `NAVIGATION_TARGETS` whitelist (`dashboard`, `tasks`, `vault`, `strategy`,
  `next_actions`) enforced in code, unchanged — Part A kept Projects/Portfolios/CEO inside
  existing `strategy` tabs and `hologram_hub` rather than new routes (see
  `MCOSA_V12_ROADMAP.md`'s "Module-split decision"), so no new navigation targets were
  needed.

### LK-7 — Observability / Cost: DONE
- `realtime_events` table (`RealtimeEvent`) — `SESSION_CONNECTED`/`SESSION_ERROR` written
  by `event_bridge.py`, only on an actual status transition (not on skipped/no-op paths).
- `voice_usage_records` table (`VoiceUsageRecord`) — one row per session, written at
  `end_session` with computed `duration_seconds`; `estimated_cost` stays null (no pricing
  model wired up yet — deliberately not guessed).
- `RealtimeSession.summary` (nullable) — optional end-of-session summary accepted by
  `POST /sessions/{id}/end`; raw transcript is never accepted or persisted (SAVE_SUMMARY
  default, spec §38/§93/§157).
- `IdleGuard` (`session_guards.py`) closes the session after `VOICE_IDLE_TIMEOUT_SECONDS`
  of *continuous* "away" user state (distinct from `AgentSession`'s own 15s
  `user_away_timeout`, which only flips state) — unit-tested with injectable
  schedule/cancel/close, no real event loop needed. A separate hard cap,
  `VOICE_SESSION_MAX_MINUTES`, closes the session regardless of activity.
- `GET /api/v1/realtime/health` — config sanity (LIVEKIT_*/GOOGLE_API_KEY presence), not a
  live worker ping.
- Idempotency (spec §70/§90.11): `DeveloperJob.idempotency_key` (same
  `UniqueConstraint('workspace_id', 'idempotency_key', ...)` pattern as `Task`) —
  `request_developer_job` passes the LiveKit provider tool-call id
  (`RunContext.function_call.call_id`) through as the key, so a duplicate delivery of the
  same tool call returns the existing job instead of creating a second one. `on_duplicate="reject"`
  on the three consequential-action tools (`request_developer_job`, `approve_action`,
  `reject_action`) adds framework-level in-flight dedup as defense-in-depth.

### LK-7.5 — Desktop/Mobile Hybrid Transport groundwork (spec §101-139, V12.2): PARTIAL, deliberately stubbed
`RealtimeTransportResolver` (`transport_resolver.py`) is fully implemented and tested (8
tests: mobile/web always cloud, desktop AUTO/LOCAL/CLOUD × available/unavailable). Wired
into `create_realtime_session` behind `FLAG_DESKTOP_LOCAL_TRANSPORT_V12_2` (**not seeded,
off by default**). `local_available` is hardcoded `False` in `router.py` — there is no
local LiveKit server infrastructure yet (spec §101-102 groundwork), so every real request
resolves to `livekit_cloud` today regardless of flag state, by design. Desktop voice
Profiles A ("Local Efficient")/C ("Local Private") are **not implemented** — no local
STT/TTS integration exists, and none was stubbed with fake behavior; only Profile B
("Natural Realtime" = today's Gemini Live path) is real.

### LK-8 — Optional Multimodal (screen share/video): NOT STARTED, non-goal for MVP (spec §96)

### LK-9 — Future Telephony: NOT STARTED, explicitly out of scope (spec §96)

---

## API surface (actual, as implemented)

```
# backend/app/modules/realtime/router.py — prefix /api/v1/realtime
POST /sessions              body: {device_type, voice_transport?: auto|local|cloud}
POST /sessions/{id}/end     body: {summary?: str}
GET  /health
```

## Feature flags (actual state)

| Flag key | Seeded | Enforced | Notes |
|---|---|---|---|
| `desktop_livekit_local_v12_2` | **not seeded (off)** | yes, in `create_realtime_session` | Deliberately off — no local LiveKit infra exists yet; flipping it on today still resolves to cloud (see LK-7.5). |

No other Part B flags exist — the rest of the tool bridge (CEO brief, next actions,
project/portfolio status, developer jobs, approvals) reuses Part A's existing flags
(`FLAG_NEXT_BEST_ACTION_V12`, `FLAG_PORTFOLIO_V12`) rather than adding new ones for
read-only voice access to the same data.

## Migration chain

```
f3a9c1e7b2d4  add realtime_sessions
b2cc9b34766c  add idempotency_key to developer_jobs
3b8502359c58  add realtime_events + realtime_sessions.summary
aed16401ab42  add voice_usage_records
```

Chained off Part A's `v12_011_flags2` head. Single Alembic head confirmed
(`alembic heads` → `aed16401ab42`) — see `DEPLOYMENT.md`'s Realtime Voice (LiveKit)
section for the human-readable version of this chain.

---

## Verification (2026-08-12)

```
backend:              335 passed, 3 skipped (cd backend && .venv/bin/python -m pytest app/tests -q)
services/realtime_agent: 30 passed (cd services/realtime_agent && .venv/bin/python -m pytest tests/ -q)
alembic heads:         aed16401ab42 (single head)
boundary-check:        clean (rg for :8888|backend/server|javis/|web_socket_channel → no matches)
flutter analyze:       No issues found (scoped to lib/test, excluding vendored build/ output)
flutter test:          4/4 passed (test/voice_session_controller_test.dart)
```

`alembic upgrade head` was not run against a live database this session — the local
Postgres container's credentials didn't match `backend/.env` (pre-existing environment
issue, unrelated to these changes). Migration correctness was instead verified via
`alembic heads`/`alembic history` (script-only, no DB connection needed) plus AST-parsing
each new revision file. Run `alembic upgrade head` for real before deploying.

---

## Remaining items (deliberate, not bugs)

- **`backend/app/modules/realtime/` stays flat**, not split into
  `domain/application/infrastructure/api` (spec §91's suggested layout). The module is
  still 5 files; the literal restructuring is deferred to whenever it actually grows
  enough to justify the churn, as its own isolated no-behavior-change commit — mixing a
  rename with the LK-0..LK-7 behavior changes in this pass would have made review harder
  for no present benefit.
- **No local LiveKit server.** `FLAG_DESKTOP_LOCAL_TRANSPORT_V12_2` and
  `RealtimeTransportResolver` exist and are tested, but `local_available` is hardcoded
  `False` — this is real infrastructure/deployment work (bundling or launching a local
  LiveKit server from the Desktop Flutter shell) that was explicitly out of scope for this
  pass. The only follow-up needed later is supplying a real health check where the
  `local_available = False` comment in `router.py::create_realtime_session` says so.
- **Desktop voice Profiles A/C not built.** Only Profile B (Gemini Live, today's only
  path) is real. Building A ("Local Efficient" — local STT + DeepSeek + local TTS) or C
  ("Local Private") without real local STT/TTS integration would have meant shipping fake
  behavior behind a setting — deliberately not done.
- **No automated Vietnamese barge-in latency benchmark.** A manual checklist exists in
  `services/realtime_agent/README.md`; building real automated latency assertions would
  need recorded audio fixtures and is left for a follow-up.
- **`estimated_cost` on `VoiceUsageRecord` stays null.** No per-provider pricing model
  exists in this repo yet; `duration_seconds` and `model_profile` are tracked so a cost
  calculation can be added later without a schema change.
- **Screen share/video (LK-8) and telephony (LK-9)** are explicit MVP non-goals per spec
  §96 — not started, not planned until there's a clear business need.
