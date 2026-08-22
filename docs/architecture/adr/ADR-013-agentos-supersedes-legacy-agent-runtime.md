# ADR-013: `agentos/` is the target agent-runtime architecture; `legacy/agent_runtime` is phased out

## Status

Accepted (2026-08-22), user-confirmed. Extends ADR-012's decision (which covered `legacy/backend`'s LLM Gateway/OAuth/n8n/Sandbox capabilities) to the **agent orchestration/runtime layer specifically** — `legacy/agent_runtime/workforce/agents/*` (ADK orchestration, GovernanceKernel, TaskBoardService, ModelGateway, DeepSeek Harness adapter) — which ADR-012 did not address and which `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` (dated 2026-08-20, before ADR-012) still lists as "Canonical production."

## Context

Per `docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md` (Part A1/A2/A10), `agentos/` already re-implements the blueprint's Agent Core, Multi-Agent, Skill Ecosystem, Memory, and Self-Improvement layers — in most cases more completely than `legacy/agent_runtime`'s ADK-based equivalent (e.g. Memory: `agentos/memory/` has a real MemoryStore/consolidation pipeline, `legacy/agent_runtime` has only a minimal models file). But `legacy/agent_runtime` is what actually runs production traffic today: `AdkCofounderWorkflow`, `TaskBoardService`, `GovernanceKernel`, `reliability/model_gateway.py` (LiteLLM-based), and the DeepSeek Harness adapter are wired into the real orchestration path per the ownership map.

Two governance/policy implementations exist with **incompatible vocabularies**:
- `agentos/core/policy.py` — `PermissionClass` (11 capability tags: READ_LOCAL...FINANCIAL_ACTION), static ALLOW/DENY/REQUIRE_APPROVAL table, no per-agent trust tiering.
- `legacy/agent_runtime/cosa_core/governance/policy_engine.py` — `PermissionLevel` (L0_READ/L1_SUGGEST/L2_DRAFT/L3A_EXECUTE_WITH_APPROVAL/L3_EXECUTE) + per-tool risk (R0-R4) + `ExecutionMode` (INTERACTIVE/APPROVED_WORKFLOW/AUTONOMOUS_SAFE) + `PROTECTED_CORE_RESOURCES` immutability list — richer, actively used in production.

Two ModelGateway implementations exist, not the same class: `agentos/core/adapters/model_gateway.py` (self-contained httpx, built per ADR-012 after `legacy/backend` was frozen) vs `legacy/agent_runtime/workforce/agents/reliability/model_gateway.py` (LiteLLM-based, production).

Two workflow engines exist (see ADR-015).

## Decision

1. **`agentos/` is the target architecture for the agent runtime layer**, consistent with ADR-012's framing of `agentos/` + `services/` as the target canonical system overall. `legacy/agent_runtime` is **not deleted immediately** — it keeps serving production traffic until each of its capabilities has a proven equivalent in `agentos/`, following the same "prove an end-to-end flow before cutover" gate ADR-012 already established for `legacy/backend` (ADR-012 Decision §2).
2. **Governance vocabulary**: see ADR-014 — `legacy/agent_runtime`'s `PermissionLevel` (L0-L3A-L3) + risk model is adopted as canonical, ported into `agentos/core/policy.py`, replacing `PermissionClass` as the primary decision mechanism.
3. **Multi-agent orchestration** (`TaskBoardService`, ADK delegation nodes): `agentos/agents/agent_registry.py` + `agentos/agents/parallel.py` are the target, but do not yet reach feature parity with `TaskBoardService` (durable delegation, worker leases, retry/cancel/continuation — see ownership map row "Durable multi-agent delegation"). Phase-out of `TaskBoardService` happens only after `agentos/` has an equivalent durable delegation mechanism, not before — do not cut over on the strength of this ADR alone.
4. **ModelGateway**: `agentos/core/adapters/model_gateway.py` is the target. Provider coverage gap: `legacy/agent_runtime/workforce/agents/reliability/model_gateway.py` uses LiteLLM (broader provider support); `agentos/`'s version currently covers DeepSeek/OpenAI/OpenRouter/Anthropic only (per ADR-012's "Follow-up: LLM Chat Gateway delivered self-contained" note) — Gemini/Kira/apiai_vn not yet ported. Track as a gap, not a blocker to this ADR.
5. **No new code should be added to `legacy/agent_runtime`** going forward except compatibility fixes, per CLAUDE.md §16 and the ownership map's "Rules for new code." New agent-runtime capability work happens in `agentos/`.

## Consequences

- This ADR does **not** authorize an immediate cutover — it sets direction. `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`'s rows for `legacy/agent_runtime/workforce/agents/{orchestration,delegation,governance,reliability}` should be updated to note "target: superseded by `agentos/`, see ADR-013" rather than removed, until each capability has a migration completed (this is Giai đoạn 5 in the gap analysis roadmap).
- Every future gap-closing task in `agentos/` (Giai đoạn 3 of the gap analysis) should be evaluated against "does this bring `agentos/` closer to parity with the `legacy/agent_runtime` capability it's meant to replace" — not built speculatively.
- `agentos/core/policy.py`'s `PermissionClass` is not deleted outright; see ADR-014 for its transition role.
- The workflow-engine choice is decided separately in ADR-015 (also affected by this ADR's overall direction).
