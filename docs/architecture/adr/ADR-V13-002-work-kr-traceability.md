# ADR-V13-002: Reuse Work-to-KR traceability
## Status
Accepted (2026-08-13)
## Context
Initiatives and weekly commitments already connect execution to key results.
## Decision
Reuse `InitiativeKeyResultLink` and `WeeklyCommitment`; add only nullable Function tags and Outcome cycle scope.
## Consequences
V13 extends the existing execution engine instead of creating WorkItem duplicates.
