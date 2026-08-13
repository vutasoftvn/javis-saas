# ADR-V13-2-001: WorkItem Reuse in Sales OS

## Context
Spec proposed introducing custom execution primitives for Sales.

## Decision
Reuse existing `Task` + `Outcome` for work execution. `SalesOpportunity` and `SalesLead` state machines (`stage`, `qualification_status`) represent domain entity states, not a secondary runtime engine.
