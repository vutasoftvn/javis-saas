# ADR-V13-2-006: Sales to Finance Handoff Boundary

## Context
Spec mandates notifying Finance upon winning an opportunity.

## Decision
Sales creates a `Handoff(from_function="SALES", to_function="FINANCE")` on opportunity stage change to `WON`. Actual invoice/receivable bookkeeping is deferred to Finance domain implementation.
