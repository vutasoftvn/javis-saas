# AgentOS Self-Improvement Subsystem

## Purpose
Phase 10 Self-Improvement loop:
- Gap detection (`GapDetector`)
- Skill candidate creation & refinement
- Supply chain verification pipeline
- Human approval gate (`ImprovementApprovalGate`)
- Skill promotion to `ACTIVE`

## Ownership
- **Canonical Owner:** `agentos/improvement/`

## Operational Status
- **Status:** `IMPLEMENTED / TESTED / NOT YET WIRED TO PRODUCTION EVAL PIPELINE`

## Remaining Gap & Roadmap
- `GapDetector` currently accepts `CapabilityOutcome` supplied manually by the caller. It does not yet have an automated ingestion feed wired to live evaluation/execution history.
- Wiring this to the real evaluation history is scheduled for **Phase 10 (Observability & Eval)** and is intentionally deferred from Phase 0.
