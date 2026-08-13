# ADR-V13-1-007: `CompanyRuntimeManager` coordinates, never executes
## Status
Accepted (2026-08-13)
## Context
An orchestration layer is the most likely place for a second execution engine to appear, which the repo rules forbid.
## Decision
`CompanyRuntimeManager` only delegates to existing services — `WorkIntentClassifier`, `DecompositionService`, `DependencyService`, `BlockerRouter`, `NeedsYouService`, `HandoffService`, `CheckpointService` — and reads `Task`/`TaskDependency`. It owns no queue, no worker, and no execution loop, and it does not dispatch work itself.
## Consequences
All real execution stays where it already was: `backend/app/worker_main.py` and the existing `devices` developer-job path, which V13.1 reaches through the Review flow rather than through the manager. The manager is therefore safe to call from a request handler or a LiveKit tool.
