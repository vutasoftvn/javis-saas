# ADR-V13-001: Cycle is a read-composed view
## Status
Accepted (2026-08-13)
## Context
`TwelveWeekCycle`, `CycleContract`, and `OkrCycle` already model the operating cycle.
## Decision
Compose the founder Cycle view from `TwelveWeekCycle` and `CycleContract`; keep `OkrCycle` as its OKR-period container.
## Consequences
No duplicate cycle table or competing source of truth is introduced.
