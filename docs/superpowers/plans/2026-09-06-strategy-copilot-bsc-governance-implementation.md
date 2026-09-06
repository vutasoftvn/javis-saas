# Strategy Copilot, BSC Filter & Human Governance Implementation Plan

> **For the implementation agent:** Execute this plan task by task, commit after each task, and run the listed focused tests before moving to the next task.

**Goal:** Biến workflow chiến lược hiện có thành chuỗi có thể cấu hình theo workspace: Mục tiêu chiến lược → BSC Focus Scope → PESTEL và đánh giá nguồn lực/năng lực → SWOT → TOWS có chấm điểm và chọn lọc → OKRs → Initiatives → weekly tasks; đồng thời bảo đảm Founder hoặc thành viên được uỷ quyền là người phê duyệt mọi quyết định làm thay đổi hướng đi.

**Architecture:** BSC là phạm vi phân tích (filter), không phải một tab chạy song song với PESTEL/SWOT/TOWS và không tạo kho KPI thứ hai. `strategy.workspace_strategy_settings` quyết định cách vận hành cho toàn workspace; project/cycle chỉ được siết chặt hơn, rồi snapshot chính sách vào cycle/review. Các artefact phân tích lưu theo workspace và có lineage đến strategic objective, TOWS option, OKR, Initiative, task. Agent chỉ tạo evidence, draft, score và proposal; các transition chọn chiến lược, publish OKR, phê duyệt Initiative, đóng review đều đi qua business authorization.

**Tech Stack:** Encore TypeScript API, PostgreSQL migrations + Drizzle schema, Vitest, Flutter/GetX/Dio, existing workspace headers and business-authorization service.

**Approved design:** [Strategy Copilot BSC & Governance Design](../specs/2026-09-06-strategy-copilot-bsc-governance-design.md)

## Non-negotiable rules

- Chỉ thêm API chiến lược dưới `/operations/strategy/*`; không hiện thực các route ma `/strategy/lenses/*` mà frontend hiện đang gọi.
- Tất cả read/write phải nhận `X-Workspace-Id`, gọi `requireWorkspaceAccess`, và query/foreign key phải không cho nối dữ liệu chéo workspace.
- BSC mode `OFF` bỏ bước scope; `OPTIONAL` cho phép bỏ qua; `REQUIRED` bắt buộc có ít nhất một trong bốn góc nhìn `FINANCIAL`, `CUSTOMER`, `INTERNAL_PROCESS`, `LEARNING_AND_GROWTH` trước khi lưu phân tích hoặc tạo SWOT.
- Dùng thuật ngữ **Đánh giá nguồn lực và năng lực chiến lược**, gồm: nguồn lực tài chính; năng lực con người và tổ chức; tri thức, dữ liệu và sở hữu trí tuệ; tài sản công nghệ và vận hành; tài sản thị trường và quan hệ; năng lực quản trị, pháp lý và kiểm soát rủi ro.
- `tows_selection_limit` luôn trong `[1, 2]`; không tạo/công bố OKR từ một TOWS option chưa được chọn. Mỗi Objective được publish có tối đa ba KRs định lượng.
- Initiative là dự án/luồng công việc kéo dài nhiều tuần; task hoặc weekly commitment có thể là BAU và không cần Initiative, nhưng nếu có `initiative_id` thì phải cùng workspace với task/commitment.
- Chu kỳ thực thi sử dụng `durationWeeks` hiện hữu, không ràng buộc 12 tuần. Mid-cycle tự động nằm ở `ceil(durationWeeks / 2)` cho chu kỳ từ 4 tuần; End-cycle ở tuần cuối.
- BSC scorecard chỉ đọc published Objective/KR/metric-contract hiện có. Không thêm bảng BSC goals hoặc KPI độc lập.

## Task 1: Thiết lập quyền chiến lược và policy workspace

**Files:**
- Create: `services/company/identity/migrations/10_strategy_governance_permissions.up.sql`
- Create: `services/company/identity/migrations/10_strategy_governance_permissions.down.sql`
- Modify: `services/company/identity/services/permission-catalog.ts`
- Create: `services/company/operations/migrations/45_workspace_strategy_settings.up.sql`
- Create: `services/company/operations/migrations/45_workspace_strategy_settings.down.sql`
- Modify: `services/company/shared/db/schema/strategy.ts`
- Create: `services/company/operations/strategy/services/workspace-strategy-settings.service.ts`
- Create: `services/company/operations/strategy/services/strategy-governance-authorization.service.ts`
- Create: `services/company/operations/strategy/handlers/workspace-strategy-settings.handler.ts`
- Create: `services/company/operations/strategy/tests/workspace-strategy-settings.test.ts`

1. Seed the seven new permission definitions in migration 10 and mirror every key in `PERMISSION_CATALOG`:

   ```ts
   type StrategyGovernancePermission =
     | "strategy.framework.manage"
     | "strategy.analysis.write"
     | "strategy.option.select"
     | "strategy.okr.publish"
     | "strategy.initiative.approve"
     | "strategy.review.close"
     | "strategy.agent.configure";
   ```

   Preserve the current `strategy.read`, `strategy.write`, `strategy.target.manage`, and `strategy.transition` grants for backward compatibility. The migration is additive and the down migration removes only the seven newly seeded definitions after dependent `role_permissions` are removed by FK cascade.

2. Add `strategy.workspace_strategy_settings`, keyed by `workspace_id`, with: `strategy_method` (`CLASSIC|BSC_FILTER`), `bsc_mode` (`OFF|OPTIONAL|REQUIRED`), `enabled_bsc_perspectives jsonb`, `tows_selection_limit`, `weekly_review_enabled`, `mid_cycle_review_policy` (`OFF|AUTO|CUSTOM`), `end_cycle_review_enabled`, `allowed_agent_profiles jsonb`, `approval_policy` (`FOUNDER_ONLY|DELEGATED_APPROVER`), `revision`, `updated_by_member_id`, `updated_at`. Use database checks for enum-like values, a check on `tows_selection_limit BETWEEN 1 AND 2`, JSON defaults of `[]`, and workspace FK with cascade delete.

3. In the service expose typed defaults and normalisation. Treat a missing row as the backward-compatible default `{ strategyMethod: "CLASSIC", bscMode: "OFF", towsSelectionLimit: 1, weeklyReviewEnabled: true, midCycleReviewPolicy: "AUTO", endCycleReviewEnabled: true, approvalPolicy: "FOUNDER_ONLY" }`; do not create a row during GET. Reject duplicate perspectives, unknown agent profiles, empty perspectives in `REQUIRED`, `BSC_FILTER` combined with `OFF`, and an attempted project/cycle override that relaxes the workspace policy.

4. Implement `requireStrategyGovernanceAuthority(ctx, permission, scope, settings)`. It first resolves workspace settings, then enforces `FOUNDER_ONLY` with the same founder/co-founder rule as today; under `DELEGATED_APPROVER` it calls `requireCommandAuthority` for the named permission and scope. All terminal strategy commands in later tasks use this helper. Settings change itself is governed by the current policy, not an untrusted replacement policy supplied in the PUT payload.

5. Implement `GET /operations/strategy/settings` and `PUT /operations/strategy/settings`. Both require workspace access; PUT additionally calls `requireStrategyGovernanceAuthority(ctx, "strategy.framework.manage", { workspaceId }, currentSettings)`. Persist the actor and increment revision atomically with optimistic `expectedRevision` support. Return policy revision and a `canEdit` capability flag so the UI does not infer authority from the member role string.

6. Add pure service tests for defaults, the BSC consistency matrix, revision conflict, founder default allow, `FOUNDER_ONLY` rejection of an otherwise delegated grantee, delegated approver allow when policy permits it, and a workspace member without the grant receiving `permissionDenied`. Test a role assignment scoped to project as well as workspace, because `ResourceScope` supports both.

**Verification:**

```bash
cd services/company && pnpm test -- operations/strategy/tests/workspace-strategy-settings.test.ts identity/tests/permission-evaluator.test.ts
cd services/company && pnpm typecheck
```

**Commit:** `feat(strategy): add workspace governance settings and permissions`

## Task 2: Lưu mục tiêu chiến lược và BSC Focus Scope trước phân tích

**Files:**
- Create: `services/company/operations/migrations/46_strategy_objectives_bsc_scope.up.sql`
- Create: `services/company/operations/migrations/46_strategy_objectives_bsc_scope.down.sql`
- Modify: `services/company/shared/db/schema/strategy.ts`
- Create: `services/company/operations/strategy/services/strategic-objective.service.ts`
- Create: `services/company/operations/strategy/handlers/strategic-objective.handler.ts`
- Create: `services/company/operations/strategy/tests/strategic-objective.test.ts`

1. Add `strategy.strategic_objectives` with snowflake `id`, `workspace_id`, optional `project_id`, `title`, `success_definition`, `time_horizon_end`, `status` (`DRAFT|ACTIVE|ARCHIVED`), `owner_member_id`, actor/revision/timestamps, and composite uniqueness `(id, workspace_id)`. The success definition must describe a measurable end state; a title alone cannot become active.

2. Add `strategy.bsc_focus_scopes` with `id`, `workspace_id`, `strategic_objective_id`, `perspective`, `focus_question`, `focus_statement`, `priority`, `status`, actor/revision/timestamps. Enforce one active scope per `(strategic_objective_id, perspective)` and a composite FK `(strategic_objective_id, workspace_id)` to the new objective. The service represents the four perspective values as a closed TypeScript union and accepts only scopes enabled in workspace settings.

3. Provide endpoints:

   ```text
   GET  /operations/strategy/objectives
   POST /operations/strategy/objectives
   GET  /operations/strategy/objectives/:id
   PUT  /operations/strategy/objectives/:id
   PUT  /operations/strategy/objectives/:id/bsc-focus
   ```

   Creating/editing the objective or scopes needs `strategy.analysis.write`. Activating an objective validates the settings snapshot: BSC `REQUIRED` needs one or more valid active scopes; BSC `OPTIONAL` can have zero. Store `settingsRevision` in the objective activation metadata so the later workflow can explain which policy applied.

4. Do not edit `bsc_scorecard_widget.dart` in this task. This backend task establishes that BSC scope is a strategic input, distinct from the later read-only scorecard.

5. Test BSC-off activation without scope, required-mode rejection without scope, rejection of disabled perspective, duplicate-perspective upsert behaviour, project cross-workspace rejection, and updating an archived objective rejection.

**Verification:**

```bash
cd services/company && pnpm test -- operations/strategy/tests/strategic-objective.test.ts
cd services/company && pnpm typecheck
```

**Commit:** `feat(strategy): add objectives and BSC focus scopes`

## Task 3: Thay lens ma bằng PESTEL, nguồn lực/năng lực và SWOT có lineage

**Files:**
- Create: `services/company/operations/migrations/47_strategy_analysis_artifacts.up.sql`
- Create: `services/company/operations/migrations/47_strategy_analysis_artifacts.down.sql`
- Modify: `services/company/shared/db/schema/strategy.ts`
- Create: `services/company/operations/strategy/services/strategy-analysis.service.ts`
- Create: `services/company/operations/strategy/handlers/strategy-analysis.handler.ts`
- Create: `services/company/operations/strategy/tests/strategy-analysis.test.ts`
- Modify: `services/company/operations/strategy/handlers/evidence.handler.ts`

1. Create three workspace-scoped artefact tables, all linked by composite FK to the strategic objective:

   | Table | Required fields | Purpose |
   | --- | --- | --- |
   | `strategy.pestel_signals` | `dimension`, `statement`, `impact`, `certainty`, `evidence_refs`, `bsc_perspectives`, `status` | external signal in P/E/S/T/E/L |
   | `strategy.resource_capability_assessments` | `category`, `statement`, `strength_level`, `evidence_refs`, `bsc_perspectives`, `status` | internal resource/capability assessment using the six approved categories |
   | `strategy.swot_items` | `kind`, `statement`, `source_type`, `source_id`, `evidence_refs`, `bsc_perspectives`, `status` | Strength/Weakness/Opportunity/Threat with source provenance |

   Use `jsonb` arrays for references and BSC perspectives, but validate their members in the service. Add indexes by `(workspace_id, strategic_objective_id, status)` and one-by-one IDs needed for provenance lookup.

2. Require a valid active strategic objective for every create/list route. If BSC is required, reject PESTEL/resource/SWOT items with no intersection between their BSC perspectives and enabled focus scopes. For `CLASSIC` or BSC off, allow the empty array.

3. Implement one typed analysis service rather than reusing `frontend/lib/modules/strategy/services/strategy_lens_service.dart`. It must expose create/update/list methods for each artefact and `deriveSwotDrafts`, which can only produce drafts with explicit source IDs and copied evidence references. No API should claim an AI-generated draft is reviewed.

4. Add routes under `/operations/strategy/objectives/:objectiveId/analysis/*` for PESTEL, resources, and SWOT. Retain `strategy.analysis.write` for mutation and `strategy.read` for list/get. Extend evidence response usage only to supply references; do not duplicate evidence records into analysis tables.

5. Test workspace isolation, source-to-SWOT provenance, BSC required intersection validation, rejection of invalid PESTEL/BSC/resource enums, and no AI/agent request being able to make a SWOT item active without a human write call.

**Verification:**

```bash
cd services/company && pnpm test -- operations/strategy/tests/strategy-analysis.test.ts operations/strategy/tests/execution-planning-chain.test.ts
cd services/company && pnpm typecheck
```

**Commit:** `feat(strategy): add objective-scoped PESTEL resource and SWOT analysis`

## Task 4: TOWS scoring, recommendation, selection limit and decision audit

**Files:**
- Create: `services/company/operations/migrations/48_tows_option_selection.up.sql`
- Create: `services/company/operations/migrations/48_tows_option_selection.down.sql`
- Modify: `services/company/shared/db/schema/strategy.ts`
- Modify: `services/company/operations/strategy/services/decision-record.service.ts`
- Create: `services/company/operations/strategy/services/tows-option.service.ts`
- Create: `services/company/operations/strategy/handlers/tows-option.handler.ts`
- Create: `services/company/operations/strategy/tests/tows-option.test.ts`

1. Add `strategy.tows_options` with objective/workspace lineage, `quadrant` (`SO|WO|ST|WT`), title, rationale, linked SWOT item IDs, `status` (`DRAFT|PROPOSED|SELECTED|REJECTED|SUPERSEDED`), AI provenance, selected actor/time, `decision_id`, and revision. Add `strategy.tows_option_evaluations` with option ID, `impact_score` and `difficulty_score` constrained to `1..5`, `rationale`, scorer actor/kind, and timestamp.

2. In `tows-option.service.ts`, calculate a transparent priority view (`impact`, `difficulty`, `priorityScore = impact * 2 - difficulty`) but never let that score change status itself. An agent can create `DRAFT` options/evaluations and return the ranking; it never receives a select endpoint or a terminal status transition.

3. Implement:

   ```text
   POST /operations/strategy/objectives/:objectiveId/tows-options
   PUT  /operations/strategy/tows-options/:id
   POST /operations/strategy/tows-options/:id/evaluations
   POST /operations/strategy/tows-options/:id/select
   POST /operations/strategy/tows-options/:id/reject
   GET  /operations/strategy/objectives/:objectiveId/tows-options
   ```

   `select` requires `requireStrategyGovernanceAuthority(..., "strategy.option.select", ...)`, locks the objective row or otherwise serialises the count check, limits selected rows to the settings value, and writes a `decision_records` entry that captures candidate ranking, settings revision, selected IDs, approver, reason, and source evidence. `reject` needs the same authority. Replacement must change an existing selected option to `SUPERSEDED` in the same transaction before selecting the replacement.

4. The service must reject selection when source SWOT items are not active, when option/workspace/objective are mixed, or when `impact_score`/`difficulty_score` is absent. Ensure a concurrent pair of selection requests cannot both exceed the limit.

5. Test top-1 and top-2 policy, concurrent select collision, delegated approver success, agent selection denial, automatic score ordering without automatic selection, decision provenance, and replacement selection retaining audit history.

**Verification:**

```bash
cd services/company && pnpm test -- operations/strategy/tests/tows-option.test.ts identity/tests/permission-evaluator.test.ts
cd services/company && pnpm typecheck
```

**Commit:** `feat(strategy): add scored and governed TOWS selection`

## Task 5: Nối TOWS đã chọn với OKRs và Initiative

**Files:**
- Create: `services/company/operations/migrations/49_strategy_okr_initiative_lineage.up.sql`
- Create: `services/company/operations/migrations/49_strategy_okr_initiative_lineage.down.sql`
- Modify: `services/company/shared/db/schema/operations.ts`
- Modify: `services/company/operations/services/okr.service.ts`
- Modify: `services/company/operations/handlers/okr.handler.ts`
- Modify: `services/company/operations/services/initiative.service.ts`
- Modify: `services/company/operations/handlers/initiative.handler.ts`
- Create: `services/company/operations/strategy/tests/strategy-okr-initiative-lineage.test.ts`

1. Turn the currently unreferenced `okr_objectives.strategic_objective_id` into an enforced composite relationship with `strategy.strategic_objectives(id, workspace_id)`. Add `tows_option_id` and `published_by_member_id/published_at` to objective. Add columns to `strategy.initiatives`: `strategic_objective_id`, `source_tows_option_id`, `description`, `intended_outcome`, `start_date`, `target_date`, `milestones jsonb`, `approval_status` (`DRAFT|PENDING_APPROVAL|APPROVED|REJECTED|CLOSED`), approver fields, revision. Create `strategy.initiative_key_results(workspace_id, initiative_id, key_result_id)` with a composite primary key and same-workspace validation.

2. Extend `CreateObjectiveParams`, API DTOs, and views with `strategicObjectiveId` and `towsOptionId`. New strategic objectives must originate from a `SELECTED` option in the same workspace/objective. Keep legacy objectives nullable so existing records migrate without fabrication. Add `publishObjectiveService` rather than treating ordinary edit as publication; it validates one to three KRs, each with title/baseline/current/target/unit/scoring contract, then requires `requireStrategyGovernanceAuthority(..., "strategy.okr.publish", ...)`.

3. Expand initiative create/update/read APIs to carry lineage, outcome, dates, milestones and linked KR IDs. `PENDING_APPROVAL → APPROVED` calls `requireStrategyGovernanceAuthority(ctx, "strategy.initiative.approve", scope, settings)` and records approver, decision ID and settings revision. Only approved Initiatives can be attached to new strategic weekly commitments; BAU remains permissible with no initiative.

4. Validate every relation at the database boundary and service boundary: cycle/objective/KR, Initiative/KR, Initiative/project, source TOWS option, and objective must share the workspace. Do not use a client-supplied workspace ID as evidence of ownership.

5. Test no selected-TOWS lineage rejection, selected option happy path, four-KR publish rejection, cross-workspace KR link rejection, initiative approval authorization, nullable legacy read, and one objective’s KRs appearing in the initiative lineage response.

**Verification:**

```bash
cd services/company && pnpm test -- operations/strategy/tests/strategy-okr-initiative-lineage.test.ts operations/tests/execution-outcome.test.ts
cd services/company && pnpm typecheck
```

**Commit:** `feat(strategy): link selected strategy to OKRs and initiatives`

## Task 6: Bảo toàn Initiative khi materialize weekly execution và tasks

**Files:**
- Modify: `services/company/operations/services/execution-plan.service.ts`
- Modify: `services/company/operations/services/twelve-week-year.service.ts`
- Modify: `services/company/operations/services/task.service.ts`
- Modify: `services/company/operations/services/initiative.service.ts`
- Modify: `services/company/operations/tests/execution-plan-accept.test.ts`
- Modify: `services/company/operations/tests/twelve-week-plan-update.test.ts`
- Create: `services/company/operations/tests/initiative-workspace-integrity.test.ts`

1. Extend the execution-plan action contract with optional `initiativeId`. At acceptance, load and validate the Initiative once in the caller workspace, require `APPROVED` for a strategy-bound action, and preserve it when inserting `weeklyCommitments`. Replace the current hard-coded `initiativeId: null` materialisation path with the validated value.

2. When tasks are generated from a weekly commitment, copy the commitment initiative. For direct task and direct commitment creation, look up the referenced initiative and reject missing, soft-deleted, cross-workspace, or unapproved Initiative references. Retain the existing direct BAU flows when the field is null.

3. Limit agent-generated execution plans to proposal state. `requireFounderCommand` in the acceptance path must be replaced with the workspace strategy governance helper for `execution.plan.approve`, so the configured Founder-only/delegated approval model applies without weakening the existing permission catalog. Keep every approval event attributed to the human actor.

4. Build one reusable `assertInitiativeInWorkspace` helper in initiative service and call it from all three write services, rather than duplicating unscoped `initiatives.id` lookups.

5. Test proposed plan acceptance preserves initiative ID through commitment and task, assignment to a different workspace is rejected, unapproved initiative is rejected for strategic work, BAU task remains valid, and delegated execution-plan approver succeeds while a non-grantee fails.

**Verification:**

```bash
cd services/company && pnpm test -- operations/tests/execution-plan-accept.test.ts operations/tests/twelve-week-plan-update.test.ts operations/tests/initiative-workspace-integrity.test.ts
cd services/company && pnpm typecheck
```

**Commit:** `fix(operations): preserve approved initiative lineage in execution`

## Task 7: Phân vai Strategy Copilot nhưng giữ human-in-the-loop

**Files:**
- Modify: `services/company/operations/services/ai-member.service.ts`
- Modify: `services/company/operations/services/autonomy-classifier.ts`
- Modify: `services/company/operations/strategy/services/kickoff-suggestion-cosa-client.ts`
- Create: `services/company/operations/strategy/services/strategy-copilot.service.ts`
- Create: `services/company/operations/strategy/handlers/strategy-copilot.handler.ts`
- Create: `services/company/operations/strategy/tests/strategy-copilot-authorization.test.ts`

1. Extend `OwnerAgentProfile` only with `research_intelligence` and `strategy`. Map `research_intelligence` to evidence ingestion, source discovery, PESTEL extraction and resource-capability drafting; map `strategy` to SWOT synthesis, TOWS option drafts, ranking explanations, and initiative draft suggestions. Preserve `operations`, `finance`, `marketing` behaviour.

2. The agent configuration endpoint reads workspace settings and requires `requireStrategyGovernanceAuthority(..., "strategy.agent.configure", ...)`. It permits only profiles in `allowed_agent_profiles`, validates an available workforce member, and returns a capability manifest to the UI. Do not silently create an agent profile merely because a setting names it.

3. Proposal APIs have explicit response state (`DRAFT`/`PROPOSED`) and source evidence. They may call services that write draft artefacts, but they cannot invoke TOWS select/reject, Objective publish, Initiative approve, review close, framework settings write, or cycle resize. Those command handlers must independently retain their human authorization guard; no trust is placed in a caller’s `actorKind` field.

4. Test each new profile routing, disabled profile rejection, agent attempting every terminal transition receives permission denied, and human approver can accept a proposal through the normal selected/published/approved endpoints without losing provenance.

**Verification:**

```bash
cd services/company && pnpm test -- operations/strategy/tests/strategy-copilot-authorization.test.ts operations/tests/agent-claimable.test.ts
cd services/company && pnpm typecheck
```

**Commit:** `feat(strategy): add governed research and strategy copilot roles`

## Task 8: Add Weekly, Mid-cycle and End-cycle review lifecycle

**Files:**
- Create: `services/company/operations/migrations/50_cycle_reviews.up.sql`
- Create: `services/company/operations/migrations/50_cycle_reviews.down.sql`
- Modify: `services/company/shared/db/schema/operations.ts`
- Create: `services/company/operations/strategy/services/cycle-review.service.ts`
- Create: `services/company/operations/strategy/handlers/cycle-review.handler.ts`
- Modify: `services/company/operations/services/twelve-week-year.service.ts`
- Create: `services/company/operations/strategy/tests/cycle-review.test.ts`
- Modify: `services/company/operations/strategy/tests/weekly-review.test.ts`

1. Keep existing `strategy.weekly_reviews` as the workspace-wide operational journal. Add `operating.cycle_reviews` for project/cycle control, with `workspace_id`, `project_id`, `cycle_id`, `kind` (`WEEKLY|MID_CYCLE|END_CYCLE`), `scheduled_week_no`, `scheduled_at`, `status` (`SCHEDULED|IN_PROGRESS|COMPLETED|SKIPPED|SUPERSEDED`), KR/initiative/PESTEL snapshots, `decision_id`, review conclusion, actor, settings revision and revision timestamps.

2. Implement a deterministic `buildCycleReviewSchedule(durationWeeks, policy)`:

   ```ts
   // duration 1..3: WEEKLY + END_CYCLE only
   // duration >=4 and policy AUTO: add MID_CYCLE at Math.ceil(durationWeeks / 2)
   // policy CUSTOM: expose unscheduled mid-cycle creation to an authorized user
   // policy OFF: never create a mid-cycle automatically
   ```

   Schedule reviews at cycle creation/activation. On resize, preserve completed reviews, supersede incomplete obsolete slots, create new non-duplicated slots, and write the before/after schedule to the existing cycle revision journal.

3. Add routes to list reviews, start/update a scheduled review, and close it. Closing a weekly review may change weekly tasks; closing a mid-cycle review may propose or approve changes to Initiative/KR under their own existing authority; closing end-cycle review requires `requireStrategyGovernanceAuthority(..., "strategy.review.close", ...)` and creates a decision record. A review cannot directly mutate objective, KR, or Initiative state without calling that object’s command service and its permission check.

4. Snapshot visible PESTEL signals and active initiatives at review start. A later edit must not rewrite the historical review basis. Link a decision record rather than copying approval detail again.

5. Test 1/3/4/8/10/16-week schedules, custom/off policies, timezone-safe scheduled dates from the existing calendar helper, resize rescheduling, immutable completed snapshots, cross-workspace rejection, and founder/delegated review closer coverage.

**Verification:**

```bash
cd services/company && pnpm test -- operations/strategy/tests/cycle-review.test.ts operations/strategy/tests/weekly-review.test.ts operations/tests/twelve-week-plan-update.test.ts
cd services/company && pnpm typecheck
```

**Commit:** `feat(strategy): schedule governed mid-cycle and end-cycle reviews`

## Task 9: Replace Flutter ghost lens client with typed operating-strategy APIs

**Files:**
- Create: `frontend/lib/modules/strategy/models/strategy_workflow_models.dart`
- Create: `frontend/lib/modules/strategy/services/strategy_workflow_service.dart`
- Modify: `frontend/lib/modules/strategy/services/strategy_lens_service.dart`
- Modify: `frontend/lib/modules/hologram_hub/controllers/mixins/hub_lenses_mixin.dart`
- Modify: `frontend/lib/modules/strategy/views/tabs/strategy_lenses_tab.dart`
- Modify: `frontend/lib/modules/strategy/views/strategy_view.dart`
- Create: `frontend/test/modules/strategy/services/strategy_workflow_service_test.dart`

1. Create immutable Dart DTOs for workspace settings, objective, BSC scope, PESTEL signal, resource/capability assessment, SWOT item, TOWS option/evaluation, Initiative and cycle review. Keep enum conversion tolerant on read (`unknown` maps to an explicit unsupported state) and strict on writes.

2. `StrategyWorkflowService` is the only service that calls the new `/operations/strategy/*` routes. It uses the established API client/workspace header mechanism and sends `expectedRevision` for policy-changing writes. Replace every use of `/strategy/lenses/*`; do not leave hidden fallback calls to these route-inventory ghosts.

3. Deprecate `StrategyLensService` by making it a thin adapter during one release only, forwarding to workflow service without changing request paths. Then remove the adapter and its imports once `StrategyLensesTab` and `HubLensesMixin` use typed workflow state directly. The migration makes failed legacy requests impossible to mask.

4. Add unit tests using the frontend HTTP mock pattern to assert each request path, header propagation, JSON mapping, revision-conflict mapping, and no request whose path starts with `/strategy/lenses`.

**Verification:**

```bash
cd frontend && flutter test test/modules/strategy/services/strategy_workflow_service_test.dart
cd frontend && flutter analyze
```

**Commit:** `refactor(frontend): use operating strategy workflow APIs`

## Task 10: Implement the guided BSC-filter-to-TOWS flow in Flutter

**Files:**
- Modify: `frontend/lib/modules/strategy/views/tabs/strategy_lenses_tab.dart`
- Modify: `frontend/lib/modules/hologram_hub/widgets/lenses/strategy_lenses_hub_modal.dart`
- Modify: `frontend/lib/modules/hologram_hub/widgets/lenses/tows_matrix_widget.dart`
- Modify: `frontend/lib/modules/hologram_hub/widgets/lenses/bsc_scorecard_widget.dart`
- Create: `frontend/lib/modules/strategy/widgets/strategic_objective_step.dart`
- Create: `frontend/lib/modules/strategy/widgets/bsc_focus_scope_step.dart`
- Create: `frontend/lib/modules/strategy/widgets/strategy_analysis_step.dart`
- Create: `frontend/lib/modules/strategy/widgets/tows_prioritization_step.dart`
- Create: `frontend/test/modules/strategy/views/strategy_workflow_test.dart`

1. Replace the existing peer tabs and hardcoded PESTEL → SWOT → TOWS → BSC stage order with a guided stateful sequence:

   ```text
   Strategic objective
     → BSC focus scope (conditional on workspace policy)
     → PESTEL + resource/capability assessment
     → SWOT with source provenance
     → TOWS evaluation and human selection
   ```

   The page must state the selected objective and current BSC focus at all later steps, so users see the context constraining the analysis.

2. Render the six resource/capability categories by their approved Vietnamese names. Require a source/evidence chip for every manual SWOT item and show the BSC perspective chips on PESTEL/resources/SWOT. Do not label the category simply “Tài/Nhân/Trí/Vật”.

3. TOWS UI accepts only scores 1–5, shows impact and difficulty separately plus the ranking explanation, never auto-checks an option, and renders a selection counter such as `1 / 1 chiến lược đã chọn`. Disable selection at the policy limit and show the server validation error if a concurrent change occurred. Replace the current fixed twelve-cell direct-tactic presentation.

4. Change `bsc_scorecard_widget.dart` into a read-only scorecard of published Objectives/KRs grouped by perspective. Remove any creation/edit path that treats BSC as an independent planning phase. The wrapper/modal reads settings and feature state from server rather than `P5/P6` client-side unlock heuristics.

5. Widget tests cover BSC OFF, OPTIONAL skipped, REQUIRED blocking, an enabled/disabled perspective, evidence/provenance rendering, selection counter at one/two, and no “BSC next to PESTEL” peer navigation control.

**Verification:**

```bash
cd frontend && flutter test test/modules/strategy/views/strategy_workflow_test.dart
cd frontend && flutter analyze
```

**Commit:** `feat(frontend): guide BSC-filtered strategy analysis and TOWS choice`

## Task 11: Surface OKR → Initiative → task and review control in the workspace

**Files:**
- Modify: `frontend/lib/modules/strategy/services/okr_service.dart`
- Modify: `frontend/lib/modules/strategy/views/strategy_view.dart`
- Modify: `frontend/lib/modules/strategy/views/project_kickoff_view.dart`
- Create: `frontend/lib/modules/strategy/widgets/initiative_plan_panel.dart`
- Create: `frontend/lib/modules/strategy/widgets/cycle_review_timeline.dart`
- Create: `frontend/lib/modules/strategy/widgets/workspace_strategy_settings_sheet.dart`
- Create: `frontend/test/modules/strategy/views/initiative_and_review_test.dart`

1. Repoint the legacy OKR client to the existing `/operations/okr-cycles/*` family while adding strategic-objective/TOWS lineage and explicit publish actions. The UI must make “Draft” and “Published” visibly distinct; it cannot claim a selected strategy was executed until its objective and Initiative have passed their approval states.

2. Add an Initiative Plan panel after Objective/KRs: title, intended outcome, linked KRs, owner, target date, milestones, status and approval reason. It creates an Initiative in draft, submits it for approval, and shows its downstream weekly commitments/tasks. Weekly sprint UI chooses an approved Initiative or explicitly marks an item BAU.

3. Add a review timeline to the current project/cycle view. It shows Weekly, Mid-cycle and End-cycle slots calculated by server, review status, the policy revision used, and decision link. Only show edit/close actions when the `can*` flags returned by API permit them; never decide from a local “founder” role string.

4. Add workspace Settings entry for strategy method, BSC mode/perspectives, TOWS limit, review policy, agent profiles and approval policy. It is read-only when `canEdit` is false. The settings sheet submits revisions and handles a 409 by reloading instead of overwriting another approver’s configuration.

5. Test Initiative approval state gating task association, BAU task creation, one- and two-option policies, 10-week mid-cycle position, settings read-only state, and revision conflict recovery.

**Verification:**

```bash
cd frontend && flutter test test/modules/strategy/views/initiative_and_review_test.dart
cd frontend && flutter analyze
```

**Commit:** `feat(frontend): add initiative planning reviews and strategy settings`

## Task 12: End-to-end contract, migration and regression verification

**Files:**
- Create: `services/company/operations/strategy/tests/strategy-workflow-e2e.test.ts`
- Modify: `docs/architecture/generated/route-inventory.md`
- Create: `docs/architecture/strategy-workflow-governance.md`

1. Create an integration-style Vitest flow with two workspaces and four actors: Founder, delegated strategy approver, regular member and strategy agent. Exercise settings → objective → BSC scope → PESTEL/resource → SWOT → TOWS score/select → Objective/KRs/publish → Initiative/approve → execution plan/weekly commitment/task → reviews. Assert every parent ID, selected policy revision and decision ID is preserved.

2. Include negative paths: required BSC with no scope, data from workspace B used in workspace A, fourth KR, auto-selection by agent, unapproved Initiative attached to task, policy relaxation at project/cycle, and review close by an unauthorised actor.

3. Run migrations against a disposable database from the repository migration runner, then run the full Company test suite and Flutter test suite. Update route inventory to remove `/strategy/lenses/*` from active expectations and document each real `/operations/strategy/*` route, permission and agent boundary in the architecture document.

4. Manually smoke-test a 10-week cycle: configured Mid-cycle review is scheduled in week 5, changing the cycle duration preserves the completed review history, and the BSC scorecard only reflects published KRs.

**Verification:**

```bash
cd services/company && pnpm migrate
cd services/company && pnpm test
cd services/company && pnpm typecheck
cd frontend && flutter test
cd frontend && flutter analyze
git diff --check
```

**Commit:** `test(strategy): verify governed strategy-to-execution workflow`

## Delivery checkpoints

1. After Task 4, demo the complete strategy analysis path through a selected TOWS option; no execution write exists yet.
2. After Task 8, demo the selected option through a published OKR, approved Initiative, weekly task, and a 10-week mid-cycle review.
3. After Task 11, demo the same path in Flutter with a Founder workspace and a delegated-approver workspace.
4. After Task 12, inspect migration output, all focused/full test results, and `git diff --check` before presenting the branch for review.
