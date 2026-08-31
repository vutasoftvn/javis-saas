# Full MVP Marketing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Marketing cockpit's unbacked `/marketing/*` surface with durable Company Commercial contracts for context, objectives, campaigns, experiments, assets, learnings, decisions and source-proven metrics.

**Architecture:** Company Commercial owns user-created marketing records and observed metric imports. Existing marketing context, campaign, asset, form, customer and sales records are retained and exposed through a consolidated `/commercial/marketing/*` API. New experiment/learning/metric/attribution/decision tables have one owner and explicit source metadata. AI may create only labelled draft proposals based on supplied evidence; it cannot manufacture observations, publish assets or turn suggestions into approved marketing state.

**Tech Stack:** TypeScript/Encore, Drizzle/PostgreSQL, Control Plane connector status contracts, Flutter/Dart/GetX, Vitest, Flutter test and real-service E2E.

**Spec:** `docs/superpowers/specs/2026-08-31-full-mvp-contract-first-truth-only-design.md`

## Global Constraints

- Complete the Foundation plan before enabling Marketing capabilities; all enabled client calls use generated `MvpEndpoint` metadata and `ApiResult`.
- Company Commercial is the writable owner of campaigns, assets, objectives, experiments, learnings, metric observations, attributions and decisions. It links Strategy/Vault/Agent records by ID/reference; it does not duplicate their content.
- A campaign budget, metric baseline/current value, conversion count or attribution is `null`/unmeasured until user input or an authorized provider observation exists. Do not default it to `0`.
- Imported metrics require provider key, source record ID, observed timestamp, ingestion timestamp and immutable payload hash. A missing/expired connector is `not_connected`, never a successful zero-valued metric.
- Model-generated content is `MODEL_DRAFT`, carries input/source refs and requires human review before it affects a campaign/context. No model response is presented as customer research, evidence or an observed KPI.
- All request workspace access and referenced project/campaign/contact IDs are checked server-side. Connector secrets stay in Control Plane and never appear in Commercial or Flutter payloads.
- Migration number `16_mvp_marketing_contracts` is reserved for Commercial; preserve current migrations 1–15 unchanged.

---

## File map

| File | Responsibility |
|---|---|
| `services/company/commercial/migrations/16_mvp_marketing_contracts.up.sql` | Marketing objective/experiment/learning/observation/attribution/decision/proposal tables plus current schema corrections |
| `services/company/commercial/migrations/16_mvp_marketing_contracts.down.sql` | Safe reversal of new Commercial structures |
| `services/company/shared/db/schema/commercial.ts` | Drizzle models for new Marketing records and nullable observed values |
| `services/company/commercial/services/marketing-mvp.service.ts` | Workspace-scoped CRUD, metric provenance and proposal transitions |
| `services/company/commercial/services/marketing-metric-import.service.ts` | Service-authenticated connector metric intake/idempotency |
| `services/company/commercial/handlers/marketing-mvp.handler.ts` | Human `/commercial/marketing/*` routes |
| `services/company/commercial/handlers/marketing-metric-import.handler.ts` | Internal provider ingestion route |
| `services/company/commercial/handlers/index.ts` | Handler exports |
| `services/company/commercial/tests/marketing-mvp.test.ts` | Commercial database/auth/provenance tests |
| `services/company/commercial/tests/marketing-metric-import.test.ts` | Metric dedupe/missing-connector/error tests |
| `frontend/lib/modules/marketing/models/marketing_mvp_models.dart` | Typed Marketing DTOs, metric state and proposal labels |
| `frontend/lib/modules/marketing/services/marketing_mvp_service.dart` | Typed canonical Marketing client |
| `frontend/lib/modules/marketing/services/marketing_service.dart` | Shrinks to a compatibility delegate; legacy raw routes removed after migration |
| `frontend/lib/modules/marketing/controllers/marketing_controller.dart` | Result-aware cockpit state |
| `frontend/lib/modules/marketing/views/**/*.dart` | Truthful content/context/experiment/metric/approval states |
| `frontend/test/marketing_mvp_service_test.dart` | Client error/empty/provenance tests |
| `frontend/test/marketing_mvp_views_test.dart` | Cockpit metric/draft/connector UI tests |

## Task 1: Add durable Marketing records and source provenance

**Files:**

- Create: `services/company/commercial/migrations/16_mvp_marketing_contracts.up.sql`
- Create: `services/company/commercial/migrations/16_mvp_marketing_contracts.down.sql`
- Modify: `services/company/shared/db/schema/commercial.ts`
- Test: `services/company/commercial/tests/marketing-mvp.test.ts`

**Interfaces:**

- Produces `MarketingObjective`, `MarketingExperiment`, `MarketingLearning`, `MarketingMetricObservation`, `MarketingAttribution`, `MarketingDecision`, and `MarketingProposal` repository types.
- Later services accept IDs as strings, resolve tenant scope first, and return Foundation `MvpSuccess` envelopes.

- [ ] **Step 1: Write database/auth/provenance tests.**

  ```ts
  it("does not turn an unmeasured KPI into zero", async () => {
    const metric = await createMetricDefinition(ctxA, { name: "qualified_leads", unit: "count" });
    expect(metric.latestObservation).toBeNull();
    expect(metric.measurementState).toBe("NOT_MEASURED");
  });

  it("stores provider provenance and rejects a duplicate provider event", async () => {
    await ingestObservation({ workspaceId: wsA, providerKey: "google-ads", sourceRecordId: "evt-1", payloadHash: "abc", observedAt: NOW, value: 12 });
    await expect(ingestObservation({ workspaceId: wsA, providerKey: "google-ads", sourceRecordId: "evt-1", payloadHash: "abc", observedAt: NOW, value: 12 })).rejects.toMatchObject({ code: "23505" });
  });

  it("rejects a campaign reference from another workspace", async () => {
    await expect(createExperiment(ctxB, { campaignId: campaignA.id, hypothesis: "user supplied" })).rejects.toMatchObject({ code: "not_found" });
  });
  ```

- [ ] **Step 2: Run focused tests and verify they fail before migration 16.**

  Run: `cd services/company && npx vitest run commercial/tests/marketing-mvp.test.ts`

  Expected: FAIL with missing tables/types.

- [ ] **Step 3: Add schema with exact source and lifecycle constraints.**

  Add `commercial.marketing_objectives`, `marketing_experiments`, `marketing_learnings`, `marketing_metric_definitions`, `marketing_metric_observations`, `marketing_attributions`, `marketing_decisions`, and `marketing_proposals`. Every table has `id BIGINT`, `workspace_id BIGINT`, timestamps and a workspace-leading index. Observation rows require:

  ```sql
  provider_key TEXT NOT NULL,
  source_record_id TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL,
  ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  value DOUBLE PRECISION NOT NULL,
  UNIQUE (workspace_id, provider_key, source_record_id, payload_hash)
  ```

  `marketing_proposals` requires `origin IN ('USER','MODEL_DRAFT')`, `status IN ('DRAFT','IN_REVIEW','APPROVED','REJECTED')` and non-empty `source_refs` for `MODEL_DRAFT`. Alter `commercial.marketing_campaigns.budget` to nullable with no implicit default; a missing budget is an unmeasured planned-spend value, not zero. Do not backfill existing null values with invented numbers.

- [ ] **Step 4: Add down migration and rehearse apply/rollback.**

  Run:

  ```bash
  cd services/company && WORKSPACE_MIGRATOR_DATABASE_URL="$WORKSPACE_MIGRATOR_DATABASE_URL" node scripts/migrate.mjs
  cd services/company && WORKSPACE_MIGRATOR_DATABASE_URL="$WORKSPACE_MIGRATOR_DATABASE_URL" node scripts/migrate.mjs --down 1
  cd services/company && WORKSPACE_MIGRATOR_DATABASE_URL="$WORKSPACE_MIGRATOR_DATABASE_URL" node scripts/migrate.mjs
  ```

  Expected: apply, rollback and reapply work on an isolated database without modifying pre-existing campaign/context rows.

- [ ] **Step 5: Re-run tests and commit persistence.**

  Run: `cd services/company && npx vitest run commercial/tests/marketing-mvp.test.ts commercial/tests/marketing-context.tenant-isolation.test.ts`

  ```bash
  git add services/company/commercial/migrations/16_mvp_marketing_contracts.* services/company/shared/db/schema/commercial.ts services/company/commercial/tests/marketing-mvp.test.ts
  git commit -m "feat: persist truthful marketing records"
  ```

## Task 2: Implement canonical Commercial APIs and provider metric ingest

**Files:**

- Create: `services/company/commercial/services/marketing-mvp.service.ts`
- Create: `services/company/commercial/services/marketing-metric-import.service.ts`
- Create: `services/company/commercial/handlers/marketing-mvp.handler.ts`
- Create: `services/company/commercial/handlers/marketing-metric-import.handler.ts`
- Modify: `services/company/commercial/handlers/index.ts`
- Test: `services/company/commercial/tests/marketing-mvp.test.ts`
- Test: `services/company/commercial/tests/marketing-metric-import.test.ts`

**Interfaces:**

- Produces the canonical human route family below and an internal service-authenticated metric intake route.
- Existing `marketing-context` handler is retained but wrapped/migrated to the Foundation success envelope and becomes a member of the same manifest surface.

- [ ] **Step 1: Write failing contract tests for empty/error/model-draft behavior.**

  ```ts
  it("returns not_connected instead of a fake provider metric", async () => {
    await expect(listMetricObservations(ctx, { providerKey: "google-ads" })).rejects.toMatchObject({ code: "not_connected" });
  });

  it("keeps a model proposal as draft until a human approves it", async () => {
    const proposal = await createProposal(ctx, { origin: "MODEL_DRAFT", sourceRefs: ["evidence:123"], body: { headline: "draft" } });
    expect(proposal.status).toBe("DRAFT");
    expect(await listPublishedCampaignAssets(ctx)).not.toContainEqual(expect.objectContaining({ id: proposal.id }));
  });
  ```

- [ ] **Step 2: Run focused tests and verify missing service/handlers fail.**

  Run: `cd services/company && npx vitest run commercial/tests/marketing-mvp.test.ts commercial/tests/marketing-metric-import.test.ts`

  Expected: FAIL before the new service modules exist.

- [ ] **Step 3: Implement exact human route families.**

  Expose and declare in the manifest:

  ```text
  GET|PATCH                                  /commercial/marketing-context
  GET|POST                                   /commercial/marketing/objectives
  PATCH|DELETE                               /commercial/marketing/objectives/:id
  GET|POST                                   /commercial/marketing/campaigns
  GET|PATCH|DELETE                           /commercial/marketing/campaigns/:id
  GET|POST                                   /commercial/marketing/campaigns/:id/assets
  PATCH                                      /commercial/marketing/assets/:id
  GET|POST                                   /commercial/marketing/experiments
  POST                                       /commercial/marketing/experiments/:id/complete
  POST                                       /commercial/marketing/experiments/:id/decide
  GET|POST                                   /commercial/marketing/learnings
  GET                                        /commercial/marketing/metrics
  GET                                        /commercial/marketing/metrics/:id/history
  GET                                        /commercial/marketing/attributions
  GET|POST|PATCH|DELETE                      /commercial/marketing/decisions
  GET|POST                                   /commercial/marketing/proposals
  POST                                       /commercial/marketing/proposals/:id/submit-review
  POST                                       /commercial/marketing/proposals/:id/approve
  POST                                       /commercial/marketing/proposals/:id/reject
  ```

  Each route calls `requireWorkspaceAccess`, checks cross-resource workspace membership and returns `MvpSuccess`. Context creates no default content: its absence is a genuine `empty` response. `POST proposals` with `MODEL_DRAFT` requires non-empty source refs and returns only a draft. The approve handler creates/updates an explicitly selected target record in the same transaction and writes review actor/time; it does not execute connector publishing or spend.

- [ ] **Step 4: Implement service-only metric intake.**

  `POST /commercial/internal/marketing/metric-observations` accepts a signed service identity, not browser credentials. It validates provider grant/status via the Control Plane contract before storing a value; unavailable/expired/missing grant returns typed `not_connected`/`unavailable` and writes no observation. Use the observation uniqueness key for retries. Human manual observations use a separate route/body with `provider_key: "manual"`, explicit value and actor audit; this is still real supplied data, not a fallback.

- [ ] **Step 5: Run Commercial tests.**

  Run:

  ```bash
  cd services/company && npx vitest run commercial/tests/marketing-mvp.test.ts commercial/tests/marketing-metric-import.test.ts commercial/tests/marketing-context.contract.test.ts commercial/tests/marketing-context.tenant-isolation.test.ts
  ```

  Expected: PASS for ownership, empty context, provider-not-connected, metric dedupe and draft-only model output.

- [ ] **Step 6: Commit canonical Marketing API.**

  ```bash
  git add services/company/commercial/services/marketing-mvp.service.ts services/company/commercial/services/marketing-metric-import.service.ts services/company/commercial/handlers/marketing-mvp.handler.ts services/company/commercial/handlers/marketing-metric-import.handler.ts services/company/commercial/handlers/index.ts services/company/commercial/tests
  git commit -m "feat: add canonical marketing contracts"
  ```

## Task 3: Migrate Marketing Flutter client, controller and cockpit states

**Files:**

- Create: `frontend/lib/modules/marketing/models/marketing_mvp_models.dart`
- Create: `frontend/lib/modules/marketing/services/marketing_mvp_service.dart`
- Modify: `frontend/lib/modules/marketing/services/marketing_service.dart`
- Modify: `frontend/lib/modules/marketing/controllers/marketing_controller.dart`
- Modify: `frontend/lib/modules/marketing/views/marketing_cockpit_view.dart`
- Modify: `frontend/lib/modules/marketing/views/tabs/marketing_node1_objectives_tab.dart`
- Modify: `frontend/lib/modules/marketing/views/tabs/marketing_node3_content_tab.dart`
- Modify: `frontend/lib/modules/marketing/views/tabs/marketing_node4_approvals_tab.dart`
- Modify: `frontend/lib/modules/marketing/views/tabs/marketing_node5_funnel_tab.dart`
- Modify: `frontend/lib/modules/marketing/views/tabs/marketing_node6_learning_tab.dart`
- Modify: `frontend/lib/modules/marketing/views/widgets/marketing_kpi_header.dart`
- Test: `frontend/test/marketing_mvp_service_test.dart`
- Test: `frontend/test/marketing_mvp_views_test.dart`

**Interfaces:**

- Consumes canonical `/commercial/marketing/*`, `/commercial/marketing-context/*`, Workforce approval IDs, and Settings connector status only through manifest endpoints.
- Produces typed `ApiResult` state per cockpit tab; no tab uses a raw `Map` empty fallback to represent a failure.

- [ ] **Step 1: Write failure/not-connected/draft widget tests.**

  ```dart
  testWidgets('missing Google Ads grant is not rendered as zero conversions', (tester) async {
    await tester.pumpWidget(MarketingCockpit.withMetricFailure(ApiFailureCode.notConnected));
    expect(find.text('Kết nối nguồn đo lường'), findsOneWidget);
    expect(find.text('0 conversions'), findsNothing);
  });

  testWidgets('model proposal is labelled draft and cannot appear as published content', (tester) async {
    await tester.pumpWidget(MarketingCockpit.withProposal(origin: ProposalOrigin.modelDraft, status: ProposalStatus.draft));
    expect(find.text('Bản nháp từ mô hình — cần duyệt'), findsOneWidget);
    expect(find.text('Đã xuất bản'), findsNothing);
  });
  ```

- [ ] **Step 2: Run tests and observe legacy client failure.**

  Run: `cd frontend && flutter test test/marketing_mvp_service_test.dart test/marketing_mvp_views_test.dart`

  Expected: FAIL while `marketing_service.dart` calls `/marketing/*`, transforms response shapes ad hoc, or returns `{}`/`[]` after a failed response.

- [ ] **Step 3: Implement typed client cutover.**

  Move endpoint calls into `MarketingMvpService`, one method per manifest capability. Migrate context without the current snake/camel duplication shim; models use the actual canonical schema. Replace raw map mutation and `_decode/_map/_list` empty recovery with `ApiResult`. Remove fallback projects list, `/marketing/*` direct calls, browser-supplied `requested_by_agent: 'Marketing Director'`, and all model action routes that claim a proposal is actual campaign state.

- [ ] **Step 4: Render attribution/provenance and action boundaries.**

  KPI cards show `measurementState`, provider/manual source, observed time and last ingestion time. Context/campaign/experiment empty states offer a user creation action with no example record. Approval tab reads the real Workforce approval list; publish/spend controls remain disabled until the owner policy/approval returns success. A provider error offers connector setup/retry, not fake metrics.

- [ ] **Step 5: Run Flutter verification and enable entries.**

  Run:

  ```bash
  cd frontend && flutter test test/marketing_mvp_service_test.dart test/marketing_mvp_views_test.dart
  cd frontend && flutter analyze
  node ../scripts/gen-mvp-contracts.mjs
  ```

  Expected: PASS; enable only completed Marketing IDs and update the acceptance ledger.

- [ ] **Step 6: Commit Flutter Marketing cutover.**

  ```bash
  git add frontend/lib/modules/marketing frontend/test/marketing_mvp_service_test.dart frontend/test/marketing_mvp_views_test.dart shared/contracts/mvp-surface.json frontend/lib/core/network/mvp_endpoints.g.dart docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "feat: wire truthful marketing cockpit"
  ```

## Task 4: Prove Marketing source truth with a real Company/connector scenario

**Files:**

- Create: `tests/e2e/test_mvp_marketing_http.py`
- Modify: `tests/e2e/conftest.py`
- Modify: `docs/architecture/generated/route-inventory.allowlist.json`
- Modify: `docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md`

**Interfaces:**

- Consumes real Company service/database, platform connector status and two authenticated workspaces.
- Produces verification for Marketing persistence, draft/review, metric provenance and tenant isolation.

- [ ] **Step 1: Write the real-service test.**

  ```python
  def test_campaign_and_metric_keep_real_provenance(real_mvp_stack, workspace_a, workspace_b):
      campaign = real_mvp_stack.company.create_campaign(workspace_a, {"name": "Founder supplied launch", "budget": None})
      assert campaign["data"]["budget"] is None
      draft = real_mvp_stack.company.create_marketing_proposal(workspace_a, {"origin": "MODEL_DRAFT", "sourceRefs": ["vault:doc-1"], "body": {"headline": "draft"}})
      assert draft["data"]["status"] == "DRAFT"
      missing = real_mvp_stack.company.list_metrics(workspace_a, provider_key="google-ads")
      assert missing.status_code in {424, 503}
      assert real_mvp_stack.company.get_campaign(workspace_b, campaign["data"]["id"]).status_code in {403, 404}
  ```

- [ ] **Step 2: Run the test against real services.**

  Run: `PYTHONPATH=$(pwd) python3 -m pytest tests/e2e/test_mvp_marketing_http.py -q`

  Expected: PASS with actual Company/Control Plane processes, or explicit missing-prerequisite SKIP. It may not create a fake connector or mocked metric response.

- [ ] **Step 3: Add a genuine provider-ingest case.**

  In an authorized test connector environment, create a real connector grant/status, POST a signed provider observation through the internal route, assert the exact source/timestamps appear, retry the same event and assert one row. If no authorized connector environment exists, leave that integration evidence pending; do not relabel a manual fixture as provider data.

- [ ] **Step 4: Run contract gates and remove matching ghosts.**

  Run:

  ```bash
  make mvp-surface-check
  make contract-freeze-check
  PYTHONPATH=$(pwd) python3 -m pytest tests/e2e/test_mvp_marketing_http.py -q
  ```

  Remove only `/marketing/*` allowlist entries whose Flutter calls have been replaced and whose routes are canonical in inventory.

- [ ] **Step 5: Commit integration evidence.**

  ```bash
  git add tests/e2e docs/architecture/generated docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "test: verify marketing mvp flow"
  ```

## Completion gate

Run:

```bash
cd services/company && npx vitest run commercial/tests/marketing-mvp.test.ts commercial/tests/marketing-metric-import.test.ts commercial/tests/marketing-context.tenant-isolation.test.ts
cd frontend && flutter test test/marketing_mvp_service_test.dart test/marketing_mvp_views_test.dart
make mvp-surface-check
git diff --check
```

Marketing is not complete if it displays a zero for an unmeasured metric, calls `/marketing/*` directly, treats a provider outage as empty success, lets a model draft become published state, or exposes connector secret material to Flutter.
