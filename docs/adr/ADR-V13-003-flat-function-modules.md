# ADR-V13-003: Function modules remain flat siblings
## Status
Accepted (2026-08-13)
## Context
Backend domains are flat packages under `app/modules`, including Marketing.
## Decision
Legal, Sales, Tech, Finance, and Learning remain sibling modules.
## Consequences
Imports and router mounting follow one repository convention.
