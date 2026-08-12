# ADR-MEM-002: Agent Memory engine is a local sidecar, never a hard dependency

## Status

Accepted (2026-08-12)

## Context

Spec §210.22 explicitly requires an ADR for any design that would make TencentDB a hard
dependency of mCOSA. Spec §146-147 recommends a local sidecar (SQLite/vector storage) over
a Tencent Cloud database dependency, and §178 requires the sidecar bind to loopback only,
never be publicly exposed, and require authentication where supported.

Postgres already exists in this repo as the system of record (`docs/architecture/CURRENT_STATE.md`).
Agent Memory's job is narrower: cross-session recall and context offload for agents — it
must never become authoritative for Project/Portfolio/OKR/12WY state (ADR-MEM-001's
gateway boundary is what makes this enforceable).

## Decision

1. The Agent Memory engine (TencentDB adapter or any future replacement) runs as a
   **local sidecar process**, bound to `127.0.0.1` by default. It is never a required
   process for `backend/app`/`brain-api` to start or serve any existing endpoint.
2. `backend/app/modules/agent_memory/adapters/null_adapter.py` is the default adapter.
   `TencentDBAgentMemoryAdapter` only activates when `FLAG_AGENT_MEMORY_V12_3` is enabled
   **and** the sidecar responds healthy (`health.py`). Any other state — flag off, sidecar
   down, sidecar erroring — falls back to null-adapter behavior (spec §181: mCOSA "must
   continue operating without Agent Memory").
3. mCOSA-side persistence for this feature (`backend/app/modules/agent_memory/models.py`)
   stores only integration metadata (`AgentMemoryEngine`, `AgentMemoryScope`,
   `MemoryCandidate`, `MemoryPromotion`, `MemoryEvaluation`, `MemorySyncRecord`,
   `MemoryHealthSnapshot` — spec §183-184). The sidecar's own internal schema (whatever
   TencentDB-Agent-Memory uses for L0-L3 memory tiers) stays entirely outside Alembic's
   migration set for `backend/app`.
4. No secrets, API keys, or credentials are ever captured into memory content — see the
   `redact.py` filter introduced alongside the Claude Code PoC (MEM-1), matching spec
   §179's explicit exclusion list.

## Consequences

- A developer can run and test all of `backend/app` with the memory sidecar never
  installed or running — `is_enabled(db, FLAG_AGENT_MEMORY_V12_3, workspace_id)` is false
  by default and `NullAgentMemoryAdapter` handles every call.
- Production deployment of the sidecar is an infrastructure decision independent of
  `backend/app`'s own deploy — same pattern already established for
  `services/realtime_agent` (see `docs/architecture/MCOSA_V12_2_LIVEKIT_ROADMAP.md`).
- If the spec §177 go/no-go gate fails after the MEM-1 Claude Code PoC, the sidecar can be
  decommissioned entirely by deleting the adapter and flipping the flag off — no
  System-of-Record data is at risk because none was ever stored there.
