# ADR-V13-1-002: Revive `TaskDependency` instead of recreating it
## Status
Accepted (2026-08-13)
## Context
The spec asks for a dependency DAG. `task_dependencies` already existed as a table but was completely dead — no reader, no writer, anywhere in the codebase.
## Decision
Extend the existing table with nullable `dependency_type` and `status` columns rather than creating a new DAG table. V13.1's `dependency_service.py` is its first real reader and writer.
## Consequences
No duplicate edge table. Existing rows (there are none in practice) default to `status = 'PENDING'` with a null type. Cycle detection lives in the service layer, not in a DB constraint.
