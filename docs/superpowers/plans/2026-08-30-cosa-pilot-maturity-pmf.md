# COSA Pilot Maturity and PMF — Tranche B2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert governed pilot outcomes into versioned metric contracts, reproducible PMF/maturity scoreboards and ten P4 decision skills, without treating a survey, an agent output or a single metric as an automatic gate pass.

**Architecture:** Company Services store metric definitions, source mappings, validated snapshots and immutable scoreboard runs. Evidence ingestion remains candidate-only; the PMF evaluator reads only reviewed evidence and validated metric snapshots, returns a recommendation and never mutates lifecycle state. The Agent Plane produces analysis/decision artifacts at L0/L1, while Flutter presents calculation inputs, freshness and missing-data flags to human owners.

**Tech Stack:** TypeScript/Encore/Drizzle/PostgreSQL, Python/FastAPI/Pydantic/Pytest, Flutter/Dart.

**Spec:** `docs/architecture/plans/2026-08-30-cosa-lifecycle-skill-operating-model.md`

## Entry gate and scope

Start only when Tranche B1 has passed and at least one human-authorized pilot has a defined cohort, complete instrumentation artifact, reviewed pilot outcome/feedback evidence and a named metric owner. The team selects model-appropriate thresholds in its workspace policy; this plan must not hard-code “40% Sean Ellis” or any universal retention, revenue, sample-size or score threshold.

This plan publishes the ten P4 skillpacks and takes the catalog from **62 to 72**. It adds no paid campaign execution, outbound sending, pricing update, revenue write, automatic pivot, G4 pass, G5 pass or project-stage mutation.

## Global constraints

- A metric contract is versioned, scoped to one workspace/project and has an owner, source mapping, unit, denominator, cadence, freshness, guardrail and decision use.
- A source snapshot is idempotent by `(workspace, contract, source system, source record/window, payload hash)` and carries observed/captured time plus data-quality result.
- A PMF scoreboard is a reproducible calculation run referencing exact contract versions, snapshot IDs and reviewed evidence IDs; its result is `INSUFFICIENT_DATA`, `MIXED`, `PROMISING` or `CONCERNING`, not `passed`.
- The evaluator and every P4 skill label facts/inferences/assumptions, expose missing/biased data and create `ACTION`, `DECISION` or `LEARN` proposals only.
- No metric endpoint accepts a lifecycle stage, `humanOverride`, external credential or source URL to fetch at runtime.

## File map

| Path | Responsibility |
| --- | --- |
| `services/company/shared/db/schema/strategy.ts` | Metric contracts, snapshots, scoreboards and maturity assessments. |
| `services/company/operations/strategy/services/{metric-contract,pmf-scoreboard,maturity-assessment}.service.ts` | Deterministic validation/calculation and advisory state. |
| `services/company/operations/strategy/handlers/{metric-contract,metric-snapshot,pmf-scoreboard,maturity-assessment}.handler.ts` | Company API with workspace/role boundaries. |
| `apps/cosa/capabilities/project_lifecycle.py` | Read/propose-only metric/scoreboard capabilities. |
| `skillpacks/{analytics,discovery,strategy,product,growth,customer_success}/*` | P4 manifests, SKILL contracts and evals. |
| `frontend/lib/modules/strategy/*` | Read-only PMF/Maturity scoreboard and decision proposals. |

---

### Task 1: Add versioned metric contracts with explicit decision semantics

**Files:**
- Create: `services/company/operations/migrations/30_metric_contracts.up.sql`
- Create: `services/company/operations/migrations/30_metric_contracts.down.sql`
- Modify: `services/company/shared/db/schema/strategy.ts`
- Create: `services/company/operations/strategy/services/metric-contract.service.ts`
- Create: `services/company/operations/strategy/handlers/metric-contract.handler.ts`
- Modify: `services/company/operations/strategy/handlers/index.ts`
- Test: `services/company/operations/strategy/tests/metric-contract.test.ts`

**Interfaces:**
- Produces `MetricContract` with `id`, `version`, `metricKey`, `displayName`, `unit`, `numeratorDefinition`, `denominatorDefinition`, `cohortDefinition`, `sourceMapping`, `cadence`, `freshUntil`, `guardrail`, `ownerMemberId`, `decisionUse` and `status`.
- APIs: create/list/get/patch draft contracts; `POST /operations/strategy/metric-contracts/:id/publish` requires a privileged human and creates a new immutable version.

- [ ] **Step 1: Write failing versioning tests**

    const v1 = await createMetricContractAsFounder({ metricKey: 'activation_rate', ...validContract });
    await publishContractAsFounder(v1.id, 'APR-METRIC-1');
    await expect(patchContractAsMember(v1.id, { unit: 'USD' })).rejects.toThrow(/immutable|founder/i);
    const v2 = await reviseContractAsFounder(v1.id, { cohortDefinition: 'paid accounts' });
    expect(v2.version).toBe(2);
    expect(v1.version).toBe(1);

Assert a workspace B request cannot resolve the contract, an empty denominator or no owner fails, and metric contract publication does not emit a gate/stage event.

- [ ] **Step 2: Run the focused tests**

    cd services/company && pnpm exec vitest run operations/strategy/tests/metric-contract.test.ts --no-file-parallelism

- [ ] **Step 3: Implement the contract aggregate**

Use a stable logical contract ID plus immutable version rows. The active version can be changed only by a founder/co-founder/admin using a non-empty approval reference. Enforce unique `(workspace_id, project_id, metric_key, version)` and source mapping shape `{ system, identifier, aggregation, window }`; reject credentials, raw SQL and unbounded free-form queries. Record human actor, approval reference and change rationale.

- [ ] **Step 4: Verify and commit**

    cd services/company && pnpm typecheck && pnpm exec vitest run operations/strategy/tests/metric-contract.test.ts operations/tests/project-stage-lifecycle.test.ts --no-file-parallelism
    git add services/company/operations/migrations/30_metric_contracts.up.sql services/company/operations/migrations/30_metric_contracts.down.sql services/company/shared/db/schema/strategy.ts services/company/operations/strategy/services/metric-contract.service.ts services/company/operations/strategy/handlers/metric-contract.handler.ts services/company/operations/strategy/handlers/index.ts services/company/operations/strategy/tests/metric-contract.test.ts
    git commit -m "feat(metrics): add versioned metric contracts"

### Task 2: Ingest validated metric snapshots without trusting an agent calculation

**Files:**
- Create: `services/company/operations/migrations/31_metric_snapshots.up.sql`
- Create: `services/company/operations/migrations/31_metric_snapshots.down.sql`
- Modify: `services/company/shared/db/schema/strategy.ts`
- Create: `services/company/operations/strategy/services/metric-snapshot.service.ts`
- Create: `services/company/operations/strategy/handlers/metric-snapshot.handler.ts`
- Test: `services/company/operations/strategy/tests/metric-snapshot.test.ts`

**Interfaces:**
- Produces `POST /operations/strategy/metric-snapshots` accepting `{ contractVersionId, sourceSystem, sourceWindow, sourceRecordId, payloadHash, observedAt, value, numerator?, denominator?, qualityChecks, evidenceIngestionId? }`.
- Produces `VALID`, `STALE`, `INCOMPLETE` or `REJECTED` snapshot quality. Only authenticated normalized source adapters may call the write route; Agent capabilities get read/propose-only routes.

- [ ] **Step 1: Write failing validation tests**

    const snapshot = await ingestSnapshot(validTelemetrySnapshot);
    expect(snapshot.qualityStatus).toBe('VALID');
    expect((await ingestSnapshot(validTelemetrySnapshot)).id).toBe(snapshot.id);
    await expect(ingestSnapshot({ ...validTelemetrySnapshot, denominator: 0 })).rejects.toThrow(/denominator/i);
    await expect(ingestSnapshot({ ...validTelemetrySnapshot, observedAt: staleDate })).resolves.toMatchObject({ qualityStatus: 'STALE' });

Assert a run ID/agent output cannot mark a snapshot `VALID`, and a snapshot in workspace A cannot reference a B contract, B evidence receipt or B project.

- [ ] **Step 2: Run and implement**

    cd services/company && pnpm exec vitest run operations/strategy/tests/metric-snapshot.test.ts --no-file-parallelism

Create snapshot rows with immutable value/input/quality data and the idempotency unique key from Global Constraints. Recalculate expected numerator/denominator/unit/freshness against the published contract. `qualityChecks` contains machine-verifiable outcomes (completeness, schema/identity match, duplicate window, consent classification); it is not arbitrary model prose. Store source receipt/evidence references but do not change their review status.

- [ ] **Step 3: Verify and commit**

    cd services/company && pnpm typecheck && pnpm exec vitest run operations/strategy/tests/metric-contract.test.ts operations/strategy/tests/metric-snapshot.test.ts operations/strategy/tests/evidence-ingestion.test.ts --no-file-parallelism
    git add services/company/operations/migrations/31_metric_snapshots.up.sql services/company/operations/migrations/31_metric_snapshots.down.sql services/company/shared/db/schema/strategy.ts services/company/operations/strategy/services/metric-snapshot.service.ts services/company/operations/strategy/handlers/metric-snapshot.handler.ts services/company/operations/strategy/tests/metric-snapshot.test.ts
    git commit -m "feat(metrics): ingest validated metric snapshots"

### Task 3: Calculate a reproducible PMF scoreboard and maturity track

**Files:**
- Create: `services/company/operations/migrations/32_pmf_scoreboards.up.sql`
- Create: `services/company/operations/migrations/32_pmf_scoreboards.down.sql`
- Modify: `services/company/shared/db/schema/strategy.ts`
- Create: `services/company/operations/strategy/services/pmf-scoreboard.service.ts`
- Create: `services/company/operations/strategy/services/maturity-assessment.service.ts`
- Create: `services/company/operations/strategy/handlers/pmf-scoreboard.handler.ts`
- Create: `services/company/operations/strategy/handlers/maturity-assessment.handler.ts`
- Test: `services/company/operations/strategy/tests/pmf-scoreboard.test.ts`

**Interfaces:**
- Produces `calculatePmfScoreboard(projectId, contractVersionIds, snapshotIds, reviewedEvidenceIds, policyVersion)` and an immutable `PmfScoreboardRun`.
- Produces maturity dimensions `measurement`, `value`, `retention`, `commercial`, `operational` with per-dimension `NOT_ASSESSED|EARLY|REPEATABLE|GOVERNED`, rationale and missing evidence.

- [ ] **Step 1: Write calculation and negative tests**

    const run = await calculate(validInputs);
    expect(run.result).toBe('PROMISING');
    expect(run.inputSnapshotIds).toEqual(validInputs.snapshotIds);
    expect(run.gateRecommendation).toBeUndefined();
    expect((await calculate({ ...validInputs, snapshotIds: [] })).result).toBe('INSUFFICIENT_DATA');

Use fixture policies where the same score changes only because the workspace-approved dimensions/weights changed. Assert a hard-coded `0.4` value is absent, a stale snapshot lowers data completeness rather than silently passing, and the service never updates project/gate tables.

- [ ] **Step 2: Run, implement, and verify**

    cd services/company && pnpm exec vitest run operations/strategy/tests/pmf-scoreboard.test.ts --no-file-parallelism

Persist input IDs, resolved contract versions, policy version, each weighted component, missing-data/reliability flags, output classification, calculation hash and human review state. `maturity-assessment` derives only from the referenced immutable run/evidence set and returns an advisory record. Re-running the same inputs must return the same calculation hash/result.

    cd services/company && pnpm typecheck && pnpm exec vitest run operations/strategy/tests/pmf-scoreboard.test.ts operations/tests/project-stage-lifecycle.test.ts --no-file-parallelism
    git add services/company/operations/migrations/32_pmf_scoreboards.up.sql services/company/operations/migrations/32_pmf_scoreboards.down.sql services/company/shared/db/schema/strategy.ts services/company/operations/strategy/services/pmf-scoreboard.service.ts services/company/operations/strategy/services/maturity-assessment.service.ts services/company/operations/strategy/handlers/pmf-scoreboard.handler.ts services/company/operations/strategy/handlers/maturity-assessment.handler.ts services/company/operations/strategy/tests/pmf-scoreboard.test.ts
    git commit -m "feat(pmf): add reproducible scoreboards and maturity"

### Task 4: Add advisory metric and PMF capabilities, not an auto-decision capability

**Files:**
- Modify: `apps/cosa/capabilities/project_lifecycle.py`
- Modify: `apps/cosa/composition/agent_plane.py`
- Test: `tests/apps/cosa/test_pmf_capability_boundary.py`
- Test: `tests/apps/cosa/composition/test_agent_plane.py`

**Interfaces:**
- Produces `analytics.metric_contract.get`, `analytics.pmf_scoreboard.get` and `analytics.pmf_scoreboard.propose`.
- Does not produce `analytics.metric_snapshot.ingest`, `strategy.pivot.execute`, `strategy.gate.pass` or any lifecycle mutator.

- [ ] **Step 1: Write failing boundary tests**

    result = await execute('analytics.pmf_scoreboard.propose', {'project_id': projectA.id}, workspaceA)
    assert result.status == 'completed'
    assert result.output_payload['classification'] in {'INSUFFICIENT_DATA', 'MIXED', 'PROMISING', 'CONCERNING'}
    assert 'strategy.pivot.execute' not in plane.capability_registry.ids()

Test missing workspace, cross-workspace project, stale/missing metrics and a prompt requesting “declare PMF and advance the project”.

- [ ] **Step 2: Implement and verify**

The propose handler only resolves existing Company scoreboards and builds an `ACTION / DECISION / LEARN` memo with source IDs, missing inputs and human owner. It cannot calculate from model-provided numbers. Run the two test modules and commit with `feat(agent): expose advisory PMF capabilities`.

### Task 5: Publish six P4 decision packs grounded in immutable inputs

**Files:**
- Create: `skillpacks/discovery/affinity-synthesis/{manifest.yaml,SKILL.md}`
- Create: `skillpacks/strategy/pivot-persevere/{manifest.yaml,SKILL.md}`
- Create: `skillpacks/analytics/{pmf-survey,pmf-scoreboard}/{manifest.yaml,SKILL.md}`
- Create: `skillpacks/product/{outcome-roadmap,backlog-prioritization}/{manifest.yaml,SKILL.md}`
- Create: `tests/agent/skills/eval/test_tranche_b2_decision_evals.py`

**Interfaces:**
- Produces six P4 IDs with P4/G4 applicability and L0/L1 artifact/proposal outputs.

- [ ] **Step 1: Write eval cases and implement**

    .venv/bin/python -m pytest tests/agent/skills/eval/test_tranche_b2_decision_evals.py -q

Cover response/sample bias, no eligible cohort, contradictory feedback, an attempt to decide pivot automatically, fabricated retention data and a request to change project stage. `pmf-scoreboard` consumes Company run IDs only. `pivot-persevere` requires a human founder decision and outputs alternatives/risks/reversibility. Validate, attribute sources and commit with `feat(skills): add P4 PMF decision packs`.

### Task 6: Publish four P4 learning, experimentation and customer-health packs

**Files:**
- Create: `skillpacks/product/continuous-discovery/{manifest.yaml,SKILL.md}`
- Create: `skillpacks/growth/experimentation-system/{manifest.yaml,SKILL.md}`
- Create: `skillpacks/customer_success/{health-scoring,churn-analysis}/{manifest.yaml,SKILL.md}`
- Create: `tests/agent/skills/eval/test_tranche_b2_learning_evals.py`

**Interfaces:**
- Produces the remaining four P4 IDs. `growth.experimentation-system` may create an internal experiment proposal through the existing approval-bound capability, but cannot launch it.

- [ ] **Step 1: Write and run negative evals**

Test biased health labels, sensitive attribute inference, insufficient cohort history, an outbound save-offer request and an experiment request with no metric contract. Then run:

    .venv/bin/python -m pytest tests/agent/skills/eval/test_tranche_b2_learning_evals.py -q

- [ ] **Step 2: Implement, validate, and commit**

Each pack includes a source/freshness requirement and owner escalation. Health/churn outputs are explainable signals, not automatic account actions; experiments require a metric-contract ID and approval handoff. Validate with `scripts/validate_skillpacks.py`, record attribution and commit with `feat(skills): add P4 learning and health packs`.

### Task 7: Render PMF/maturity transparently in Flutter

**Files:**
- Create: `frontend/lib/data/models/pmf_scoreboard_model.dart`
- Create: `frontend/lib/modules/strategy/services/pmf_scoreboard_service.dart`
- Create: `frontend/lib/modules/strategy/views/widgets/pmf_scoreboard_panel.dart`
- Create: `frontend/lib/modules/strategy/views/widgets/maturity_track_panel.dart`
- Modify: `frontend/lib/modules/strategy/views/tabs/evidence_backbone_tab.dart`
- Test: `frontend/test/pmf_scoreboard_service_test.dart`
- Test: `frontend/test/pmf_scoreboard_panel_test.dart`

**Interfaces:**
- Produces read-only display of classification, per-dimension evidence, metric definitions/source window/freshness, calculation hash, missing data and linked human decisions.

- [ ] **Step 1: Write tests before UI**

Assert `INSUFFICIENT_DATA` shows no green pass treatment; stale data has a visible warning; each number links to contract/snapshot reference; and no widget calls the stage transition service.

- [ ] **Step 2: Implement, verify, and commit**

    cd frontend && flutter analyze && flutter test test/pmf_scoreboard_service_test.dart test/pmf_scoreboard_panel_test.dart

Do not display an aggregate “PMF percentage” without its components. Add a founder decision/action-proposal card, not an execute button. Commit with `feat(strategy): show governed PMF maturity`.

### Task 8: Release-gate the pilot-to-PMF loop

**Files:**
- Modify: `apps/cosa/agents/specs.py`
- Create: `tests/apps/cosa/test_lifecycle_tranche_b2_acceptance.py`
- Create: `services/company/operations/strategy/tests/lifecycle-tranche-b2-contract.test.ts`
- Create: `frontend/test/lifecycle_tranche_b2_flow_test.dart`
- Modify: `.github/workflows/quality.yml`
- Modify: `docs/architecture/plans/2026-08-30-cosa-lifecycle-skill-operating-model.md`

- [ ] **Step 1: Write end-to-end test**

The test creates workspace A/B, a pilot, two contract versions, valid/stale snapshots, reviewed feedback and a PMF run. It proves: only A inputs are resolved; replay is idempotent; the run is reproducible; P4 packs produce advisory artifacts; no skill passes G4, runs pivot, changes stage, sends outreach or spends money; and all 72 catalog hashes resolve.

- [ ] **Step 2: Run, pin, and commit**

Pin only read/propose P4 packs to research/product/customer-success agents. Add Company, Python and Flutter acceptance tests plus both eval modules to CI. Record the immutable 10 P4 hashes, score-policy version, reviewers and trial decision in the architecture spec; commit with `test(pmf): gate pilot maturity release`.

## Definition of Done

- [ ] Metric contracts and snapshots are tenant-scoped, versioned, idempotent and data-quality checked.
- [ ] PMF/maturity result is reproducible, transparent and advisory; no universal threshold is hard-coded.
- [ ] All 10 P4 packs pass source/eval/negative-case validation and catalog count is 72.
- [ ] The UI makes definitions, freshness and missing evidence visible without a gate/transition shortcut.
- [ ] Cross-workspace, stale-data, auto-pivot and no-side-effect acceptance tests are green.

## Self-review

**Spec coverage:** Implements Order 6 (maturity tracks, metric contracts, PMF scoreboard and bounded proposals) and all P4 catalog skills. It starts only after real pilot evidence and produces the evidence needed for a human G4 decision.

**Intentional exclusions:** repeatable GTM, campaign launch, CRM write, pricing change, money actions and P5/P6 skills are delegated to Tranche C.

**Type consistency:** `PmfScoreboardRun.result` is never a gate result. A `MetricContract` version and a `MetricSnapshot` are immutable inputs; a human `DecisionRecord` remains the business decision.
