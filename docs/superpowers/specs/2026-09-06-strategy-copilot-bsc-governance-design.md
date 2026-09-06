# Strategy Copilot, BSC filter và Human Approval Governance

**Status:** Approved direction — design only, no production implementation in this document.

**Goal:** Biến chiến lược thành một luồng có thể kiểm chứng và thực thi: AI hỗ trợ tối đa việc thu thập, tổng hợp, phân tích và đề xuất; founder hoặc người được ủy quyền là người duy nhất chốt các thay đổi chiến lược có hệ quả vận hành.

## 1. Bối cảnh và vấn đề

Frontend hiện mô tả PESTEL, SWOT, TOWS và BSC như bốn tab song song. BSC còn bị khóa cứng ở stage P5/P6 tại client. Các endpoint `/strategy/lenses/*` mà UI gọi không có backend tương ứng; đây chưa phải nghiệp vụ strategy có dữ liệu durable.

Backend đã có các nền tảng tái sử dụng được:

- workspace-scoped identity, workforce members, permission catalog và policy evaluator;
- evidence, decision record, OKR/KR, cycle N tuần, initiative, task và weekly commitment;
- execution plan nháp do agent đề xuất, với `AUTO`, `NEEDS_APPROVAL`, `FOUNDER_ONLY`, sau đó founder/co-founder duyệt thành task.

Khoảng trống là lineage chiến lược: không có Strategic Goal canonical; Initiative không liên kết KR; không có lựa chọn TOWS có kiểm soát; BSC/PESTEL/SWOT/TOWS chưa được hiện thực ở server; review giữa/cuối chu kỳ chưa là bản ghi theo cycle.

## 2. Quyết định thiết kế

### 2.1 BSC là scope phân tích, không là bước song song hay KPI store thứ hai

Luồng chuẩn khi workspace bật BSC là:

```text
Strategic Goal
  → BSC Focus Scope
  → PESTEL + Resource & Capability Assessment
  → SWOT theo Strategic Goal
  → TOWS options
  → đánh giá, chọn 1–2 option
  → OKR/KR
  → Initiatives
  → weekly commitments/tasks
```

`BSC Focus Scope` chọn các góc nhìn có liên quan (Financial, Customer, Internal Process, Learning & Growth), lý do và trọng số. Nó không bắt người dùng phải điền cả bốn góc nhìn, cũng không tạo KPI tách rời khỏi KR.

Một BSC scorecard báo cáo trong tương lai, nếu cần, phải đọc từ KR/metric contracts đã được publish; nó không được tạo một nguồn KPI độc lập.

### 2.2 Dùng thuật ngữ “Đánh giá nguồn lực và năng lực chiến lược”

Không dùng mnemonic “Tài/Nhân/Trí/Vật”. Mỗi assessment thuộc một hoặc nhiều nhóm chuẩn sau:

1. **Nguồn lực tài chính:** tiền mặt, runway, ngân sách, khả năng huy động vốn.
2. **Năng lực con người và tổ chức:** kỹ năng, capacity, lãnh đạo, cấu trúc và cách phối hợp.
3. **Tài sản tri thức, dữ liệu và sở hữu trí tuệ:** dữ liệu, know-how, quy trình, IP.
4. **Năng lực công nghệ và tài sản vận hành:** nền tảng, hệ thống, automation, hạ tầng.
5. **Tài sản thị trường và quan hệ hệ sinh thái:** khách hàng, brand, distribution, đối tác.
6. **Năng lực quản trị, pháp lý và kiểm soát rủi ro:** governance, compliance, quyền quyết định, kiểm soát nội bộ.

“Nguồn lực” là những gì workspace sở hữu/tiếp cận; “năng lực” là khả năng phối hợp chúng để tạo kết quả. Mỗi record phải nêu rõ loại nào, evidence/source, mức độ sẵn có, giới hạn và BSC perspective liên quan.

### 2.3 AI đề xuất rộng, con người kiểm soát điểm chốt

Agent có thể tạo draft, synthesis, score, cảnh báo variance và execution plan. Agent không thể tự chọn chiến lược, publish OKR, thay KR, phê duyệt Initiative, chốt review hay tự bật/tắt framework của workspace.

Mỗi quyết định chốt phải tạo decision record với actor, evidence snapshot, lựa chọn thay thế, policy/config version và lý do.

## 3. Scope và trạng thái theo workspace

Tạo `strategy.workspace_strategy_settings`, một row cho mỗi workspace. Không thêm các field strategy workflow vào `core.workspaces`; bảng workspace hiện tại chỉ tiếp tục là chủ sở hữu của Vision/Mission/Core Values.

```text
workspace_id                    PK
strategy_method                 CLASSIC | BSC_FILTER
bsc_mode                        OFF | OPTIONAL | REQUIRED
enabled_bsc_perspectives        JSONB string[]
tows_selection_limit            SMALLINT, CHECK 1..2, default 1
weekly_review_enabled           BOOLEAN, default true
mid_cycle_review_policy         OFF | AUTO | CUSTOM
end_cycle_review_enabled        BOOLEAN, default true
allowed_agent_profiles          JSONB string[]
approval_policy                 FOUNDER_ONLY | DELEGATED_APPROVER
revision                        INTEGER
updated_by_member_id            BIGINT nullable
updated_at
```

Semantics:

- `OFF`: BSC scope không hiện và không có validation BSC.
- `OPTIONAL`: BSC scope hiện ở đầu flow, có thể bỏ qua cho Strategic Goal cụ thể.
- `REQUIRED`: trước khi submit/chọn TOWS cần có goal và ít nhất một perspective được chọn. Không bắt đủ bốn perspective.
- `CLASSIC` cho phép PESTEL → SWOT → TOWS không có BSC filter; `BSC_FILTER` đặt BSC scope ở đầu luồng.
- Project/cycle chỉ có thể override chặt hơn workspace policy, không thể nới lỏng nó.

Settings được snapshot vào strategic planning cycle/review để lịch sử không đổi nghĩa khi founder đổi policy sau này. Mutation dùng optimistic revision và phát audit event.

## 4. Mô hình dữ liệu và lineage

### 4.1 Strategic Goal và analysis records

Tạo `strategy.strategic_objectives`:

```text
id, workspace_id, project_id nullable,
statement, desired_outcome, timeframe_start, timeframe_end,
status: DRAFT | ACTIVE | SUPERSEDED | CLOSED,
owner_member_id, created_by_member_id, revision, timestamps
```

`strategy.okr_objectives.strategic_objective_id` đã tồn tại nhưng phải được nâng thành FK có kiểm tra workspace, và service/API phải nhận trường này.

Tạo các record strategy durable:

- `strategy.bsc_focus_scopes`: `strategic_objective_id`, perspective, enabled, weight, rationale.
- `strategy.pestel_signals`: `strategic_objective_id`, project_id, dimension, signal, impact, horizon, evidence refs, BSC perspective tags, status.
- `strategy.resource_capability_assessments`: `strategic_objective_id`, resource_category, resource_or_capability, availability, constraint, evidence refs, BSC tags, status.
- `strategy.swot_items`: `strategic_objective_id`, category, statement, importance, evidence refs, source PESTEL/resource references, BSC tags, status.
- `strategy.tows_options`: `strategic_objective_id`, quadrant, title, description, source SWOT references, trade-offs, status.
- `strategy.tows_option_evaluations`: `tows_option_id`, impact_score, effort_score, confidence_score, score rationale, evaluated_by_kind, revision.

All tables carry `workspace_id`; relation tables use composite workspace-aware foreign keys, matching the repository’s tenant-isolation pattern. Source evidence remains a reference, not copied narrative.

### 4.2 Chọn chiến lược và chuyển thành OKR

`tows_options.status` has: `DRAFT`, `EVALUATED`, `SELECTED`, `NOT_SELECTED`, `SUPERSEDED`.

Only an actor with `strategy.option.select` can choose an option. The transaction must:

1. validate all source SWOT rows and the option belong to the same workspace/goal;
2. enforce `tows_selection_limit` across active selections for that goal/cycle;
3. create a decision record with rankings and rejected alternatives;
4. mark the option `SELECTED` and preserve historic selections as `SUPERSEDED`, never overwrite them;
5. permit creation of the linked Objective/KRs.

An Objective represents the selected strategy in outcome language. A maximum of three KRs is enforced at publish time, rather than preventing early drafts.

### 4.3 Initiative is the execution bridge

Keep `strategy.initiatives` but extend it with `source_tows_option_id`, `strategic_objective_id`, description, intended outcome, start/end date, milestone definition, owner and revision.

Create `strategy.initiative_key_results(workspace_id, initiative_id, key_result_id)` as the many-to-many bridge. An Initiative may affect multiple KRs and a KR may require multiple Initiatives. Its work output must not be treated as automatic KR attainment.

`weekly_commitments.initiative_id` and `tasks.initiative_id` remain valid execution links. New creation paths validate initiative, weekly plan and task all belong to the same workspace. Standalone BAU, compliance or discovery work remains valid without an Initiative but is explicitly labelled as such.

Execution-plan acceptance currently materializes commitments with `initiative_id = null`. Once an execution plan originates from an Initiative, this link must be preserved rather than discarded.

### 4.4 Cycle reviews

Keep `strategy.weekly_reviews` as workspace-wide operational/governance review (cash, obligations and multiple plans). Do not overload it with a project strategy review.

Create `operating.cycle_reviews`:

```text
id, workspace_id, project_id, cycle_id,
kind: WEEKLY | MID_CYCLE | END_CYCLE,
scheduled_for_week, completed_at,
status: SCHEDULED | IN_PROGRESS | COMPLETED | SUPERSEDED,
kr_snapshot, initiative_snapshot, external_signal_snapshot,
decision_id, recommendation, outcome, revision, timestamps
```

For `AUTO`, the mid-cycle is scheduled at `ceil(durationWeeks / 2)`: 6→3, 8→4, 10→5, 12→6, 16→8. Cycles of one to three weeks have no automatic mid-cycle review. A resize reschedules only unfinished reviews and writes a revision/audit event. End-cycle reviews are scheduled at the final week, not on a hard-coded “week 12”.

## 5. Strategy Copilot and agent responsibilities

Existing profiles `operations`, `finance` and `marketing` remain. Add two scoped profiles:

- `research_intelligence`: gathers external/internal signals, sources and freshness; produces candidate PESTEL and market/relationship assessments.
- `strategy`: synthesizes approved evidence and drafts goal scope, SWOT/TOWS evaluations, option trade-offs, OKRs and Initiative portfolios.

Agent output is always a proposal payload with source references, confidence and the current settings revision. It transitions through:

```text
DRAFT → PROPOSED → HUMAN_REVIEW → APPROVED | REJECTED | SUPERSEDED
```

The Strategy Copilot orchestrates, but does not replace specialist agents:

| Agent | May do | May not do |
|---|---|---|
| Research & Intelligence | Gather/classify signals, cite sources, flag freshness | Treat an inference as verified evidence or choose strategy |
| Finance | Assemble runway, budget and unit-economics context | Change finance records or approve allocation |
| Marketing/GTM | Summarize customer, channel and market evidence | Publish a chosen strategy |
| Operations | Assess capacity, dependencies, create draft execution plans | Commit tasks from a strategic draft without human approval |
| Strategy | Synthesize alternatives, scores, draft OKR/Initiatives/review packet | Select TOWS, publish OKR, approve Initiative/review |

Agents use short-lived, workspace- and capability-scoped delegation. Analysis calls are read-only or draft-only; they cannot use an approval capability.

## 6. Human authority and permissions

The repository has both a general permission catalog/evaluator and hard-coded founder/lifecycle guards. New strategy commands use the general `requireCommandAuthority` path and resource scope. This permits explicit delegation while remaining fail-closed.

Add to the permission catalog:

```text
strategy.framework.manage
strategy.analysis.write
strategy.option.select
strategy.okr.publish
strategy.initiative.approve
strategy.review.close
strategy.agent.configure
```

Suggested authority matrix:

| Action | Default authority | Delegation |
|---|---|---|
| View strategy context | Members with `strategy.read` | Yes |
| Add evidence and analysis drafts | `strategy.analysis.write` | Yes |
| Select TOWS / publish OKR / approve Initiative / close a review | Founder/co-founder | A human member with explicit corresponding permission and project scope, when `approval_policy=DELEGATED_APPROVER` |
| Change framework, agent set or approval policy | Founder/co-founder | No |

An administrator is not implicitly a strategic approver unless the permission evaluator grants the exact permission. This resolves the current inconsistency between founder-only command guards and lifecycle guards that also accept admin.

Every approval command takes an expected revision, checks workspace and project scope, records the human actor, and returns a conflict rather than silently overwriting a newer proposal.

## 7. API and UI boundaries

New server APIs use the implemented `/operations/strategy/*` namespace, not the ghost `/strategy/lenses/*` namespace.

The minimum surfaces are:

- workspace settings: get/update strategy settings;
- goals and BSC scopes: CRUD drafts, activate/supersede goal;
- PESTEL/resource/SWOT/TOWS: create draft, list by goal, evaluate option;
- explicit `select` TOWS command;
- draft/publish Objective and KRs from a selected option;
- Initiative CRUD/link KR/submit/approve;
- list/create/complete cycle reviews and review-decision command;
- read-only Strategy Copilot proposal and action-context endpoints.

The UI changes from four peer tabs to a guided, resumable workflow. It shows BSC as “Phạm vi BSC” before analysis when enabled. It must show provenance, staleness, agent/human actor and approval state, rather than presenting a generated draft as finalized strategy.

The TOWS screen cannot create a direct 12-week tactic. It first requires selection and an Initiative; execution is then planned from that Initiative using the actual cycle duration.

## 8. Validation and acceptance criteria

Backend and frontend coverage must demonstrate:

1. A workspace with BSC `OFF`, `OPTIONAL`, and `REQUIRED` behaves as configured; `REQUIRED` accepts one relevant perspective and rejects a selection with no scope.
2. Cross-workspace goal, option, initiative, KR and review links fail at both service and database boundary.
3. A member may draft analysis but cannot select/publish/approve without granted capability; an explicitly delegated approver can only act in allowed project scope.
4. A Strategy Copilot cannot call an approval endpoint with a draft/read delegation.
5. `tows_selection_limit` prevents a third active selection when the setting is two; a superseded selection preserves history.
6. A selected option produces Objective → no more than three published KRs → Initiatives → linked commitments/tasks, without auto-incrementing KR progress.
7. Mid-cycle review scheduling passes for cycles of 2, 6, 8, 10, 12 and 16 weeks; a resize changes unfinished scheduled reviews only.
8. A changed PESTEL signal, risk, resource constraint or KR variance makes a review packet actionable but does not itself pivot strategy.
9. Flutter never assumes a BSC unlock from a local project-stage fallback and never renders “week x / 12” for an N-week cycle.

## 9. Migration and rollout

The BSC/lens endpoints are currently unimplemented, so this is primarily additive and has no production lens data to migrate. Reuse existing Initiative, OKR, cycle, evidence and decision data; add nullable source links first, backfill only records whose workspace/project lineage is demonstrably valid, then enforce composite foreign keys.

Feature availability is per workspace. Initial rollout is `bsc_mode=OPTIONAL`, `strategy_method=BSC_FILTER`, selection limit one, agents draft-only and founder-only approvals. Delegated approver and additional agent profiles are enabled only by explicit workspace policy.

## 10. Non-goals

- AI does not autonomously change company strategy, publish OKRs or authorize external/financial actions.
- BSC does not become a second KPI store beside KR/metric contracts.
- Completing a task or Initiative does not itself mark a KR successful.
- This design does not rename `twelve_week_cycles`; N-week behavior remains behind its existing storage name.
