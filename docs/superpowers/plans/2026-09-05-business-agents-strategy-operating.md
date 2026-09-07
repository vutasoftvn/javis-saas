# Kế hoạch strategy, chu kỳ N tuần, OKR và weekly

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đóng F03/F10–F14; nối evidence→gate→decision→cycle→weekly→kết quả, giữ độ dài chu kỳ founder tự chọn.

**Architecture:** Giữ bảng và ID cycle/OKR hiện có, thêm liên kết và lịch sử bằng migration Expand. Company tính lịch/score/decision; Flutter chọn project/cycle rõ; agent tạo đề xuất và evidence qua tool có quyền.

**Tech Stack:** Encore/TypeScript/Drizzle, PostgreSQL, Flutter/GetX, Vitest/Flutter tests.

**Spec:** [07](/docs/architecture/overview/07-code-audit-business-agents-2026-09-05.md), [08](/docs/architecture/overview/08-phan-tich-cycle-cas-permissions-2026-09-05.md), [plan tổng](/docs/superpowers/plans/2026-09-05-business-agents-master.md).

## Global Constraints

- Kế thừa toàn bộ Global Constraints, Money/RuleDecision và lệnh test từ plan tổng; phụ thuộc A1, A2/A3 khi bật mutation mới.
- “Hết chu kỳ không tự động chuyển stage.”
- “Hoàn thành task không tự động làm KR đạt.”
- Không bắt discovery có OKR; cam kết có thể phục vụ experiment/obligation/BAU. Không dùng tài liệu để coi UI stub đã là tính năng thật.
- Không bắt tuần 13; không hard-limit N theo P-stage; N nguyên dương, nằm trong phạm vi integer của DB. Lịch tương lai tạo theo nhu cầu.

## S1 — Evidence hợp lệ, PMF đúng metric, gate gắn decision

**Files sửa:** [stage-lifecycle.service.ts](/services/company/operations/strategy/services/stage-lifecycle.service.ts), [pmf-scoreboard.service.ts](/services/company/operations/strategy/services/pmf-scoreboard.service.ts), [gate-evaluation.service.ts](/services/company/operations/strategy/services/gate-evaluation.service.ts), [decision-recording.service.ts](/services/company/operations/strategy/services/decision-recording.service.ts), [project-stage-lifecycle.service.ts](/services/company/operations/strategy/services/project-stage-lifecycle.service.ts), [strategy schema](/services/company/shared/db/schema/strategy.ts).

**Files tạo:** [eligible-evidence.service.ts](/services/company/operations/strategy/services/eligible-evidence.service.ts), [strategy-gate-integrity.test.ts](/services/company/operations/strategy/tests/strategy-gate-integrity.test.ts), [41_gate_decision_provenance.up.sql](/services/company/operations/migrations/41_gate_decision_provenance.up.sql).

**Interfaces:** `selectEligibleEvidence(ctx,{projectId?,at,requireApproved:true})` trả evidence có id/version/source/freshUntil và exclusion reasons. Dùng chung cho W-stage/PMF/project gate. `transitionProject` bổ sung decisionId/expectedStageVersion; service resolve decision→evaluation→policy/evidence snapshot cùng project/workspace. Không nhận requirementsMet=true từ caller làm bằng chứng.

- [ ] Viết test ma trận approved/candidate/rejected/expired/deleted; metric contract có/thiếu; cohort đúng/sai; edge allowed=false. Test PMF dùng production evaluator, không dựng outcome PROMISING trong fixture. Thêm helper pure trong file mới:

```ts
export function isEvidenceEligible(e: {
  status: string; deletedAt: Date | null; freshUntil: Date | null;
}, at: Date): boolean {
  return e.status === "approved" && e.deletedAt === null
    && (e.freshUntil === null || e.freshUntil.getTime() > at.getTime());
}
```

Canonical status literal phải đối chiếu enum đang dùng khi nối query; test lower/upper legacy qua adapter, không âm thầm chấp nhận chuỗi lạ.
- [ ] Chạy `DBTEST company operations/strategy/tests/strategy-gate-integrity.test.ts`; test candidate score cao phải FAIL trước sửa. Migration thêm provenance snapshot/version vào record hiện có, không tạo gate engine thứ hai.
- [ ] Lọc evidence trước khi tính missing flags. PMF dùng metric contract direction/unit/cohort/window và sample quality; missing contract hoặc zero approved evidence trả INSUFFICIENT_DATA, không clamp số bất kỳ về [0,1]. Không thay đổi metric raw value để phù hợp score.
- [ ] Transition transaction: resolve edge đúng version/effective date → kiểm allowed → kiểm decision/evaluation còn phù hợp stage version → CAS stageVersion → journal + outbox. `hold/kill/pivot` theo edge và decision tương ứng; không tự biến mọi quyết định thành proceed. Gate đã pass nhưng policy/evidence đổi thì yêu cầu đánh giá lại.
- [ ] Test replay chỉ một event, stale evaluation bị chặn, decision project A không dùng cho B; W-stage và P-stage không cập nhật lẫn nhau. Typecheck, boundaries, migration gates; commit `fix: bind stage transitions and pmf scoring to eligible evidence`.

## S2 — Lịch chu kỳ linh hoạt và đồng bộ kickoff có revision

**Files sửa:** [twelve-week-year.service.ts](/services/company/operations/services/twelve-week-year.service.ts), [weekly-goal.service.ts](/services/company/operations/strategy/services/weekly-goal.service.ts), [project-operating-setup.service.ts](/services/company/operations/strategy/services/project-operating-setup.service.ts), [project-kickoff-materialize.service.ts](/services/company/operations/strategy/services/project-kickoff-materialize.service.ts), [operations schema](/services/company/shared/db/schema/operations.ts), [twelve-week-year.handler.ts](/services/company/operations/handlers/twelve-week-year.handler.ts).

**Files tạo:** [execution-calendar.ts](/services/company/operations/services/execution-calendar.ts), [execution-cycle-calendar.test.ts](/services/company/operations/tests/execution-cycle-calendar.test.ts), [42_execution_cycle_calendar.up.sql](/services/company/operations/migrations/42_execution_cycle_calendar.up.sql).

**Schema:** cycle thêm display_name, timezone, start_local_date/end_local_date, revision, calendar_state READY/NEEDS_SETUP; stageDurationWeeks tách thành cycleDurationWeeks ở setup và giữ stageTargetDate riêng. Commitment/task thêm source_action_id, source_revision và revision nếu chưa có. Bảng cycle_revisions lưu before/after/reason/actor; unique(cycle_id,revision). Không rename twelve_week_cycles ở release này.

**Quy tắc lịch:** tuần thực thi là khối 7 ngày dân sự bắt đầu ở startLocalDate; founder chọn ngày bắt đầu, mặc định thứ Hai kế tiếp theo workspace timezone. `endLocalDateExclusive=start+7*N ngày`; API rõ end exclusive. Không cộng 168 giờ UTC để xác định tuần ở vùng DST. Weekly review workspace có lịch họp riêng và liên kết các weekly plan được review. Mặc định một cycle ACTIVE/project; dữ liệu cũ có nhiều ACTIVE phải founder chọn, không tự đóng bản ghi.

**Interfaces:** `resolveExecutionWeek(startLocalDate:string,durationWeeks:number,localDate:string): number|null`; outside cycle trả null. API cập nhật weekly goal bắt buộc cycleId+weekNo+expectedVersion; đường cũ chỉ tự suy ra khi đúng một ACTIVE READY cycle, không còn chọn newest.

- [ ] Viết test pure và DB: N=2/6/12/16, N=0/-1/1.5 bị chặn; trước bắt đầu/sau kết thúc null; ngày DST vẫn tuần đúng. Test mẫu:

```ts
expect(resolveExecutionWeek("2026-09-07", 6, "2026-09-14")).toBe(2);
expect(resolveExecutionWeek("2026-09-07", 6, "2026-10-19")).toBeNull();
```

- [ ] Chạy `DBTEST company operations/tests/execution-cycle-calendar.test.ts operations/strategy/tests/weekly-goal.test.ts`; RED xác nhận tuần 2 không còn được ghi vào tuần 1.
- [ ] Triển khai arithmetic ngày bằng date-only ordinal; timezone chỉ dùng chuyển instant→localDate qua Intl hỗ trợ IANA. Reject date không tồn tại bằng roundtrip YYYY-MM-DD. DURATION_LIMITS chỉ là stage guidance; không khóa cycleDurationWeeks. CreateWeeklyPlan kiểm tenant cycle, week range/date range, uniqueness; server tính ngày.
- [ ] Kickoff diff theo source_action_id: added tạo; changed cập nhật task còn draft/todo bằng expected revision, giữ assignee/progress; task đang làm/đã done tạo change request để founder chọn áp dụng tương lai. Removed archive/cancel công việc chưa bắt đầu, không xóa evidence/historical completion. Tránh dùng latest cycle khi chỉnh setup đã gắn cycleId.
- [ ] Backfill ngày từ dữ liệu đủ chắc; thiếu/mâu thuẫn→NEEDS_SETUP. Không tự gán ngày hôm nay để sửa lịch cũ. Test giữ action ID đổi “3”→“10” cập nhật draft task, done task giữ lịch sử. Cycle resize lưu revision, không sửa tuần đã chốt. Migration + tests pass; commit `feat: support configurable execution cycles with stable weekly history`.

## S3 — Liên kết KR và bằng chứng hoàn thành

**Files sửa:** [operations schema](/services/company/shared/db/schema/operations.ts), [okr.service.ts](/services/company/operations/services/okr.service.ts), [okr-scoring.service.ts](/services/company/operations/services/okr-scoring.service.ts), [twelve-week-year.service.ts](/services/company/operations/services/twelve-week-year.service.ts), [execution-plan.service.ts](/services/company/operations/services/execution-plan.service.ts).

**Files tạo:** [execution-outcome.service.ts](/services/company/operations/services/execution-outcome.service.ts), [kr-observation.service.ts](/services/company/operations/services/kr-observation.service.ts), [execution-outcome.test.ts](/services/company/operations/tests/execution-outcome.test.ts), [43_execution_outcomes.up.sql](/services/company/operations/migrations/43_execution_outcomes.up.sql).

**Schema:** cycle_key_results(workspace_id,cycle_id,key_result_id) unique triple; commitment_key_results tương tự; commitment owner_member_id, purpose_type KR/EXPERIMENT/OBLIGATION/BAU, purpose_ref, done_criteria JSON có schema, committed_at, revision. kr_observations UUID, workspace,kr_id,value_decimal,measurement_at,window_start/end,evidence_refs,source_ref,recorded_by,metric_contract_version,idempotency_key unique theo source/kr. Baseline chưa có thì NULL/NEEDS_BASELINE, không suy ra 0. KR thêm scoring_type LINEAR_INCREASE/LINEAR_DECREASE/MILESTONE/RANGE và contract version. Dùng native NUMERIC/string cho observation, không Number cho monetary KR.

**Interfaces:** `computeLinearProgress({baseline,target,current}): number|null` cho tỷ lệ vô hướng; `recordKrObservation(ctx,input)` append-only và cập nhật current projection trong transaction; `validateTaskCompletion(ctx,{taskId,expectedVersion,evidenceRefs})` đánh giá done criteria và tạo completion event. Model không được set accepted=true.

- [ ] Viết test core và DB: baseline/giảm/missing/target=baseline, evidence stale, zero commitment (score null), mục tiêu không đạt dù mọi task done. Mẫu:

```ts
expect(computeLinearProgress({baseline:10,target:5,current:8})).toBeCloseTo(0.4);
expect(computeLinearProgress({baseline:100,target:200,current:150})).toBeCloseTo(0.5);
expect(computeLinearProgress({baseline:5,target:5,current:5})).toBeNull();
```

- [ ] Chạy `DBTEST company operations/tests/execution-outcome.test.ts operations/tests/okr-scoring.test.ts`; cập nhật test cũ chỉ khi thay semantics được mô tả rõ: target attainment và progress from baseline là hai trường khác nhau.
- [ ] Triển khai linear core `Math.max(0,Math.min(1,(current-baseline)/(target-baseline)))` sau finite/direction checks; MILESTONE dựa milestone accepted; RANGE trả status in/out theo window, không dùng công thức linear. Projection phải chọn observation mới nhất theo measurement time và source precedence, late observation không rollback current tùy tiện.
- [ ] Execution score = cam kết hoàn tất đủ evidence / cam kết đã chốt đầu tuần; mặc định trọng số bằng nhau. Thay scope sau chốt tạo revision; carry-over tạo cam kết mới link bản cũ, không đổi denominator lịch sử. Outcome score đọc KR progress/evidence freshness; override score/target cần quyền và reason, lưu revision.
- [ ] Test một KR qua hai cycle không nhân đôi observation/progress; một task link nhiều KR không tự increment KR; owner cùng workspace; no-KR discovery hợp lệ. Test concurrent observation idempotency. Gates + commit `feat: link weekly commitments to measured outcomes and completion evidence`.

## S4 — Action context thật và quyết định tạo kế hoạch

**Files sửa:** [next-best-action.handler.ts](/services/company/operations/strategy/handlers/next-best-action.handler.ts), [next-best-action.service.ts](/services/company/operations/strategy/services/next-best-action.service.ts), [weekly-review.service.ts](/services/company/operations/strategy/services/weekly-review.service.ts), [decision-recording.service.ts](/services/company/operations/strategy/services/decision-recording.service.ts), [strategy schema](/services/company/shared/db/schema/strategy.ts).

**Files tạo:** [project-action-context.service.ts](/services/company/operations/strategy/services/project-action-context.service.ts), [project-action-context.test.ts](/services/company/operations/strategy/tests/project-action-context.test.ts), [44_review_decision_links.up.sql](/services/company/operations/migrations/44_review_decision_links.up.sql).

**Consumes:** S1 gate provenance, S2 cycle/week, S3 outcome; L1 open obligations contract; F6 budget summary khi đã có. Trước F6 cash/budget adapter trả unavailable có reason, không sinh số mẫu.

**Produces:** `getProjectActionContext(ctx,projectId)` gồm assumptions/evidence/metrics/stage/currentCycle/currentWeek/openObligations/cashSummary/budgetSummary, mỗi phần có availability/sourceVersion/asOf; `proposeNextActions(ctx,projectId)` trả actions hoặc INSUFFICIENT_DATA. `acceptActionProposal` nhận expectedVersion/cycleId/weekNo, ghi decisionId vào plan/commitment và outbox transaction.

- [ ] Seed hai project có assumption khác nhau qua helper/DB fixture; gọi service thật kiểm action thay đổi theo context. ID `9007199254740993` phải giữ string. Test không có assumption trả thiếu dữ liệu thay cho assumption id=1.
- [ ] Chạy `DBTEST company operations/strategy/tests/project-action-context.test.ts`; RED xác nhận handler mẫu không qua. Implement typed source envelope:

```ts
export type ContextPart<T> =
  | { availability: "READY"; data: T; asOf: string; sourceVersion: string }
  | { availability: "UNAVAILABLE"; reason: string };
```

- [ ] Handler chỉ auth/parse/service; service resolve project scope, read assumptions thật và L1 listOpenObligations. Tạo kế hoạch từ proposal phải chốt scope/week/owner, không auto activate stage. Weekly review tổng hợp link nhiều weeklyPlanId và decisionIds; complete không sửa bản COMPLETED, cần revision review bổ sung.
- [ ] Test obligations OPEN xuất hiện, cash unavailable không trở thành cash=0, context stale nêu lý do; accept replay không nhân bản commitment. Giữ tenant guard A1. Typecheck/boundaries + commit `feat: build strategy actions and reviews from live business context`.

## S5 — Flutter cycle/OKR/weekly persistence xuyên màn hình

**Files sửa:** [twelve_wy_service.dart](/frontend/lib/modules/strategy/services/twelve_wy_service.dart), [twelve_week_service.dart](/frontend/lib/modules/strategy/services/twelve_week_service.dart), [okr_service.dart](/frontend/lib/modules/strategy/services/okr_service.dart), [twelve_wy_state_mixin.dart](/frontend/lib/modules/strategy/controllers/mixins/twelve_wy_state_mixin.dart), [okr_state_mixin.dart](/frontend/lib/modules/strategy/controllers/mixins/okr_state_mixin.dart), [project_kickoff_controller.dart](/frontend/lib/modules/strategy/controllers/project_kickoff_controller.dart), [twelve_wy_modals.dart](/frontend/lib/modules/strategy/widgets/twelve_wy/twelve_wy_modals.dart), [twelve_wy_governance_dialog.dart](/frontend/lib/modules/strategy/widgets/twelve_wy/twelve_wy_governance_dialog.dart), [twelve_week_year_view.dart](/frontend/lib/modules/strategy/views/twelve_week_year_view.dart), [weekly_review_tab.dart](/frontend/lib/modules/strategy/views/tabs/weekly_review_tab.dart), [mvp_strategy_models.dart](/frontend/lib/modules/strategy/models/mvp_strategy_models.dart), [mvp-surface.json](/shared/contracts/mvp-surface.json).

**Files test:** sửa [twelve_wy_service_test.dart](/frontend/test/modules/strategy/services/twelve_wy_service_test.dart); tạo [execution_cycle_flow_test.dart](/frontend/test/modules/strategy/execution_cycle_flow_test.dart). Backend tạo [execution-cycle-view.service.ts](/services/company/operations/services/execution-cycle-view.service.ts) và [execution-cycle-view.handler.ts](/services/company/operations/handlers/execution-cycle-view.handler.ts).

**API mới/adapter:** GET `/operations/execution-cycle-view?projectId=...&cycleId=...` trả cycle, currentWeek|null, weeklyPlans, commitments, linkedKrs, executionScore, outcomeProgress, dataIssues, allowedActions. Các đường CRUD cycle/weekly hiện có giữ route và thêm version/scope; chỉ nối route legacy nếu có caller còn thật, không dựng backend cho mọi URL cũ đã chết. Tên mới là presentation, không phải migration đổi tên bảng.

```json
{"cycle":{"id":"501","displayName":"Tìm 5 pilot","durationWeeks":6,
 "startLocalDate":"2026-09-07","endLocalDateExclusive":"2026-10-19",
 "timezone":"Asia/Ho_Chi_Minh","revision":1},"currentWeek":2,
 "executionScore":0.8,"outcomeProgress":0.4,"dataIssues":[],"allowedActions":["weekly.plan.edit"]}
```

- [ ] Test service create/update/review phải gọi HTTP và dùng server id; reload project A không hiện cycle B. Không giữ test kỳ vọng timestamp ID/null như thành công. Chạy FLUTTER cho hai file trên để xác nhận RED.
- [ ] Implement DTO score nullable, cycle/week identity, dataIssues; controller loading/empty/needsSetup/error/ready, reject stale response nếu người dùng đã đổi project. Save dùng expectedVersion, conflict giữ edit draft và reload offer inline.
- [ ] UI tên “Chu kỳ thực thi”, tên tùy đặt/N tuần; preset chỉ gợi ý; stage deadline riêng. Chọn KR hoặc experiment/obligation/BAU; hiển thị execution và outcome hai số riêng kèm freshness. Review cuối chu kỳ dùng ngày thật; nghỉ là lựa chọn; bỏ copy tuần 13 bắt buộc.
- [ ] Test widget keys và kết quả server:

```dart
expect(find.text('Tuần 2 / 6'), findsOneWidget);
expect(find.textContaining('Tuần 13 là bắt buộc'), findsNothing);
expect(find.byKey(const ValueKey('cycle-save-error')), findsNothing);
```

Test thêm save 500 hiện cycle-save-error, không báo đã lưu; legacy NEEDS_SETUP cho founder bổ sung lịch, không tự tạo cycle rỗng.
- [ ] Regenerate contracts, frontend contract gate, typecheck Company, Flutter analyze và existing mixin/weekly tab tests. Commit `feat: persist configurable cycles okrs and weekly reviews in Flutter`.

**Nghiệm thu toàn plan:** F03/F10–F14 có regression; 2/6/12/16 tuần end-to-end; một KR nhiều cycle; không đổi lịch sử khi sửa kickoff/target; review dựa evidence thật và permission thật. Mọi transition cần policy/evidence hợp lệ, không bị calendar tự kích hoạt.
