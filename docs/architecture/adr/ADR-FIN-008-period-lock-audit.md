# ADR-FIN-008: Period locks and mutations are audited
## Status
Accepted (2026-08-13)
## Context
Closed accounting data needs controlled reopening and an audit trail.
## Decision
LOCKED periods reject writes; admin-authorized reopen and finance mutations use `core/audit.py`.
## Consequences
Financial history is workspace-scoped, explicit, and reviewable.
