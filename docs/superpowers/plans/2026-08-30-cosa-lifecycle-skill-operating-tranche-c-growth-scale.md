# COSA P5–P6 Growth and Scale — Tranche C Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the remaining 23 P5/P6 governed skillpacks and enable only individually proven, bounded business actions for repeatable growth and scale; reach the 95-skill catalog without treating catalog completion as permission to send, spend, sign, hire or deploy.

**Architecture:** The existing capability gateway is the sole execution path and evaluates tenant, connector ownership/readiness, policy, approval, idempotency and audit before a handler. P5/P6 skills resolve a capability only when their manifest declares it, the capability is registered and its target-specific readiness record is green; otherwise they create an artifact/proposal/handoff. Company Services own commercial/finance/operations truth and every mutable workflow has a compensating/rollback path.

**Tech Stack:** Python/FastAPI/Pydantic/Pytest, TypeScript/Encore/Drizzle/PostgreSQL, Flutter/Dart.

**Spec:** `docs/architecture/plans/2026-08-30-cosa-lifecycle-skill-operating-model.md`

## Entry gate and scope

Enter after a human G4 decision, a validated PMF/maturity release (Tranche B2), and a named owner has selected the first repeatable motion. P5 packs become candidates after G4; P6 packs become candidate-only until a human G5 decision confirms repeatability. A pack may be published at 95-catalog completeness but it may not be pinned to execute a side effect until its own readiness evidence exists.

The plan publishes 14 P5 + 9 P6 = **23** packs, raising the catalog from 72 to **95**. It sequences every executable capability by action class, rather than enabling an entire domain at once.

**Out of scope:** autonomous public communication, unbounded/bulk messaging, budget/targeting changes, money transfer, contract signature, hiring/firing decision, production security/identity configuration, cross-workspace automation, automatic G5/G6 pass and automatic lifecycle transition.

## Global constraints

- A capability enablement record is specific to `(capability_id, workspace_id, target/connector, skill_id, skill_hash, action_class)` and expires/revokes independently.
- `R` and `A` can execute only under tenancy/readiness checks; `B`, `X`, `M` and `D` need idempotency/audit/approval as applicable. `M` is human-owned. `D` is human-owned except a separately approved sandbox/rollback envelope.
- “L2-B” means a narrow action with specified target, payload schema, rate/monetary limit, owner, rollback/compensation and approval binding; it never means generic access to a provider.
- Every connector-backed output shows recipient/claim/amount/target preview. No skill is allowed to construct or reuse connector credentials.
- All 23 packs retain the Tranche A immutable lifecycle/evidence/autonomy/eval/attribution contract and have an artifact-only fallback.

## File map

| Path | Responsibility |
| --- | --- |
| `packages/agent/capabilities/{gateway,readiness,grants,idempotency}.py` | Capability readiness and exact invocation enforcement. |
| `apps/cosa/capabilities/{marketing_write,operations_write,engagement_message_draft,finance_write}.py` | Explicit handlers; no direct provider access from skills. |
| `apps/cosa/composition/agent_plane.py` | Explicit per-capability registration. |
| `services/company/{commercial,finance-legal,operations}` | Source of truth, business policy, approval/audit and compensating actions. |
| `skillpacks/{marketing,sales,finance,growth,customer_success,operations,strategy,people}/*` | P5/P6 skill contracts and evals. |
| `frontend/lib/modules/{approvals,skills,marketing,tasks}` | Preview, approval and audit presentation; no raw execute button. |

---

### Task 1: Add a durable capability-enablement registry and fail closed

**Files:**
- Create: `packages/agent/migrations/017_capability_enablements.sql`
- Create: `packages/agent/migrations/017_capability_enablements.down.sql`
- Create: `packages/agent/capabilities/enablements.py`
- Modify: `packages/agent/capabilities/readiness.py`
- Modify: `packages/agent/capabilities/gateway.py`
- Test: `tests/agent/capabilities/test_enablements.py`
- Test: `tests/agent/capabilities/test_gateway.py`

**Interfaces:**
- Produces `CapabilityEnablement` and `assert_enabled_for_invocation(request, skill_ref, target_snapshot)`.
- A missing, expired, revoked, wrong-workspace, wrong-target, wrong-hash or wrong-action-class enablement returns `denied` before a handler executes.

- [ ] **Step 1: Write failing authorization matrix tests**

    enabled = enablement(workspace='ws-a', capability='operations.task.create_draft', skill_hash='abc', action_class='B')
    assert await gateway.execute(request(workspace='ws-a', skill_hash='abc')).status == 'completed'
    assert await gateway.execute(request(workspace='ws-b', skill_hash='abc')).status == 'denied'
    assert await gateway.execute(request(workspace='ws-a', skill_hash='changed')).status == 'denied'
    assert await gateway.execute(request(workspace='ws-a', action_class='X')).status == 'denied'

Also assert an expired or revoked record creates an audit event and no idempotency claim/handler invocation.

- [ ] **Step 2: Run the focused test**

    .venv/bin/python -m pytest tests/agent/capabilities/test_enablements.py tests/agent/capabilities/test_gateway.py -q

- [ ] **Step 3: Implement durable fail-closed lookup**

Persist enablement scope, source approval, target snapshot fingerprint, permitted schema/action limits, owner, expiry/revocation and evaluation/rollback references. The gateway resolves a pinned `SkillSpec` hash from invocation context before readiness. It never treats a manifest capability declaration, a user prompt or `ApprovalPolicy.NEVER` as an enablement.

- [ ] **Step 4: Verify and commit**

    .venv/bin/python -m pytest tests/agent/capabilities/test_enablements.py tests/agent/capabilities/test_gateway.py tests/apps/cosa/composition/test_agent_plane.py -q
    git add packages/agent/migrations/017_capability_enablements.sql packages/agent/migrations/017_capability_enablements.down.sql packages/agent/capabilities/enablements.py packages/agent/capabilities/readiness.py packages/agent/capabilities/gateway.py tests/agent/capabilities/test_enablements.py tests/agent/capabilities/test_gateway.py
    git commit -m "feat(capabilities): require scoped enablement"

### Task 2: Harden bounded internal business writes before enabling them

**Files:**
- Modify: `apps/cosa/capabilities/operations_write.py`
- Modify: `apps/cosa/capabilities/marketing_write.py`
- Modify: `apps/cosa/capabilities/engagement_message_draft.py`
- Modify: `apps/cosa/composition/agent_plane.py`
- Test: `tests/apps/cosa/test_operations_write_capability.py`
- Test: `tests/apps/cosa/test_marketing_write_capabilities.py`
- Test: `tests/apps/cosa/test_engagement_message_draft.py`

**Interfaces:**
- `operations.task.create_draft` requires `project_id`, `evidence_refs`, `decision_reason`, idempotency and scoped B enablement.
- `commercial.campaign_asset.write` remains an internal versioned artifact write; it cannot publish a page/ad/email.
- `commercial.experiment.write` creates an approval-bound draft tied to a metric-contract ID; it cannot activate/spend.

- [ ] **Step 1: Write failing no-bypass tests**

Attempt a task with evidence from another workspace, campaign asset with `public_url`, experiment with no metric contract, and a message draft with a send flag. Assert deny/validation failure; assert exact replay returns the same write; assert connector functions are never invoked.

- [ ] **Step 2: Implement and verify**

    .venv/bin/python -m pytest tests/apps/cosa/test_operations_write_capability.py tests/apps/cosa/test_marketing_write_capabilities.py tests/apps/cosa/test_engagement_message_draft.py -q

Resolve `workspace_id` only from invocation context, add project/evidence/metric references to the Company payload, validate the approval/enablement envelope at the gateway and persist artifact provenance. Keep message delivery `none`. Commit with `fix(capabilities): bind bounded writes to evidence and scope`.

### Task 3: Implement action-preview and approval/audit UX

**Files:**
- Modify: `frontend/lib/data/models/approval_model.dart`
- Modify: `frontend/lib/modules/approvals/services/approvals_service.dart`
- Create: `frontend/lib/modules/approvals/views/widgets/action_preview_card.dart`
- Modify: `frontend/lib/modules/approvals/views/widgets/approval_ticket_card.dart`
- Modify: `frontend/lib/modules/skills/views/widgets/skill_detail_sidebar.dart`
- Test: `frontend/test/action_preview_card_test.dart`
- Test: `frontend/test/approvals_service_test.dart`

**Interfaces:**
- Produces a preview showing target, action class, selected skill/version/hash, evidence refs, idempotency key, rollback/compensation and approval/expiry state.

- [ ] **Step 1: Write UI tests**

Assert an `X` preview displays recipient/claim/rate limit, an `M` preview has no approve-to-execute path, an expired approval cannot be approved, and an unknown skill hash displays a blocked state. No widget may send raw payload directly to a connector.

- [ ] **Step 2: Implement, run and commit**

    cd frontend && flutter analyze && flutter test test/action_preview_card_test.dart test/approvals_service_test.dart

Use the existing approval API; do not add a frontend-only authorization path. Commit with `feat(approvals): display bounded action evidence`.

### Task 4: Publish eight P5 marketing/growth skillpacks as proposal-first

**Files:**
- Create: `skillpacks/marketing/{gtm-funnel,content-strategy,copywriting,landing-cro,paid-experiments,brand-narrative,reputation-monitoring}/{manifest.yaml,SKILL.md}`
- Create: `skillpacks/growth/ab-testing/{manifest.yaml,SKILL.md}`
- Create: `tests/agent/skills/eval/test_tranche_c_marketing_evals.py`
- Modify: `docs/integrations/skill-source-attribution.md`

**Interfaces:**
- Produces exactly eight P5 IDs. Each defaults to R/A output; `landing-cro`, `paid-experiments`, `reputation-monitoring` and `ab-testing` name an optional B/X capability and must choose artifact fallback when it is disabled.

- [ ] **Step 1: Write evals**

Cover unsourced claims, unapproved brand voice, launch-ad request, bulk posting, crisis response, PII targeting, no consent, no metric contract and prompt-injection in social content. Expected outputs are a claim-bound draft, experiment proposal or human escalation.

- [ ] **Step 2: Implement, validate and commit**

    .venv/bin/python -m pytest tests/agent/skills/eval/test_tranche_c_marketing_evals.py -q

Use P5/G5 applicability, source attribution and evidence freshness. `paid-experiments` never selects/changes a budget; `reputation-monitoring` never responds publicly. Validate skillpacks and commit with `feat(skills): add governed P5 marketing packs`.

### Task 5: Publish six P5 sales, finance and customer-success skillpacks

**Files:**
- Create: `skillpacks/sales/{lead-lifecycle,enablement,pipeline-analysis}/{manifest.yaml,SKILL.md}`
- Create: `skillpacks/finance/unit-economics/{manifest.yaml,SKILL.md}`
- Create: `skillpacks/growth/referrals/{manifest.yaml,SKILL.md}`
- Create: `skillpacks/customer_success/lifecycle/{manifest.yaml,SKILL.md}`
- Create: `tests/agent/skills/eval/test_tranche_c_revenue_evals.py`

**Interfaces:**
- Produces six P5 IDs. CRM/finance/customer updates are optional B capabilities with strict target enablements; offers, contracts, payouts and outreach remain human-owned.

- [ ] **Step 1: Write and run negative evals**

Test cross-tenant lead, customer health bias, fabricated CAC/LTV, referral reward/payment, renewal price change and a request to email a sequence. Then run:

    .venv/bin/python -m pytest tests/agent/skills/eval/test_tranche_c_revenue_evals.py -q

- [ ] **Step 2: Implement, validate and commit**

Require reviewed CRM/payment/telemetry source references and the published metric contracts. `lead-lifecycle` outputs qualification/SLA handoff; `unit-economics` labels uncertain inputs; `customer_success.lifecycle` produces a playbook/approved task proposal. Commit with `feat(skills): add governed P5 revenue packs`.

### Task 6: Publish nine P6 scale/governance skillpacks with human boundaries

**Files:**
- Create: `skillpacks/operations/{sop-builder,automation-design}/{manifest.yaml,SKILL.md}`
- Create: `skillpacks/growth/{channel-expansion,expansion-revenue}/{manifest.yaml,SKILL.md}`
- Create: `skillpacks/strategy/{segment-expansion,geo-expansion,partnerships}/{manifest.yaml,SKILL.md}`
- Create: `skillpacks/people/{hiring-copilot,culture-operating-principles}/{manifest.yaml,SKILL.md}`
- Create: `tests/agent/skills/eval/test_tranche_c_scale_evals.py`

**Interfaces:**
- Produces all nine P6 IDs. SOP/automation remains a controlled internal proposal; geographic expansion, partnerships and people decisions always end in named human ownership.

- [ ] **Step 1: Write safety evals**

Cover auto-hiring, contract signature, cross-border legal assertion, automation with no rollback, channel expansion without G5/maturity evidence and upsell to a churn-risk customer. Expected results contain assumptions/risk/approval owners and no mutation.

- [ ] **Step 2: Implement, validate and commit**

    .venv/bin/python -m pytest tests/agent/skills/eval/test_tranche_c_scale_evals.py -q

`operations.automation-design` requires process owner, exception path, rollback and enablement reference. `geo-expansion` and `partnerships` use L1/H; `hiring-copilot` must not rank people using protected traits. Validate packs, attribution and commit with `feat(skills): add P6 scale and governance packs`.

### Task 7: Introduce per-workflow readiness tests before a B/X/D action is enabled

**Files:**
- Create: `tests/apps/cosa/test_growth_scale_capability_readiness.py`
- Create: `tests/agent/evals/test_growth_scale_holdouts.py`
- Modify: `.github/workflows/quality.yml`
- Modify: `docs/architecture/plans/2026-08-30-cosa-lifecycle-skill-operating-model.md`

**Interfaces:**
- Produces one named readiness record per enabled action, containing target, policy, connector ownership, limit, exact skill hash, positive/negative holdout score, approver, rollback test and expiry.

- [ ] **Step 1: Write a representative action matrix test**

For an internal task draft (B), artifact write (A), campaign preview (X blocked), ad spend (M blocked) and sandbox test (D blocked): assert only the first two can execute with valid records. For any enabled B/X/D action, assert revoked/expired enablement, wrong hash, wrong workspace, replay, failed handler and rollback all have deterministic results/audit.

- [ ] **Step 2: Implement CI gate and commit**

    .venv/bin/python -m pytest tests/apps/cosa/test_growth_scale_capability_readiness.py tests/agent/evals/test_growth_scale_holdouts.py tests/agent/capabilities/test_enablements.py -q
    .venv/bin/python scripts/validate_skillpacks.py

Add these commands to CI. Do not mark an action enabled merely because its skill eval passes. Commit with `test(capabilities): gate growth and scale execution`.

### Task 8: Publish/pin the 95-skill catalog and prove it fails safely

**Files:**
- Modify: `apps/cosa/agents/specs.py`
- Create: `tests/apps/cosa/test_lifecycle_tranche_c_acceptance.py`
- Create: `frontend/test/lifecycle_tranche_c_flow_test.dart`
- Modify: `docs/architecture/plans/2026-08-30-cosa-lifecycle-skill-operating-model.md`

- [ ] **Step 1: Write full-catalog acceptance**

Assert all 95 immutable hashes resolve. For each P5/P6 pack, run an out-of-stage/missing-evidence/cross-workspace/side-effect request. Assert a pack with a missing capability returns the declared artifact fallback. Assert every enabled bounded action appears with preview/approval/audit and no money, contract, public send, stage or employment decision executes.

- [ ] **Step 2: Pin conservatively, verify, and commit**

Pin L0/L1 skills freely only after registry acceptance. Pin L2-B skills one capability/target at a time using enablement records. Add the Python/Flutter acceptance to CI; record the catalog inventory, pin matrix, enabled-action matrix, reviewer and expiry dates in the architecture spec. Commit with `test(lifecycle): gate P5 P6 governed catalog`.

## Definition of Done

- [ ] All 95 skillpacks pass contract, attribution and stage/policy/tenant/prompt-injection evals.
- [ ] A declared capability is insufficient without a durable, exact enablement; missing/expired scope fails closed.
- [ ] The first enabled B action has idempotency, audit, preview, approval and tested compensation; M remains human-owned.
- [ ] Every P5/P6 pack has artifact fallback and no automatic G5/G6 or lifecycle mutation exists.
- [ ] Cross-plane full-catalog acceptance and action-matrix tests are green.

## Self-review

**Spec coverage:** Implements Tranche C’s P5/P6 catalog and the operating model’s requirement that action capability is independently verified from skill publication. It operationalizes G5/G6 as human decisions supported by evidence, not agent triggers.

**Intentional exclusions:** Public send, spending, contract signature, people decisions and production security/deploy execution require a subsequent, separately approved target-specific implementation plan even if a skill references that domain.

**Type consistency:** `CapabilityEnablement` binds a `SkillSpec.definition_hash`, not a mutable name/version alone. An action class is evaluated at the gateway, not inferred from the agent role or UI.
