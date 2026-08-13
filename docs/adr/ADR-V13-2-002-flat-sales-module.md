# ADR-V13-2-002: Flat Module Structure for Sales

## Context
Spec proposed `app/functions/sales/{domain,application,api}` structure.

## Decision
Maintain consistency with existing modules (`finance/`, `marketing/`) by structuring Sales as a flat module `backend/app/modules/sales/` with sub-routers and domain services.
