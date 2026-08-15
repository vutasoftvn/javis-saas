# COSA Cloudflare-OS Integration Plan

> **Source spec:** `COSA_Cloudflare_OS_Integration_v13.1_v13.2.md` (repo root).
> **Related plan:** `docs/architecture/COSA_AGENT_GOVERNANCE_REALIZATION_PLAN.md` (its "Approach B"
> phase is the prior art this plan builds on — see below).
> **Trạng thái:** Roadmap — approved direction, phases not yet implemented (as of 2026-08-15).

## Context

`COSA_Cloudflare_OS_Integration_v13.1_v13.2.md` specifies adapting Cloudflare OS's architecture patterns (Workspace, Capability-based security, Action Center, Provenance, Sandbox, Mini Apps, Blueprints) natively into COSA, without forking Cloudflare OS or replacing FastAPI/PostgreSQL. It was added in commit `c116497` alongside three sibling specs (`COSA_Agentic_Architecture_Adjustment`, `COSA_DSPy_Intelligence_Optimization_Integration`, `COSA_OpenSandbox_Agent_Runtime_Integration`), and that **same commit already implemented a large share of the P0 scope**: execution/sandbox runtime, control plane (goal→plan→step), governance (policy engine, approvals, audit events), n8n adapter, and an embryonic model gateway. The current uncommitted working tree continues that work (state-machine enforcement, retry/fallback, event-schema widening, a `gateway/` route facade).

Two Explore passes over the codebase confirmed this: **Workspace, Policy Engine, Sandbox, and n8n integration are not greenfield** — they already exist and are reasonably mature. The one clear, load-bearing gap versus the target architecture is a **Capability Gateway**: today, policy checks are duplicated inline in two call sites (`control_plane/execution.py`, `execution/service.py`) rather than funneled through one chokepoint, and there's no capability-grant/scope/expiry model, no simulate-before-approve step, and no idempotency enforcement. This plan sequences the integration so it **extends existing modules** (per `CLAUDE.md`'s migration method and the doc's own §45 "reuse existing entities, don't duplicate") rather than reimplementing what's already there, and closes the Capability Gateway / Action Center / Observation gap first, since everything else (Mini Apps, Blueprints, AI Gateway unification) explicitly depends on that foundation being stable (doc §31, §51).

## What already exists vs. what's genuinely new

| Doc concept | Existing code | Verdict |
|---|---|---|
| Workspace / tenancy | `modules/iam/models.py::Workspace`, `WorkspaceMember`; `Brain` as sub-scope; `core/auth.py::get_current_workspace_member`; `core/tenancy.py::get_*_scoped()` helpers | **Reuse as-is.** `workspace_id` is the canonical tenant key everywhere. |
| Policy Engine | `agents/governance/policy_engine.py::PolicyEngine` — L0_READ…L3A/L3 ladder × tool risk_level → ALLOW/DENY/REQUIRE_APPROVAL | **Reuse, don't replace.** Called ad hoc from 2 places; needs one chokepoint. |
| Approval workflow | `agents/governance/models.py::AgentApproval` + `approval_service.py` + `approvals_router.py` (pending→approved/rejected/executed, expiry) | **Extend**, close to doc's `agent_actions` already. Known bug: `execution/service.py` calls a non-existent instance API on `ApprovalService` (static-only class) — will raise if that branch executes. |
| State machine | `agents/governance/states.py` — Run/Plan/Step transition graphs, enforced in `control_plane/execution.py` | **Reuse.** Not yet applied in `orchestration/chief_of_staff.py` (writes status directly). |
| Audit / Observation | `AgentEventRecord` (rich, plan/step/actor/tool-aware) + `AgentToolCall` (schema exists, appears unwritten) | **Extend `AgentToolCall`** into the Observation record instead of a new table. |
| Sandbox | `agents/execution/` — `ExecutionProvider`/`OpenSandboxExecutor`, `SkillManifest`→`SandboxPolicy`, `CredentialBroker`, redaction, artifacts | **Reuse.** Already enforces INV-07 (untrusted sandbox), no ambient secrets. |
| n8n | `automations/runtime/adapters/n8n.py::N8nAdapter` + `agents/execution/n8n_bridge.py` (HMAC-signed) | **Reuse/wrap** as the first `ResourceConnector`. |
| AI Gateway | `agents/reliability/model_gateway.py::ModelGateway` + `model_profiles.py` + `reliability.py` (circuit breaker, retry, cost tracking, fallback) | **Extend**, don't build new `ai_gateway/` module. Separate from chat's own `modules/chat/model_registry.py` path — unify later, not now. |
| Capability Gateway | Nothing dedicated. `agents/gateway/` (untracked) is a pure route-aggregation facade, not an authz broker | **Genuinely missing — this is the core new work.** |
| Provenance | Fragmented (`AgentMemoryItem.provenance_jsonb`, `ArtifactRef.content_hash`) | **New, but built on the extended `AgentToolCall`, not a parallel table.** |
| Context Library | `modules/strategy::ContextPack/ContextPackSource` + `agents/context/builder.py` | **Extend later (P1).** |
| Skill Registry | Only `modules/marketing::SkillRegistry`/`SkillRouter` (workspace-scoped, capability→provider+fallback) — domain-limited | **Generalize later (P1).** |
| Mini Apps, Blueprints, Resource Introduction | Not found anywhere | **Confirmed greenfield, explicitly deferred (P2), per doc's own ADR-006.** |

Also noted, not part of this plan but relevant: `modules/outcomes` (`Outcome`→`OutcomeRun`→`RunStep`, risk_level L0–L4) is a third, separately-evolved goal/execution/approval pattern alongside control-plane's `AgentGoal/Plan/Step` and governance's `AgentApproval`. Recommendation: **keep it separate** — Outcomes is founder-defined broader deliverable tracking, the new Action Center is narrowly AI-proposed capability-gated side effects. Revisit consolidation only if duplication becomes actively painful.

### Prior art: why a general gateway is *now* the right move, not premature

`docs/architecture/COSA_AGENT_GOVERNANCE_REALIZATION_PLAN.md` (2026-08-14) already faced this exact question and **explicitly deferred** building a general "Tool Execution Gateway" (its own name for the same gap): *"Approach A vẫn là điểm đến đúng đắn về lâu dài, nhưng nên là một phase riêng SAU KHI Approach B đã chứng minh giá trị"* — build the narrow, targeted version first (real approval gating on `/automations/{key}/execute`, real `AgentRuntime` call in Chief of Staff, idempotent approval consumption), prove it, then generalize. Verified against the actual repo history: **all 5 steps of that plan are already committed** (`9487cf3`, 24 commits before `c116497`) — `automation_definitions` is seeded, `execute_automation` rejects missing/unapproved/reused approvals, Chief of Staff makes a real `AgentRuntime` call and creates real `AgentApproval` rows, `N8nAdapter.get_status`/`cancel` are real. So Approach B has already proven itself, and the codebase already moved on to build `control_plane/`, richer `governance/`, and the `agents/gateway/` facade on top of it. This plan's Capability Gateway is the "Approach A, as its own phase" step that document itself anticipated — not a premature second execution engine.

## Key adaptation decisions (deviate from the doc's literal schema, with rationale)

1. **Tenancy**: use `workspace_id` as the sole canonical key for all new tables (matches `CLAUDE.md`). `company_id` on agent tables is a legacy alias (`company_id = workspace_id` in practice, per `router_api.py`) — do not build it out as a separate tier the way the doc's SQL examples imply. `brain_id` is used only where a resource is genuinely brain-scoped (e.g. a specific Vault brain's Gmail integration).
2. **Capability Gateway module location**: new `backend/app/agents/capabilities/` (registry + grants + service), mounted through the existing `agents/gateway/router.py` facade — keeps the routing-aggregation layer intact while giving the authz logic its own home.
3. **Action Center**: extend `AgentApproval` (add `capability`, `resource_type`, `resource_id`, `simulation_result_jsonb`, `idempotency_key`) instead of a new `agent_actions` table — reuses the existing router, service, and Flutter `control_plane_service.dart` calls already wired to it.
4. **Observation**: extend `AgentToolCall` (add `resource_type`, `resource_id`, `capability`, `source_version`, `content_hash`) instead of a new `agent_observations` table.
5. **Policy taxonomy**: keep the existing L0_READ…L3A/L3 enforcement ladder as-is; treat the doc's L0–L5 risk classification and `domain.resource.action` capability naming as **metadata the registry uses to select** a `PermissionLevel` + approval requirement, not a parallel enforcement path. Doc's L4 (external side-effect) → `L3A_EXECUTE_WITH_APPROVAL`; L5 (financial/legal critical) → `L3A` plus a `strong_approval` flag (no silent auto-approve, mandatory explicit confirmation, per INV-10).
6. **Mini Apps / Blueprints / Resource Introduction**: out of scope for this plan — correctly sequenced after the gateway/action-center/observation foundation is stable, matching doc §31 and ADR-006.

## Phased implementation

**Phase 0 — Stabilize (bug fixes, no new features)**
- Fix `execution/service.py`'s broken `ApprovalService(db)` instance-call — align to the actual static API (or intentionally fold into the Phase 1 gateway refactor so the call site disappears entirely).
- Make `orchestration/chief_of_staff.py` route its `AgentRun` status writes through `governance/states.py::validate_run_transition()` instead of setting `.status` directly.
- Confirm whether `AgentToolCall` is currently written anywhere (grep before assuming) — if not, note it explicitly as "reserved but unused" ahead of Phase 3.

**Phase 1 — Capability Gateway** (the core net-new piece)
- `agents/capabilities/models.py`: `CapabilityGrant` (Snowflake PK, `workspace_id`, `subject_type`, `subject_id`, `capability`, `resource_type`, `resource_id`, `scope_jsonb`, `granted_by`, `expires_at`, `revoked_at`).
- `agents/capabilities/registry.py`: static `domain.resource.action` catalog → default doc-risk-level → mapped `PermissionLevel` + approval requirement; unknown capability = default deny.
- `agents/capabilities/service.py`: `CapabilityGateway.check(workspace_id, subject_type, subject_id, capability, resource_type, resource_id)` → registry lookup → optional `CapabilityGrant` check → delegates to the existing `PolicyEngine.evaluate()` (reused, not duplicated) → returns ALLOW/DENY/REQUIRE_APPROVAL + risk_level.
- `agents/capabilities/router.py`: `POST /api/v1/capabilities/check` (doc §22.1 contract), grant/revoke/list endpoints; mounted via `agents/gateway/router.py`.
- Migration `v13_043_capability_grants.py` (idempotent-safe, following the existing inspect-before-add convention).
- Refactor the two existing inline `PolicyEngine`/`ToolSpec` call sites (`control_plane/execution.py`, `execution/service.py`) to call `CapabilityGateway.check()` instead — single chokepoint, and the Phase 0 bug disappears as part of this refactor.
- Tests mirroring `test_governance_policy_approval.py`: default-deny, grant/expiry/revoke, decision matrix; regression tests for both refactored call sites.

**Phase 2 — Action Center**
- Migration `v13_044_agent_approval_action_fields.py` widening `AgentApproval`.
- New `ResourceConnector` protocol (`observe/simulate/execute`) in `agents/capabilities/connector.py`; first real implementation wraps the existing `N8nAdapter` (already HMAC-authenticated) with a `.simulate()` that previews without POSTing.
- `CapabilityGateway` on `REQUIRE_APPROVAL` creates/reuses an `AgentApproval` populated with the connector's `simulate()` result; `execute()` only runs post-approval.
- Idempotency: check `idempotency_key` before execute, short-circuit if already run (INV-06).
- Re-validate capability+policy at execute time, not just proposal time (INV-05) — approval alone isn't authorization.
- Flutter: extend `control_plane_service.dart`'s existing approval calls to surface `simulation_result`/`capability`/`resource`; extend the `agents` module UI (reuse `AgentActivityTimelineWidget` patterns) rather than building a new module.

**Phase 3 — Observation / Provenance**
- Migration widening `AgentToolCall` (resource_type/resource_id/capability/source_version/content_hash).
- Wire `control_plane/execution.py` and `execution/service.py` to actually write an `AgentToolCall` row per capability check.
- Skip artifact-lineage join table unless a concrete need surfaces (no speculative schema).

**Phase 4+ (P1/P2, sequenced after 0–3 are stable in production)**
- AI Gateway: let `ModelGateway` own provider clients directly instead of an injected `invoker_fn`; defer unifying with chat's separate model path.
- Skill Registry: generalize `modules/marketing::SkillRegistry`/`SkillRouter` cross-domain.
- Context Library: extend `ContextPack`/`ContextPackSource`.
- Mini Apps / Blueprints / Resource Introduction: not started until 0–3 are stable, per doc's own priority ordering.

## Security invariants (doc §32) — status after this plan

Already enforced today: INV-07 (sandbox untrusted), INV-04 (approval ≠ execution, already two steps), INV-08 N/A (no Blueprints yet). Becomes fully true only after this plan: INV-01/INV-03 (default-deny, no bypass — closed by Phase 1's single chokepoint), INV-05 (revalidate at execute — Phase 2), INV-06 (idempotency — Phase 2), INV-09 (append-only observation — Phase 3), INV-10 (no silent L5 auto-approve — Phase 1 registry mapping + Phase 2 strong-approval flag).

## Verification

- Backend: `cd backend && pytest app/tests/agents/ -q` after each phase; extend `test_governance_policy_approval.py`, `test_control_plane.py`, `test_agent_gateway.py` for the new gateway.
- Migrations: `alembic upgrade head`, verified against both Postgres and the sqlite test bootstrap (existing convention in `v13_040`–`v13_042`).
- Frontend: `flutter analyze` plus widget tests for any Action Center UI changes.
- Manual end-to-end: one real simulate→approve→execute flow through the n8n connector, mirroring doc §33.2's "Email approval" test shape.
- `DEPLOYMENT.md`: add a `## COSA Capability Gateway & Action Center` section (ownership, feature flags `FEATURE_CAPABILITY_GATEWAY`/`FEATURE_ACTION_CENTER`) following the existing pattern used for OpenSandbox/n8n/LiveKit sections.

## Không làm trong plan này (out of scope)

- Mini Apps, Blueprints, Resource Introduction UI/backend — greenfield, deferred to after Phase 0–3 are stable (doc ADR-006, §31).
- Unifying chat's `modules/chat/model_registry.py` path with `ModelGateway` — separate decision, not forced by this plan.
- Re-enabling disabled Strategy/PESTEL/SWOT/TOWS modules — explicitly forbidden by both `CLAUDE.md` and the source doc §2.2.
