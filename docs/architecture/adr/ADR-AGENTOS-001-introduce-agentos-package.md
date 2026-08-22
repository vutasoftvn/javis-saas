# ADR-AGENTOS-001: Introduce `agentos/` package as the Agent Core baseline

## Context
`docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` proposes a
target architecture where a small, stable Python "Agent Core" (`agentos/`)
owns reasoning/runtime, while business state stays in domain services. This
is a big-bang blueprint decision, not an incremental refactor of the
existing `cosa_core`/`workforce` modules — see the spec §6 for explicit
conflicts with `CLAUDE.md`'s "smallest safe change" guidance, accepted
knowingly by the user who requested this blueprint.

## Decision
Add a new top-level Python package `backend/agentos/` implementing the
Agent Core primitives from the blueprint: `AgentRun`, `TaskContext`,
`AgentResult`, `AgentContext`, the `Agent` protocol, and canonical event
names (`entity.action`). Phase 1 builds the MVP single-agent runtime loop
on top of these. Existing `cosa_core`/`workforce` code is left untouched in
this phase — no migration, no deletion, no production wiring.

## Consequences
- Two parallel agent-runtime implementations exist during the migration
  window: production traffic keeps flowing through `cosa_core`/`workforce`;
  `agentos/` is inert (no caller wires it into `main.py`) until a later
  phase explicitly cuts traffic over.
- Every new `agentos/` module defines its interface (protocol/pydantic
  model) before any implementation task — Phase 0 tasks are ordered
  strictly before Phase 1 tasks in the implementation plan for this reason.
