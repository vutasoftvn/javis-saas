# ADR-V13-1-005: Needs You is a read-time pointer table
## Status
Accepted (2026-08-13)
## Context
The founder exception queue draws from Tasks, Blockers, and three separate approval tables. Copying their content into a queue table would create five sources of truth that drift.
## Decision
`needs_you_items` stores pointers only (`source_type`, `source_id`, `priority`, `status`, `snooze_until`) and no duplicated content. The queue is composed at read time against the source tables, following the convention `ai_team/service.py::get_function_statuses()` already set.
## Consequences
An item can never show stale content. Snooze and priority are queue-local concerns and live on the pointer. A deleted source row must be tolerated by the read path rather than cascading.
