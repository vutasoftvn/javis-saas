# mCOSA V12.3 — Hierarchical Agent Memory Roadmap

## Status: MEM-0 and MEM-1 infrastructure DONE; PoC benchmarks NOT YET RUN; go/no-go gate PENDING (2026-08-12)

`mCOSA_V12_3_Consolidated_Project_Portfolio_LiveKit_Agent_Memory.md` Part C proposes
integrating TencentCloud/TencentDB-Agent-Memory as an optional local sidecar for
cross-session agent recall and context offload, distinct from `backend/app/modules/vault`
(governed Knowledge) and PostgreSQL (system of record). Nothing "agent memory"-shaped
existed anywhere in `backend/app` before this session — this is genuinely greenfield work.

The spec is explicit (§209, §212) that this must be built in strict phase order — MEM-0
(adapter boundary only, no prompt integration) → MEM-1 (Claude Code task-continuation PoC,
the *only* integration allowed before the gate) → **go/no-go gate** (§177) → MEM-2 onward,
only if the gate passes. This document records what was actually built for MEM-0/MEM-1 and
states plainly that the gate itself has not been evaluated, because evaluating it requires
a real multi-day operational trial (spec §174 Benchmark A) that cannot be run inside a
single engineering session — it needs a live TencentDB-Agent-Memory sidecar and a real
half-finished feature worked on across two actual Claude Code sessions a day apart.

---

## What's built (MEM-0)

`backend/app/modules/agent_memory/`:

- `gateway.py` — abstract `AgentMemoryGateway` (spec §145's exact method list: `capture`,
  `recall`, `search`, `get_task_context`, `get_scenario`, `get_profile`, `end_session`,
  `promote_candidate`, `forget`, `export`). Domain code depends only on this
  (ADR-MEM-001).
- `adapters/null_adapter.py` — `NullAgentMemoryAdapter`, the default whenever the flag is
  off or the engine is unreachable. Every gateway method returns an empty/unavailable
  shape rather than raising.
- `adapters/tencentdb_adapter.py` — `TencentDBAgentMemoryAdapter`, a thin HTTP facade over
  a local sidecar at `http://127.0.0.1:8765` (loopback only, ADR-MEM-002). **The exact HTTP
  paths/payload shapes are this adapter's own placeholder contract** — they have not been
  verified against a pinned TencentCloud/TencentDB-Agent-Memory release (spec §216
  requires pinning a specific release, not tracking latest). Every call degrades to the
  null-adapter shape on any connection/timeout error.
- `health.py` — `check_sidecar_health()` (spec §180: `HEALTHY|DEGRADED|UNAVAILABLE|REBUILDING`).
  Confirmed working against this dev environment's actual state: no sidecar is running, and
  the check correctly reports `UNAVAILABLE` without raising or hanging.
- `service.py` — `get_gateway(db, workspace_id)`: resolves `NullAgentMemoryAdapter` when
  `FLAG_AGENT_MEMORY_V12_3` is off (default), `TencentDBAgentMemoryAdapter` when on. Callers
  never check the flag themselves.
- `models.py` — integration metadata only (spec §183-184, ADR-MEM-002): `AgentMemoryEngine`,
  `AgentMemoryScope`, `MemoryCandidate`, `MemoryPromotion`, `MemoryEvaluation`,
  `MemorySyncRecord`, `MemoryHealthSnapshot`. Migration `cce0693a148d`. The sidecar's own
  internal schema stays entirely outside this migration set.
- `redact.py` — secrets-exclusion filter (spec §179's exact list: API keys, access/refresh
  tokens, passwords, private keys, seed phrases, session cookies, authorization headers,
  connection strings with credentials). 12 named patterns + a seed-phrase heuristic, each
  with its own test.
- `router.py` — `GET /api/v1/memory/status`, `GET /api/v1/memory/health` (MEM-0), plus
  `GET /api/v1/memory/task-context/{job_id}` (MEM-1, see below).
- `FLAG_AGENT_MEMORY_V12_3` (`agent_memory_v12_3`) in `backend/app/core/feature_flags.py`
  — **not seeded, off by default**, following the same pattern as
  `desktop_livekit_local_v12_2`.

ADRs: `docs/adr/ADR-MEM-001-agent-memory-gateway-boundary.md`,
`docs/adr/ADR-MEM-002-local-sidecar-not-hard-dependency.md`.

## What's built (MEM-1 — Claude Code PoC, the only integration before the gate)

Scoped strictly to Claude Code per spec §148/§212 — DeepSeek chat, LiveKit voice, and
founder profile are untouched.

- **Capture**: `claude_code_capture.py::capture_developer_job_completion(db, workspace_id, job)`.
  `backend/app/modules/devices`' `DeveloperJob` lifecycle (already tracking
  `worktree_path`/`diff_summary`/`test_results`/`status`) turned out to be exactly the
  natural capture point spec §148 describes — no new capture hook was invented. Wired into
  `devices/router.py::submit_job_results_endpoint` (fires only on terminal
  `SUCCEEDED`/`FAILED` status, `diff_summary` passed through `redact_text()` first, never
  raises — a capture failure cannot break the device's job-completion response).
- **Recall**: `GET /api/v1/memory/task-context/{job_id}` → `gateway.get_task_context(job_id)`.
  No existing MCP server config was found in this repo to expose this as a Claude Code
  tool directly (checked for `.mcp.json`/`.claude/` at the repo root — neither exists), so
  MEM-1 exposes recall as a plain authenticated REST endpoint rather than fabricating an
  MCP integration that isn't actually wired to the Claude Code CLI. Wiring this into a real
  MCP server (so Claude Code can call it as a tool mid-session) is unstarted follow-up work,
  not represented as done here.

---

## What was NOT done — and why

**PoC Benchmark A (spec §174, resume-time comparison) has not been run.** This requires:
1. A real half-finished feature, worked on in one Claude Code session.
2. That session ending, a day passing.
3. A second Claude Code session resuming, once with the memory capture/recall path wired
   in and once without, comparing resume time / files reread / tokens / incorrect
   assumptions / tests passed / task success.

This is an operational trial spanning real elapsed time and a live `TencentDBAgentMemoryAdapter`
target (the sidecar itself was never stood up this session — no TencentDB-Agent-Memory
process was installed or run). It cannot be simulated or fabricated inside a single
engineering session without producing dishonest numbers. **This is the literal next step**
before any go/no-go decision.

**PoC Benchmark C (spec §176, isolation) has not been run against a real backend.** A
lightweight proxy exists — `test_agent_memory_claude_code_capture.py` confirms
`workspace_id` is included in every captured event, i.e., our side correctly *sends* scope
information — but this is not the same as verifying a real sidecar correctly *enforces*
that scope on `recall`/`search`. That verification requires the sidecar to actually exist
and be queried with two conflicting-fact fake projects (spec §176's exact test). Deferred
to MEM-3, which is explicitly a full isolation/security phase with adversarial leakage
tests (spec §159) — doing a partial version of it now against a facade with no real
backend would produce a false sense of security.

## Go/No-Go Gate (spec §177): PENDING, not evaluated

None of the gate's criteria (zero cross-project leakage, acceptable recall quality,
materially improved resume time, decreased context/token pressure, stable memory service,
acceptable operational complexity, working backup/forget) have been measured, because the
sidecar this adapter targets has never been run. **Do not proceed to MEM-2 (context
offload), MEM-3 (isolation/security), MEM-4 (DeepSeek chat), MEM-5 (Founder Memory), MEM-6
(LiveKit voice), or MEM-7 (learning loop) until this gate is actually evaluated** — that is
the entire point of building `AgentMemoryGateway` as a strict abstraction (ADR-MEM-001):
the adapter can be swapped or the feature can be shelved without any caller code changing,
specifically so this incomplete state is safe to leave as-is.

### Next steps to actually evaluate the gate

1. Pin a specific TencentCloud/TencentDB-Agent-Memory release (spec §216 — do not track
   `latest`). Install and run it locally, bound to `127.0.0.1:8765` per
   `TencentDBAgentMemoryAdapter`'s current default (adjust the adapter's HTTP paths/payload
   shapes against that release's actual API — they are currently untested placeholders).
2. Enable `FLAG_AGENT_MEMORY_V12_3` for one workspace.
3. Run PoC Benchmark A for real, on a real feature, across a real day boundary.
4. Run PoC Benchmark C for real, with two fake projects with conflicting facts, against the
   live sidecar.
5. Record the results against every criterion in spec §177 and write the go/no-go decision
   as its own short ADR or update to this document — do not proceed past this document's
   current "PENDING" state implicitly.

---

## Verification (2026-08-12, MEM-0/MEM-1 infrastructure only)

```
backend: 371 passed, 3 skipped (cd backend && .venv/bin/python -m pytest app/tests -q)
alembic heads: cce0693a148d (single head)
boundary-check: clean
```

`check_sidecar_health()` and `TencentDBAgentMemoryAdapter` were exercised against this
dev environment's actual (sidecar-absent) state and correctly reported
`UNAVAILABLE`/degraded results rather than raising — this confirms graceful degradation
works, not that the adapter's API contract is correct against a real TencentDB-Agent-Memory
instance.
