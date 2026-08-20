# ADR 006: Runtime Event Authority

## Status
Accepted

## Context
In COSA Phase 6, we need a reliable, replayable operational visibility mechanism for workflows and agents. We currently have multiple disparate mechanisms logging activities: `AgentEventRecord`, `AgentToolCall`, audit logs, OpenTelemetry, and some SQLite scaffold for local tracking. To avoid fragmented state, data inconsistency, and split-brain scenarios regarding what "actually happened" during a run, we must define one canonical authority for runtime events.

## Decision
1. **Primary Authority**: PostgreSQL is the single canonical source of truth (append-only event store) for all runtime events.
2. **Local Cache / Projection**: SQLite (if used on edge/client) is strictly an optional local cache and offline projection. It is not a competing server authority. It must tolerate deletion and can be rebuilt entirely from the Postgres cursor.
3. **Immutability**: Event records are append-only facts. Any corrections must be represented as later events (compensating actions), never by mutating existing events in place.
4. **Redaction**: No private reasoning, secrets, raw credentials, provider requests/responses, or unbounded tool output will enter the event log, projection, or UI.
5. **Correlation**: Audit records and OpenTelemetry traces remain separate projections/telemetry. They are linked to the canonical event log via correlation IDs and causation IDs. They do not create a second session authority.
6. **Recovery Rule**: Pause/resume operations must use the persisted workflow version, execution scope snapshot, and the Postgres event cursor. They must not infer a new scope.

## Consequences
- Requires building a deterministic projection engine that reads from the Postgres append-only log to reconstruct states (e.g., Run, Task, Approval).
- Forces UI (Hologram, Run Inspector) to rely entirely on projections rather than raw AI reasoning logs.
- Simplifies debugging and auditability by centralizing the chronological sequence of workflow transitions.
