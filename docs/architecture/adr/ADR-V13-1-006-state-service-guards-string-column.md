# ADR-V13-1-006: `TaskStateService` guards a plain string column
## Status
Accepted (2026-08-13)
## Context
`Task.status` is `String(50)` with no DB enum, and `tasks/router.py::update_task` accepted any status string through an unguarded `setattr` loop. The spec proposes a twelve-state machine.
## Decision
Keep the column a plain string — no DB enum, no migration of existing values. `TaskStateService.transition()` validates a legal-transition map over the six existing values and audits through the existing `core/audit.py::write_audit_log`, which already publishes a domain event. The spec's extra state nuance lives in `work_reviews` and `blockers`, where it is actually observable.
## Consequences
No enum migration and no risk to existing rows. Validation applies only where the service is called; `update_task` routes through it under flag. No new event table.
