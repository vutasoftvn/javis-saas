# ADR-MEM-001: AgentMemoryGateway as the sole boundary for Agent Memory

## Status

Accepted (2026-08-12)

## Context

mCOSA V12.3 (`mCOSA_V12_3_Consolidated_Project_Portfolio_LiveKit_Agent_Memory.md` Part C)
proposes integrating TencentCloud/TencentDB-Agent-Memory as an optional sidecar giving
agents (starting with Claude Code) cross-session recall and context offload, distinct
from `backend/app/modules/vault` (governed company Knowledge) and PostgreSQL (system of
record for Project/Portfolio/OKR/12WY state, per `docs/architecture/MCOSA_V12_ROADMAP.md`).

Nothing "agent memory"-shaped exists in `backend/app` today. The only prior art in this
repo is `backend/server/main.py::_agent_memory()` — a legacy file-based `MEMORY.md`
reader in the reference-only `backend/server/` tree that `CLAUDE.md` explicitly forbids
reusing, importing, or extending.

TencentDB-Agent-Memory is a third-party project whose API surface, storage engine, and
maturity are not yet proven inside this codebase (spec §177's PoC gate exists precisely
because of this uncertainty).

## Decision

`backend/app` domain code depends only on an abstract `AgentMemoryGateway`
(`backend/app/modules/agent_memory/gateway.py`) with the method set specified in spec
§145: `capture`, `recall`, `search`, `get_task_context`, `get_scenario`, `get_profile`,
`end_session`, `promote_candidate`, `forget`, `export`.

Concrete adapters live under `backend/app/modules/agent_memory/adapters/`:

- `NullAgentMemoryAdapter` — always available, returns empty/unavailable results. This is
  the default whenever the feature flag is off or the configured engine is unreachable.
- `TencentDBAgentMemoryAdapter` — the first real adapter, talking to a local sidecar
  process over loopback only (see ADR-MEM-002).

No file outside `backend/app/modules/agent_memory/adapters/` may import TencentDB-specific
types or talk to the sidecar directly. Callers (Claude Code capture hooks, future DeepSeek
chat context building, future LiveKit voice memory) depend only on the gateway interface,
resolved through whichever adapter the config selects.

## Consequences

- Swapping the memory engine (e.g., if the spec §177 go/no-go gate fails for TencentDB)
  means writing a new adapter and changing configuration, not touching any caller.
- The gateway's method signatures become the actual product surface for "what agent
  memory can do" — changes to that contract are deliberate, reviewed changes, not
  incidental to whichever adapter happens to be active.
- `NullAgentMemoryAdapter` makes graceful degradation (spec §181) the *default* behavior
  from the first line of code, not a bolt-on for later.
