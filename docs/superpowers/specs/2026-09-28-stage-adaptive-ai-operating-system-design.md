# Stage-Adaptive AI Operating System Design

**Status:** Proposed — source-traced on `main`; not implementation or runtime-production evidence.

**Date:** 2026-09-28

## 1. Mục tiêu

Đưa COSA từ một **Governed Agent Platform theo Project** thành một AI Operating
System tăng trưởng cùng startup: hỗ trợ Founder khám phá và kiểm chứng ở P0–P2,
đưa workflow AI tạo giá trị đo được ở P3–P4, rồi vận hành một digital workforce
có kiểm soát ở P5–P6.

Thiết kế không coi AI là một sản phẩm chatbot độc lập. Mỗi năng lực AI phải gắn
với một Project, một vấn đề kinh doanh, một owner, một mức tự chủ, một mức rủi
ro, bằng chứng dữ liệu và quyết định tiếp tục/điều chỉnh/dừng rõ ràng.

Kết quả mong muốn:

1. Founder và team quản lý danh mục AI bằng business outcome, adoption, quality,
   risk và cost — không bằng số Agent, prompt hay PoC.
2. Mức kiểm soát tăng theo Project lifecycle và autonomy tier, thay vì ép P0
   phải dùng governance của P6 hoặc để P6 chạy như P0.
3. AI Initiative có hợp đồng bền vững với Objective/KR, Project, metric,
   data-readiness, policy, evaluation và usage/cost.
4. Knowledge/Data chỉ được nâng mức capability khi có ingestion, authorization,
   provenance, quality và E2E evidence; không gọi lexical/in-memory path là
   enterprise knowledge platform.
5. Core tiếp tục là identity/organization authority; Company là business truth;
   COSA chỉ thực thi Agent qua Company authority, Capability Gateway, Governance
   và Audit.

## 2. Bối cảnh source-backed

### 2.1 Nền tảng có thể tái sử dụng

- Run business đã có `workspace_id` + `project_id`; worker fail closed khi thiếu
  Project và re-check Project của conversation trước kernel.
- `ProjectAgentRunAuthority` từ Company trả Project/Workspace/profile, exact
  AgentSpec identity, AI `WorkforceMember` và policy snapshot. Agent Platform
  không trực tiếp đọc Company DB.
- Capability đã có matrix T0 read, T1 reversible draft, T2 commit và T3
  external. T2 trong chat yêu cầu founder approval; T3 external chưa mở cho
  chat Agent.
- `models.run_usage` đã ghi provider/model/tokens/cost theo Workspace, Project,
  run và profile. Structured logging có trace, run, policy và capability fields.
- Objective/KR, Project lifecycle P0–P6, Executive Board role preset, asset
  evaluation và skill/Agent exact pin đã tồn tại ở các mức khác nhau.

### 2.2 Giới hạn hiện tại cần đóng

- `strategy.pilot.*`, metric contract và usage ledger chưa tạo một value
  portfolio có baseline, ROI, budget, decision và read-back state chung.
- Evaluation asset hiện thiên về structural/policy validation; chưa phải suite
  đo business-task success, groundedness, regression, cost hay safety.
- Vault document ingestion chưa release; semantic retrieval không có production
  embedding provider được wire. Không được công bố enterprise knowledge as ready.
- Repository chưa có source-backed capability cho workforce literacy, training,
  organizational readiness hoặc change-management telemetry. Các phần này phải
  được thiết kế như operating process + product evidence, không bịa thành data
  model ngay.

## 3. Phạm vi và không-phạm-vi

### Trong phạm vi

- Một AI Initiative Portfolio Project-scoped, lifecycle và decision gates.
- Value, FinOps, evaluation, data-readiness và governance contracts cần thiết
  để Pilot → Scale có bằng chứng.
- Stage/adoption/autonomy policy áp dụng cho COSA Agent/Workflow/Knowledge
  capability.
- Read model/API/UI truthful tối thiểu cho Founder/owner xem portfolio và quyết
  định, không tạo success giả.
- Cross-plane contracts, migrations expand-only, audit, verification và rollout.

### Không trong phạm vi

- Không triển khai một ERP, HRIS, LMS hay data lake tổng quát.
- Không tạo Organization AI CoE, governance board hay training portal như các
  bảng CRUD độc lập trước khi có owner/process thật; COSA chỉ lưu decision và
  evidence mà nó cần vận hành.
- Không nới quyền Agent, không cho LLM tự cấp capability, tự publish asset, tự
  đổi policy, tự chọn Project hoặc tự quyết high-impact action.
- Không thay Core bằng COSA/Company cho authentication, membership, role hoặc
  organization authority.
- Không bật Vault/semantic retrieval, connector write hoặc autonomous external
  action chỉ bằng feature flag/UI.

## 4. Các bất biến kiến trúc

| Invariant | Quy tắc |
|---|---|
| Authority | Core quyết định identity/organization; Company quyết định business membership, Project, ownership, budget và side effect; COSA thực thi đúng delegation/policy đã cấp. |
| Scope | Mọi AI Initiative, evidence, evaluation, usage và decision business mới có `workspace_id` + `project_id`; không infer từ active UI, title hay thứ tự list. |
| Project asset boundary | Agent/Skill/Workflow tái sử dụng thuộc Workspace; Project chỉ bind scope, policy, data, budget và exact pin. |
| Exactness | Run/initiative evaluation lưu immutable id/version/hash cho AgentSpec, prompt/model route, skill/workflow và knowledge snapshot khi dùng. |
| Autonomy | Quyền action được quyết định bởi code: capability tier + policy snapshot + initiative autonomy tier + live authority. Prompt không được tăng quyền. |
| Value truth | Không `SCALE`/`ACTIVE` khi thiếu baseline, owner, metric contract hoặc evidence gate bắt buộc. Không thay missing value bằng `0`, current time hoặc green status. |
| Data truth | Không đánh dấu data-ready hay semantic-ready nếu ingestion, entitlement, provenance, quality/eval và runtime wire chưa đủ. |
| Evidence | Static/unit/mock là evidence hẹp. Authority, approval/resume, revocation, data isolation, outbox/retry và restart phải qua disposable PostgreSQL/process E2E. |

## 5. Mô hình trưởng thành theo Project stage

`ProjectLifecycleStage` là context để áp mức tối thiểu; không phải quyền tự động
activate Agent hay auto-promote Initiative.

| Project stage | Mục tiêu AI | Autonomy tối đa mặc định | Điều kiện bắt buộc trước khi dùng | Decision gate |
|---|---|---|---|---|
| P0_DISCOVERY | research, synthesis, assumption/draft | T0/T1 | owner, problem statement, Project scope, source/evidence declaration | `DISCOVER → PILOT` |
| P1–P2 validation | test hypothesis/use case | T0/T1; T2 founder-approved case-by-case | baseline plan, success metric, risk tier, data-readiness assessment | `PILOT → VALIDATE` |
| P3_BUILD_VALIDATE | workflow nội bộ có outcome | T2, approval-bound | metric contract, evaluation suite, budget, tool/data authorization | `VALIDATE → SCALE_CANDIDATE` |
| P4_GO_TO_MARKET | workflow ảnh hưởng vận hành/khách hàng có kiểm soát | T2; T3 vẫn denied mặc định | quality/SLO, human escalation, audit, cost guardrail, incident owner | `SCALE_CANDIDATE → SCALED` |
| P5_OPERATE_GROWTH | digital workforce theo domain | T2 delegated; T3 chỉ qua ADR/future approval | recurring value evidence, FinOps allocation, data observability, process E2E | periodic portfolio review |
| P6_SCALE_GOVERN | portfolio cross-Project/Workspace | theo capability policy, never prompt | governance evidence, policy review, resilience/recovery and revocation proof | continue, reduce autonomy, pause or retire |

Các stage là **minimum controls**. Risk tier cao hoặc external effect luôn nâng
yêu cầu, kể cả Project đang ở P0. Một P6 Project vẫn có thể chạy Initiative
PILOT với control nhẹ hơn nếu capability/autonomy thấp; không được mượn stage
cao để bỏ qua evidence của workflow mới.

## 6. AI Initiative Portfolio

### 6.1 Aggregate và ownership

Tạo một aggregate Company-owned `AiInitiative`. Đây là đơn vị duy nhất dùng để
quản trị business value của một AI use case. Nó không thay thế AgentSpec,
Workflow, Objective/KR, model profile hay Project; nó liên kết các identity đó.

```text
AiInitiative
  id, workspace_id, project_id
  title, business_problem, intended_outcome
  lifecycle_state, project_stage_snapshot
  business_owner_member_id, technical_owner_member_id, risk_owner_member_id?
  objective_id?, key_result_ids[]
  autonomy_tier, risk_tier
  baseline_ref, metric_contract_ref
  data_readiness_assessment_ref
  budget_policy_ref, evaluation_policy_ref
  deployment_binding_ref?             # exact Agent/Skill/Workflow pins; optional before build
  knowledge_snapshot_ref?             # only if published/pinned
  created_at, updated_at, version
```

Owner fields tham chiếu durable `WorkforceMember`/Company member. Một AI agent
không thể là business/risk owner; agent có thể là `technical_execution_profile`
trong deployment binding. Company validates member eligibility and Project
membership; COSA never trusts a client-provided owner.

### 6.2 State machine

```text
DISCOVER
  -> PILOT              owner + problem + intended outcome + initial risk/data assessment
  -> RETIRED            duplicate/not viable
PILOT
  -> VALIDATE           baseline + metric contract + bounded evaluation evidence
  -> PAUSED / RETIRED
VALIDATE
  -> SCALE_CANDIDATE    target evidence + cost allocation + release gate
  -> PAUSED / RETIRED
SCALE_CANDIDATE
  -> SCALED             human escalation + production evidence + owner acceptance
  -> PAUSED
SCALED
  -> PAUSED / RETIRED   periodic value/risk/quality review
PAUSED
  -> PILOT / VALIDATE / SCALE_CANDIDATE   explicit remediation and new decision
RETIRED                 terminal; history remains append-only
```

Transitions use optimistic `expectedVersion`, an idempotency key, authenticated
actor, reason code and append-only event. A rejected transition returns a typed
machine code plus missing gate identifiers; it never silently coerces status.

### 6.3 Value contract

Một Initiative từ `PILOT` trở lên phải có exactly one active `AiValueContract`:

```text
AiValueContract
  initiative_id, revision
  metric_contract_id
  baseline_value, baseline_observed_at, baseline_source_ref
  target_value, target_by
  measurement_window, unit, scoring_direction
  expected_value_method            # revenue/cost/risk/cycle-time/quality
  expected_value_amount?           # decimal string + currency where monetary
  adoption_target, adoption_window
  measurement_owner_member_id
```

`baseline_value` và value amount dùng decimal string/minor units theo contract,
không `double`/`float`. `baseline_source_ref` là source identity hoặc explicit
`unavailable` state; missing baseline không thể qua `VALIDATE`.

Metrics thực thi được tái sử dụng `analytics.metric_contract`; Objective/KR
chỉ là business alignment, không là nơi tính ROI thay thế metric contract.

### 6.4 Portfolio read model

Founder/owner chỉ thấy Initiatives thuộc Project họ được Company authorize. Read
model trả:

- current lifecycle, stage snapshot, owner display state;
- baseline/target/latest outcome with explicit missing/invalid/unavailable;
- adoption, quality, safety, cost and data-readiness statuses;
- required next gate and blocking evidence;
- immutable references to decision/evaluation/usage windows.

Không trả raw prompt, tool arguments, secret, document contents, raw model
output hoặc cross-Project aggregate without separate authorization.

## 7. Governance by autonomy and risk

### 7.1 Hai dimension độc lập

`risk_tier` đo mức hậu quả (data sensitivity, regulatory/customer/financial
impact); `autonomy_tier` đo mức Agent có thể đi từ trả lời đến thực thi. Không
gộp chúng thành một enum.

```text
Autonomy A0: insight/read-only
Autonomy A1: draft/recommendation, human applies
Autonomy A2: internal commit, exact approval checkpoint required
Autonomy A3: delegated bounded execution (future; no external default)
```

Hiện implementation chỉ map A0/A1/A2 vào T0/T1/T2. A3 là reserved; không mở
T3. Khi future ADR xét A3, capability must be individually allowlisted with
spend/action limits, authenticated recipient, kill switch and post-action audit.

### 7.2 Promotion policy

`InitiativePromotionPolicy` là derived code policy, versioned/persisted as a
snapshot on transition. Minimum rules:

- `PILOT → VALIDATE`: baseline + metric + owner + risk tier + assessment.
- `VALIDATE → SCALE_CANDIDATE`: evaluation suite passes; cost budget; data
  readiness meets required level; no unresolved critical finding.
- `SCALE_CANDIDATE → SCALED`: human escalation route, rollback/pause procedure,
  required audit fields and process E2E all pass.
- Any transition to higher autonomy repeats authorization and required
  capability review; copied evidence from a different Project is invalid.

Policy decision binds initiative id/revision, deployment binding hash,
evaluation suite/version, metric revision, actor, timestamp and `decision_id`.
Run metadata includes the effective `initiative_id` and decision reference. A
run may use a lower autonomy than Initiative; it may never exceed it.

### 7.3 Approval and delegation

Existing approval stays bound to `run_id + tool_call_id + checkpoint_ref`. New
portfolio transitions are Company governance actions, never Agent tool calls.
Founder delegation may authorize defined governance tasks but cannot let a
delegate raise autonomy/risk override without scope and expiry checks. Revoked
membership/delegation prevents new transition and new capability ticket; any
in-flight behavior follows existing durable approval/revocation policy.

## 8. FinOps and value measurement

### 8.1 Usage attribution

Extend the existing usage ledger additively so every chargeable AI execution
has `initiative_id` when it supports an Initiative. `initiative_id` is resolved
from the durable deployment/command record, not arbitrary client metadata.

```text
AiUsageAttribution
  initiative_id, run_id, workspace_id, project_id
  provider_type, model_id, prompt_tokens, completion_tokens, cost_usd
  evaluation_cost_usd?, retrieval_cost_usd?, human_review_cost_ref?
  recorded_at
```

Existing runs without an Initiative remain valid and appear as `unattributed`;
they are not backfilled by guessing. `unattributed` is an explicit portfolio
quality signal, not a zero-cost bucket.

### 8.2 Budget policy

`AiBudgetPolicy` is Project-scoped, versioned and contains period, currency,
soft/hard cost threshold, model/provider restrictions, and action on breach:
`WARN`, `REQUIRE_APPROVAL`, or `PAUSE_INITIATIVE`. It cannot delete a run or
retroactively alter cost records.

Hard breach stops scheduling/new runs before model invocation with a typed
reason. Resuming requires an authorized budget decision and audit event. A
budget gate is independent from provider rate-limit retry.

### 8.3 Outcome measurement

A scheduled/triggered measurement job reads only the declared metric contract
and writes a versioned `AiValueMeasurement`. It must preserve source period,
quality state and missing-data state. It does not let the LLM infer ROI from a
chat transcript.

Portfolio review evaluates, for the same bounded window: cost, target delta,
adoption, quality, safety incidents and human override rate. It produces a
recommendation only; Company-authorized owner makes `continue`, `reduce
autonomy`, `pause` or `retire` decision.

## 9. Evaluation and ModelOps release gates

### 9.1 Evaluation suite contract

Create a Workspace asset `AiEvaluationSuite`, immutable after publish and
exact-pinned by Initiative promotion/deployment.

```text
AiEvaluationSuite
  id, version, definition_hash, workspace_id
  initiative_kind, capability_ids, knowledge_snapshot_ref?
  cases[]: input fixture ref, expected assertion type, risk label
  thresholds: task_success, groundedness, policy_safety, cost, latency
  evaluator_version, data-handling classification
```

Fixtures cannot embed production secrets, unrestricted customer data or a raw
Vault document. Sensitive evidence is referenced by authorized fixture store
identity and redacted in read models/logs.

### 9.2 Gate categories

| Gate | Required from | Evidence |
|---|---|---|
| Structural/capability closure | PILOT | exact pins, no secret/raw shell, scope containment |
| Functional task success | VALIDATE | versioned cases and thresholds |
| Groundedness/data isolation | VALIDATE if retrieval/context used | citations, tenant-negative cases, no unauthorized source |
| Policy/tool safety | VALIDATE | denied/approval/misuse cases |
| Cost/latency | SCALE_CANDIDATE | bounded load evidence and budget fit |
| Process recovery | SCALED for actioning workflows | PostgreSQL/process restart, retry, revocation and audit proof |

An evaluation result is not reusable after material pin drift: changed
AgentSpec, prompt, model route, workflow, capability list, knowledge snapshot
or metric revision requires a new result. Cosmetic display-only changes do not.

### 9.3 Production observability

Use existing structured log/trace primitives; add stable fields only:
`initiative_id`, `initiative_revision`, `evaluation_suite_ref`, `budget_policy_ref`,
`autonomy_tier`, and `risk_tier`. Logs remain allowlisted/redacted. Metrics and
traces must not serialize prompt bodies, documents, credentials or tool payloads
without a separately approved secure audit store.

Define SLOs per Initiative, not global “agent quality”: completion, safety,
latency, cost and human-escalation targets. Breach opens an Initiative alert;
only authorized policy can pause it.

## 10. Data and enterprise knowledge readiness

### 10.1 Data readiness assessment

`AiDataReadinessAssessment` is an Initiative-attached, versioned owner
attestation plus machine-checkable references:

```text
source_refs[]                 # data product / Vault source identity, never raw URI
classification
access_authority_ref
freshness_slo
quality_dimensions            # completeness, accuracy, timeliness, lineage
metadata_owner_member_id
retrieval_mode                # none | lexical | semantic
knowledge_snapshot_ref?
assessment_status             # NOT_READY | CONDITIONAL | READY
evidence_refs[]
```

`READY` is invalid if the source lacks authorization/lineage/freshness evidence.
`CONDITIONAL` permits only lower-autonomy use explicitly stated in promotion
policy. It never permits a higher-risk write action merely because a human can
see the data elsewhere.

### 10.2 Knowledge enablement order

1. Keep Vault ingestion/retrieval labelled unavailable until it is wired.
2. Implement authorized ingestion with immutable source/version identity and
   workspace entitlement checks.
3. Add lexical retrieval E2E with citation provenance, source revocation,
   restart and no cross-tenant access.
4. Add a production-pinned embedding provider only after retrieval evaluation,
   model/residency decision and dimension/version migration design.
5. Permit semantic mode only for Initiatives whose assessment and evaluation
   explicitly reference the published provider/snapshot.

This design does not use a vector database as a substitute for governance.
Agent data access remains the intersection of principal/delegation, Project,
Initiative policy, source entitlement and capability.

## 11. Organization, people and operating cadence

These are operating responsibilities with durable COSA decision/evidence hooks,
not fake standalone product modules.

| Role | Required accountability |
|---|---|
| Founder / executive sponsor | AI investment priorities, risk appetite, scale/retire decisions |
| Business owner | problem, baseline, outcome, adoption and operating change |
| Technical owner | deployment, reliability, evaluation implementation, recovery |
| Data owner | source entitlement, quality, freshness, lineage and remediation |
| Risk owner | risk tier, policy exceptions, incident review and control acceptance |
| AI enablement function | reusable patterns, evaluation templates, FinOps taxonomy and community practice |

For P0–P2, a Founder can hold several roles but the system records that fact;
P5–P6 should require separation for high-risk Initiative policy. COSA records
owners, decisions, evidence, exception expiry and review due dates. Training,
job redesign and organization communication remain human-led processes but
adoption/override/escalation metrics make their result visible in portfolio
review.

Cadence:

- per initiative: evaluation before promotion and on material pin/data change;
- weekly/biweekly at P0–P4: owner review of value, adoption, blockers;
- monthly at P5–P6: portfolio cost/value/risk review;
- incident or policy breach: immediate pause/escalation path; no waiting for
  normal cadence.

## 12. Cross-plane ownership and interfaces

| Plane | Owns | Must not own |
|---|---|---|
| Core | identity, organization membership/roles, user authorization | Project business data, Agent policy decisions |
| Company | `AiInitiative`, value/budget/transition decisions, Project binding, owner authorization, business metrics | model inference and direct Agent execution |
| COSA Control Plane | policy snapshot/delegation, schedules, model/usage control contracts | Core identity or Company business writes |
| Agent Platform / apps/cosa | pinned execution, evaluation, retrieval/runtime enforcement, trace events | bypassing Company authority or direct business DB mutation |
| Flutter | truthful portfolio/read/action UX | authorization, transition validation or financial calculation |

New APIs use typed contracts in `shared/contracts/mvp-surface.json` when
user-facing. Public handlers validate/authorize then call service; handler does
not query DB directly. Internal cross-plane endpoints are service-authenticated
and fail closed. Company command results are outboxed before Agent execution;
cross-service transactions use outbox/inbox/reconciliation, never claimed ACID.

## 13. Failure handling and truthful UX

- Missing baseline/data/eval/budget is a blocking `GateStatus`, not a green card
  with an empty number.
- A failed evaluation or budget breach shows `PAUSED`/`BLOCKED` plus durable
  reason and permitted remediation, never a successful Agent result.
- UI actions use idempotency keys and display success only after canonical API
  returns the Initiative decision/evidence identity.
- Transition retry uses same idempotency key; duplicate command returns its
  original result and does not append a second decision.
- Provider/transient errors do not downgrade authorization failures or erase
  cost/evidence. Retry budgets are bounded and visible in run state.
- Existing runs without Initiative attribution remain readable; UI labels them
  `Chưa phân bổ sáng kiến`, not `0` cost/value.

## 14. Rollout, compatibility and rollback

### Phase A — inventory and contracts

Inventory every active Agent/Workflow capability and map it to Project,
Initiative eligibility, existing metric contract and risk/autonomy tier. Add
shared DTO/API contract first; no new UI call until contracts and service
authorization are present.

### Phase B — additive persistence and read-only portfolio

Create expand-only Company/COSA schema and migrations. Existing runs, schedules
and assets remain operational with `initiative_id = NULL`; they are explicitly
unattributed. Backfill only from a durable, unambiguous command/deployment
reference; otherwise leave null and report it.

### Phase C — gated Pilot/Validate

Enable Initiative creation/read and `DISCOVER → PILOT → VALIDATE` only. Keep
`SCALE_CANDIDATE`/`SCALED` unavailable until evaluation/budget/data gates and
process evidence exist. Run migration compatibility and negative authorization
tests before exposing Flutter CTAs.

### Phase D — scale gates and FinOps

Turn on attribution, budget enforcement, evaluation suite pinning and portfolio
review. Begin with `WARN`, observe cost/value quality, then only move selected
Initiatives to `REQUIRE_APPROVAL`/`PAUSE_INITIATIVE` hard gates after owner
sign-off.

### Phase E — knowledge and digital workforce expansion

Independently ship Vault/lexical/semantic readiness through its own evidence
gates. Do not make it a prerequisite to basic non-retrieval Initiatives. A3/T3
remain future ADR work, not an implicit result of this rollout.

Rollback disables new transition/dispatch paths by feature policy while keeping
append-only history and existing read models. Down migrations may only run when
they are safe under repository migration policy; operational rollback is
preferentially a forward migration/feature disable, never destructive deletion
of value, approval or audit evidence.

## 15. Acceptance criteria

1. Every new Initiative has exact Workspace/Project scope, authorized human
   owner(s), lifecycle state and append-only decision history.
2. A Project cannot promote an Initiative without the stage/risk/autonomy gates
   mandated here; missing evidence is machine-readable and visible truthfully.
3. Every attributed production run records Initiative identity; unknown legacy
   attribution stays explicit rather than guessed.
4. Cost, quality, adoption and business measurement are queryable for the same
   bounded Initiative/window without the LLM inventing ROI.
5. Material pin/data/model change invalidates prior release evaluation.
6. An Initiative cannot use retrieval/data beyond its assessment entitlement;
   semantic availability is not claimed before production wire/evidence.
7. Existing ProjectAgentRunAuthority, capability tiers and approval binding
   remain enforced; this design never adds a prompt-only authorization path.
8. Flutter/API never report scale, deployment, budget approval or value result
   as successful until canonical durable state is returned.
9. Disposable PostgreSQL/process E2E proves scope isolation, promotion denial,
   approval/resume, revocation, budget pause, idempotent retry, restart/recovery
   and cross-plane audit correlation for the first scaled Initiative.

## 16. Verification strategy

| Layer | Required evidence |
|---|---|
| Contracts | generated DTO/route checks; lifecycle/state machine parity; no unknown frontend route |
| Unit | transition policy, required gates, cost arithmetic, pin invalidation, data-readiness and budget threshold boundary cases |
| Service integration | Company authorization/optimistic concurrency/outbox; COSA policy/delegation/usage attribution; rejected cross-Project and revoked actor cases |
| Flutter | explicit blocked/unavailable/paused states; no fake success; idempotent action UX |
| Migration | expand-only compatibility, forward upgrade from pre-Initiative rows, no guessed backfill |
| Process E2E | Core/Company/COSA/worker/PostgreSQL path for a valid pilot and each high-impact negative/recovery case |
| Operations | dashboard/query demonstrates cost-value-quality-review window with redacted audit correlation |

## 17. Open decisions deliberately deferred

- Monetary ROI formula and currency conversion policy are business/finance
  decisions. The system stores declared method and decimal evidence but does not
  invent a universal formula.
- External A3/T3 autonomy, customer messaging, financial confirmation and
  deployment actions require individual ADRs and are not enabled here.
- Choice of production embedding provider/vector storage requires data residency,
  performance, cost and evaluation evidence; it is a separate design gate.
- Full HR learning/training content system is outside COSA until an accountable
  operating owner and source of truth are selected.

