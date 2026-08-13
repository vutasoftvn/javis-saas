# ADR-V13-006: Generic cross-function Lessons
## Status
Accepted (2026-08-13)
## Context
Only Marketing previously had a specialized learning loop.
## Decision
Keep `MarketingLearning` and bridge it to the generic `Lesson` model; other Functions write Lessons directly.
## Consequences
Weekly and cycle reviews share learning without weakening Marketing semantics.
