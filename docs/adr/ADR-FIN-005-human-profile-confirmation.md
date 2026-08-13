# ADR-FIN-005: Human confirmation activates accounting profiles
## Status
Accepted (2026-08-13)
## Context
Software must not silently classify a company's accounting eligibility.
## Decision
Profiles move to ACTIVE only with `confirmed_by` from an authenticated user.
## Consequences
Activation is explicit and audited.
