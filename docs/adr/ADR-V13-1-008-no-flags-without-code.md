# ADR-V13-1-008: No feature flags for capabilities that do not exist
## Status
Accepted (2026-08-13)
## Context
The spec asks for `false`-valued flags for OpenOPC integration, marketplaces, office animation, and agent free-chat. None of these have any code to gate. ADR-V13-004 already rejected inventing flags with nothing behind them.
## Decision
Create no flags for those four. They are recorded as out of scope in the implementation plan instead. The six P1 workforce-intelligence flags are the deliberate exception: they are seeded `false` as reserved names so the migration chain does not need reopening when that work starts.
## Consequences
`/platform/feature-flags` lists only flags that gate real behaviour, plus six documented reservations. OpenOPC stays a pattern source, never a runtime dependency.
