# ADR-FIN-004: Domain services compute authoritative figures
## Status
Accepted (2026-08-13)
## Context
Cash, burn, runway, and book balances must be reproducible.
## Decision
Use Decimal-based domain functions; AI may only narrate their returned snapshots.
## Consequences
Golden fixtures verify exact book rows without LLM mocks.
