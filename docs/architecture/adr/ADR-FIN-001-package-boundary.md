# ADR-FIN-001: Deterministic Finance package boundary
## Status
Accepted (2026-08-13)
## Context
Authoritative accounting cannot depend on probabilistic output.
## Decision
All calculations live under `finance/domain`; narration lives under `finance/agent`.
## Consequences
An AST-based CI test rejects LLM imports in deterministic packages.
