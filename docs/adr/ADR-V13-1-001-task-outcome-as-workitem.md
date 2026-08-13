# ADR-V13-1-001: Task + Outcome play the WorkItem role
## Status
Accepted (2026-08-13)
## Context
The V13.1 source spec assumes a `WorkItem` table. No such table exists in this repo. `Task` already carries the execution state (status, function, execution_mode) and `Outcome` already carries the result contract (desired_result, acceptance_criteria JSONB), but the two trees were unconnected.
## Decision
Do not create `WorkItem`. Pair the existing trees with a nullable `outcomes.task_id` FK and let `Task` + `Outcome` jointly play the role.
## Consequences
No second execution engine, per the standing repo rule. Every spec sentence about a "WorkItem" reads as "the Task and its linked Outcome". The FK is nullable, so pre-existing Outcomes with no Task remain valid.
