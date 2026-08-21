# ADR-V13-1-003: `company_runtime` is a flat sibling module
## Status
Accepted (2026-08-13)
## Context
The spec proposes a nested `app/company_runtime/{domain,application,api}` package. This repo has no such parent package anywhere; backend domains are flat siblings under `app/modules` (see ADR-V13-003).
## Decision
New backend code lives at `backend/app/modules/company_runtime/`, shaped like `modules/finance/` (`models.py`, `router.py`, `routers/`, services at the top level).
## Consequences
One repository convention for imports and router mounting. The frontend mirrors this with `frontend/lib/modules/company_runtime/`.
