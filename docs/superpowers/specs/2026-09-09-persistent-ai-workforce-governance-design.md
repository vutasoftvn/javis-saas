# Persistent AI Workforce, Task Outcome & Skill Governance — Design

Ngày: 2026-09-09
Trạng thái: Approved — consolidated product/design specification

## 1. Mục tiêu

Biến AI workforce từ tập agent spec/run tạm thời thành các **AI employee bền vững
theo workspace**, có thể nhận nhiều phần việc từ nhiều manager, được founder điều
phối, có scorecard và có audit đầy đủ.

Mọi task phải có một **Outcome Contract** ngay khi được tạo để trả lời được: task
phục vụ kết quả nào, liên quan Key Result (KR) nào, cần bằng chứng nào, và làm
cách nào để đánh giá kết quả sau khi thực hiện. Outcome Analysis là bước đối
chiếu kết quả thực tế với contract; nó không thay thế contract và không được suy
đoán từ văn bản tự do.

"AI employee" là identity vận hành có lifecycle, quyền, scorecard và audit; không
phải khái niệm nhân sự/pháp lý. Thiết kế không cho LLM tự cấp quyền, tự hoàn tất
task hoặc tự sửa chính nó.

## 2. Quyết định sản phẩm đã chốt

1. AI employee là identity cố định trong một workspace, có agent_instance_id
   không tái sử dụng.
2. Nhiều manager được giao/reassign việc cho AI employee trong phạm vi quyền;
   founder là người điều phối cuối cùng về priority, hold, cancel, reassign,
   exception và delegation.
3. Một task có thể chia nhiều work package. Một attempt chỉ có một AI employee;
   reassign tạo attempt mới và giữ nguyên lịch sử cũ.
4. Mọi task tạo mới phải đồng thời có Outcome Contract version đầu tiên. DRAFT
   chỉ dành cho AI proposal hoặc input chưa đủ điều kiện. Manager/founder tạo
   trực tiếp với contract hợp lệ, hoặc xác nhận AI proposal, phải tạo queue entry
   trong cùng transaction; không dừng ở DRAFT/TODO trung gian.
5. Mọi task phải có outcome type. Task phục vụ chiến lược liên kết ít nhất một
   KR; task BAU vẫn có contract nhưng liên kết service objective/SLO thay vì KR.
6. Task Outcome Analysis là skillpack tái sử dụng cho **mọi task**. P0 không giới
   hạn phạm vi; P0 chỉ tăng độ sâu, SLA, priority và escalation.
7. Mặc định workspace là AUTO_ALL_TASKS: mỗi task result revision hợp lệ tạo một
   yêu cầu phân tích. Founder có thể chuyển policy có audit sang AUTO_BY_RULE
   hoặc MANUAL, không được sửa thầm lịch sử.
8. Outcome Analyst là AI employee cố định, ví dụ Project Outcome Analyst #1. Nó
   chạy AgentSpec đã pin skill/version và capability hẹp. Các AI employee khác
   không tự nhận công việc này chỉ vì nhìn thấy tool hay task.
9. Manager review là điều kiện để kết quả được chấp nhận. Analysis chỉ cung cấp
   evidence/risk/proposal; không tự accept task, đổi stage hoặc cập nhật KR.
10. Founder quản trị Skill Governance trên UI bằng draft/version/evaluation/
    publish/rollback. Không có chỉnh sửa live raw prompt, model hoặc capability
    làm thay đổi một run đang chạy.

## 3. Bối cảnh đã xác minh và khoảng trống

Hiện Agent Platform có RunRecord, spec/version/hash, checkpoint, tool-call ledger
và approval ledger. Workforce có assignment_id, functional_key và
reports_to_assignment_id. Chúng không thay thế AI employee identity:

- agent_spec_id là definition có version/hash, không phải nhân sự.
- run_id là một lần thực thi.
- assignment_id là vị trí/cấu hình theo thời gian.
- Task, KR và review là business truth của Company Plane; Agent Platform không
  ghi trực tiếp business database.

Company Task hiện có thể liên kết initiativeId, nhưng create contract chưa có
trường expected outcome, evidence hay KR attribution. Kickoff hiện có outcome
tuần đầu và action, nhưng action materialize thành task chỉ với title/commitment
và chưa có contract outcome riêng. Initiative có intendedOutcome và liên kết
nhiều KR, nhưng không đủ để audit đóng góp của từng task.

Skillpack và AgentSpec là hai khái niệm riêng: skillpack có lifecycle pending →
adapted → published → pinned/retired; AgentSpec pin exact skill id, version và
definition hash. AgentSpec built-in hiện author bằng code và resolve exact hash
khi run, vì vậy UI v1 không được giả vờ có quyền sửa trực tiếp static AgentSpec
trong production.

## 4. Ngôn ngữ chung và ownership

| Khái niệm | Ý nghĩa | Nguồn sự thật |
|---|---|---|
| AI employee | Nhân sự AI cố định, lifecycle và scorecard | Agent Platform |
| Assignment | Vai trò/spec/capability của employee trong effective period | Agent Platform |
| Skillpack | Phương pháp tái sử dụng có input/output contract và version | Agent Platform registry |
| Capability | Hành động read/write được policy kiểm soát | Capability Gateway + Company |
| Outcome Contract | Cam kết trước khi làm của một task | Company Plane |
| Task Result | Kết quả/evidence nộp theo version | Company Plane |
| Outcome Assessment | Phân tích AI đối với một result revision | Company Plane, qua capability hẹp |
| KR Contribution | Nhận định đóng góp có trạng thái review | Company Plane |
| Work package/attempt | Phần việc và lần thực thi có một owner AI | Company Plane |

| Context | Nguồn sự thật | Chịu trách nhiệm |
|---|---|---|
| AI employee, assignment, spec pin, capability boundary | Agent Platform (agent schema) | execution identity/lifecycle |
| Task, Outcome Contract, result, KR link, package, review | Company Plane (operating schema) | business workflow/audit |
| Run, checkpoint, tool call, approval | Agent Platform | execution/governance evidence |
| Queue/lease | Company outbox → Agent worker | signed dispatch, capacity |
| Scorecard/read model | Agent Platform, derived từ evidence được review | observability, không phải business truth |

Cross-plane references là opaque IDs; không có foreign key liên database. Company
xác minh employee/assignment/capability server-to-server trước queue. Agent chỉ
gọi Company bằng delegation ngắn hạn scope workspace, run và capability IDs.

## 5. Identity, assignment và quyền

### 5.1 AI employee

agent.workforce_employees có identity immutable và status mutable:

~~~
agent_instance_id       UUID/ULID, stable, never reused
workspace_id            tenant key
employee_code           unique per workspace, e.g. AGT-OUT-001
display_name            Project Outcome Analyst #1
status                  ACTIVE | SUSPENDED | RETIRED
created_by              founder principal
created_at, suspended_at, retired_at
~~~

Suspend/retire chặn lease mới, nhưng không xoá run, contract, attempt, review hay
scorecard. Display name không là authority.

### 5.2 Assignment

Assignment liên kết agent_instance_id với functional role, manager tree,
spec/version/hash, pinned skills, capability boundary, model/cost policy và
effective window. Thay prompt/model/tool/capability/role tạo revision hoặc
assignment mới; run lịch sử giữ snapshot đã pin.

Run workforce bắt buộc carry agent_instance_id, assignment_id, work_package_id,
work_attempt_id, spec/version/hash và pinned skill refs.

### 5.3 Quyền

| Chủ thể | Được làm | Không được làm mặc định |
|---|---|---|
| Founder | lifecycle employee; effective priority; hold/cancel/reassign; skill publish/rollback; delegate Evaluation Owner; emergency exception | sửa/xóa audit history; auto-accept ngầm |
| Manager | tạo/sửa draft contract; xác nhận contract; tạo/reassign package; review result; yêu cầu reanalysis | đổi founder priority; publish skill/capability; cập nhật KR actual không review |
| Evaluation Owner | đọc scorecard; tạo improvement proposal; chạy evaluation trong scope được cấp | tự promote capability/model/prompt risk cao |
| Outcome Analyst | đọc input có scope; ghi assessment gắn exact run/result revision | advance task; review thay người; cập nhật KR; tạo/reassign task/package; external write |

Founder delegation phải explicit, revocable, scoped theo action + functional key
hoặc principal và append-only audit. Manager chỉ thấy employee/work package có
liên quan quyền được giao.

## 6. Outcome Contract — bắt buộc khi tạo task

### 6.1 Tạo nguyên tử và queue gate

Task và TaskOutcomeContract v1 được tạo trong cùng Company transaction. DRAFT là
trạng thái của **AI proposal** hoặc input không đủ chuẩn, không phải default cho
mọi task. Luồng tạo được phân biệt rõ:

| Nguồn/lệnh | Điều kiện | Kết quả nguyên tử |
|---|---|---|
| AI proposal | AI đề xuất task/contract; chưa có manager/founder confirmation | Proposal DRAFT, không có lease/queue |
| Manager/founder create | Contract, assignee, priority, budget và dependency hợp lệ | Task + CONFIRMED contract + initial work package QUEUED |
| Confirm AI proposal | Manager/founder xác nhận hoặc chỉnh contract hợp lệ | Materialize/activate task + CONFIRMED contract + initial work package QUEUED |

Nếu dependency chưa thỏa, package vẫn là một queue entry có dependency rõ ràng và
scheduler không lease cho đến khi thỏa. Nếu thiếu assignee, budget hoặc capability
thì command từ chối rõ ràng; không tạo một task "đã xác nhận" nhưng không biết ai
chịu trách nhiệm. UI hiển thị Outcome required chỉ với proposal/input chưa đủ;
title task không tự trở thành outcome.

Emergency task chỉ được bypass bởi founder/delegate có quyền, với exception reason,
actor, expiry và event. Nó được queue có expiry audit; khi exception hết hạn,
scheduler hold package nếu contract chưa được bổ sung.

### 6.2 Nội dung contract

~~~
contract_id, task_id, workspace_id, revision, status
outcome_type                DIRECT_KR | ENABLING_KR | VALIDATION | BAU
expected_outcome            kết quả cụ thể, không chỉ là hoạt động
acceptance_criteria         structured rubric/checklist
expected_evidence_refs      evidence/artifact cần nộp
measurement_plan            baseline, target, unit, measured_at nếu áp dụng
impact_hypothesis           task dự kiến tác động vì sao
primary_kr_link_id          bắt buộc với task strategic
created_by, confirmed_by, confirmed_at
supersedes_contract_id, change_reason, created_at
~~~

task_outcome_kr_links ghi một KR chính và các KR phụ có relation type DIRECT,
ENABLING hoặc VALIDATION. Không dùng numeric weight để tự cộng tiến độ KR trong
v1. Khi task được tạo qua Initiative, UI prefill các KR của Initiative, nhưng
manager phải xác nhận link cụ thể của task. Non-BAU task chỉ hợp lệ khi Initiative
đã được governance phê duyệt; BAU có service objective hoặc SLO thay primary KR.

### 6.3 Bốn loại outcome

| Type | Kỳ vọng bắt buộc | Cách audit |
|---|---|---|
| DIRECT_KR | metric/baseline/target và evidence nguồn | đo thay đổi; không tự ghi KR actual |
| ENABLING_KR | deliverable/proof là prerequisite | kiểm tra prerequisite và impact hypothesis |
| VALIDATION | câu hỏi, evidence threshold, quyết định cần ra | đánh giá evidence/decision, không giả mạo metric move |
| BAU | SLO/service outcome và evidence vận hành | đánh giá SLA/chất lượng; không ép gắn KR |

Ví dụ, “phỏng vấn 10 khách hàng” có thể là VALIDATION: outcome là 10 interview
records, kết luận có evidence và quyết định tiếp theo; nó không tự nhận đã tăng
doanh thu/KR.

### 6.4 Revision và bất biến audit

Thay đổi scope, KR link, metric, criteria hoặc evidence sau khi CONFIRMED tạo
TaskOutcomeContract revision mới, liên kết supersedes_contract_id và bắt buộc
change_reason. Result/assessment cũ vẫn trỏ contract revision cũ. Không có
update in-place làm mất chuẩn so sánh ban đầu.

## 7. Work package, attempt và queue

operating.task_work_packages thuộc task_id:

~~~
work_package_id, task_id, workspace_id
title, objective, input_refs, output_contract, acceptance_rubric
requested_by_manager_id, assigned_agent_instance_id
requested_priority, effective_priority, priority_reason
status, dependency_ids, review_due_at, budget_limit, version
~~~

Mỗi package phải tham chiếu contract revision hiện hành và khai báo phần outcome
nó chịu trách nhiệm. Một package là đơn vị queue; một attempt là đơn vị quy trách
nhiệm. Không có hai active attempt cho cùng package.

~~~
DRAFT → QUEUED → LEASED → RUNNING → VALIDATION_PASSED
                                    → BLOCKED | CANCELLED
VALIDATION_PASSED → PENDING_MANAGER_REVIEW
PENDING_MANAGER_REVIEW → ACCEPTED | REWORK | REJECTED | ESCALATED_TO_FOUNDER
ESCALATED_TO_FOUNDER → ACCEPTED | REWORK | REJECTED | PENDING_MANAGER_REVIEW
REWORK → QUEUED (attempt mới)
~~~

Manager tạo package hợp lệ đi thẳng vào queue. Scheduler dùng effective priority
→ deadline/SLA → dependencies → budget → employee capacity → queued_at. Founder
override chỉ tạo event, không ghi đè requested priority. Reassign khi run đang
chạy thành reassignment_requested và chỉ áp dụng tại checkpoint an toàn.

Task không được coi completed chỉ vì agent gọi finish: mọi package bắt buộc được
review theo policy, result phải có evidence, và task outcome phải được đánh giá
theo contract.

## 8. Result, Outcome Assessment và KR contribution

### 8.1 Task Result

Agent hoặc human nộp TaskResult append-only theo revision:

~~~
task_result_id, task_id, contract_id, result_revision
submitted_by_kind, submitted_by_id, work_attempt_refs
summary, structured_outputs, artifact_refs, evidence_refs
claimed_measurements, blockers, submitted_at
~~~

Kết quả phải reference exact Outcome Contract revision. Rework/nộp lại tạo result
revision mới; không overwrite result/evidence trước đó.

### 8.2 Task Outcome Analysis

Mỗi result revision hợp lệ phát task.result.submitted.v1. Policy router xác định,
không phải LLM, tạo OutcomeAnalysisRequest idempotent theo workspace, task result,
analysis kind và contract revision, rồi queue cho Outcome Analyst cấu hình.

~~~
Task Result submitted
→ deterministic policy router
→ OutcomeAnalysisRequest QUEUED
→ Project Outcome Analyst #1 / pinned skill run
→ OutcomeAssessment READY | FAILED | SUPERSEDED
→ manager review of result + assessment
→ optional KR contribution review
~~~

analysis_kind tối thiểu gồm TASK_OUTCOME. PROJECT_OUTCOME_SYNTHESIS là workflow
tổng hợp theo milestone/tuần/dự án, không thay thế phân tích task. Một employee
có thể chạy cả hai ở v1, nhưng metric/capacity/scorecard phải tách theo analysis
kind.

~~~
assessment_id, request_id, task_result_id, contract_id
agent_instance_id, assignment_id, run_id
skill_id, skill_version, definition_hash, rubric_version
evidence_used_refs, missing_evidence_refs
expected_vs_actual, criterion_scores, confidence
risk_flags, causal_limits, next_action_proposals
recommendation = ACCEPT | REWORK | REJECT | NEEDS_HUMAN_DECISION
created_at, superseded_by_result_revision
~~~

Recommendation không làm state transition. Manager phải quyết định ACCEPT, REWORK
hoặc REJECT; review quá SLA escalates founder và không auto-accept.

### 8.3 KR contribution không tự động

Assessment có thể đề xuất KRContributionAssessment:

~~~
kr_contribution_id, assessment_id, kr_link_id
state = PROPOSED | VERIFIED | REJECTED | INSUFFICIENT_EVIDENCE
claimed_effect, evidence_refs, causal_confidence
verified_by, verified_at, reason
~~~

Chỉ manager/founder có thẩm quyền xác minh mới đưa contribution vào KR review.
Không task/agent/skill nào tự cập nhật KR.actualValue hoặc nhận công cho metric
không có nguồn đo. Dashboard hiển thị rõ proposed khác verified.

## 9. Skillpack và deterministic dispatch

### 9.1 Skillpack không phải employee hoặc tool

operations/task-outcome-analysis là skillpack versioned có input/output schema,
rubric và evaluation set. Nó được pin vào AgentSpec của Outcome Analyst; không
được gắn global vào mọi agent/tool prompt.

| Lớp | Câu hỏi trả lời |
|---|---|
| AI employee | Ai chịu trách nhiệm thực hiện? |
| Assignment/AgentSpec | Nó chạy với role, model, spec nào? |
| Skillpack | Phương pháp Outcome Analysis là gì? |
| Capability | Nó được phép đọc/ghi hành động nào? |
| Policy router | Khi nào và cho employee nào tạo run? |

Policy router resolve exact employee/assignment/spec/skill snapshot trước queue.
Không có rule kiểu “agent thấy task thì tự quyết định chạy analysis”. Retry reuse
idempotency key; result revision hoặc contract revision mới mới tạo request mới.
Một contract/result superseded làm assessment cũ visible với status SUPERSEDED,
không bị xoá.

### 9.2 Capability boundary

Tên capability là target contract, cần đăng ký chính thức trước runtime:

~~~
Allow: operations.task.read
       operations.task-result.read
       operations.work-package.read
       operations.evidence.read
       agent.artifact.read
       operations.outcome-assessment.record  (narrow append/upsert by request)

Deny:  operations.task.advance
       operations.task.create
       operations.project.stage.transition
       operations.kr.actual.write
       external.send
       finance.*.write
~~~

operations.outcome-assessment.record server-verify exact delegated workspace,
run, request, result revision và agent assignment. Nó không chấp nhận arbitrary
task ID từ model text.

### 9.3 Policy và mức phân tích

Workspace policy mặc định AUTO_ALL_TASKS. Founder có audit option:

| Policy | Hành vi |
|---|---|
| AUTO_ALL_TASKS | mọi result revision hợp lệ tạo assessment |
| AUTO_BY_RULE | rule versioned theo outcome type, priority, risk, budget hoặc project template |
| MANUAL | manager/founder tạo request rõ ràng |

P0 dùng depth DEEP, SLA ngắn, queue priority cao và founder escalation khi thiếu
evidence/risk. P1/P2 dùng STANDARD; BAU/P3 có thể LIGHT. Mọi depth vẫn dùng cùng
data contract và audit fields, không có task “không outcome”.

## 10. Skill Governance UI

Founder có surface riêng **AI Workforce → Skill Governance**, tách khỏi AI
Employee Profile và Task Detail.

### 10.1 Founder thấy và quản trị gì

- Catalog: skill name, purpose, owner, lifecycle, current/published/pinned
  version, definition hash và compatibility.
- Scope: AUTO_ALL_TASKS/policy; project template, task type, outcome type,
  depth, SLA, budget/capacity và escalation rule.
- Binding: AI employee/assignment nào được phép thực thi; fallback chỉ khi
  founder policy nói rõ và có audit.
- Input/output: rubric, evidence requirements, proposal schema và evaluation
  datasets; không expose credential hoặc prompt secret.
- Capability matrix: allow/deny, lý do và effective version.
- Quality: acceptance/rework rate, evidence coverage, agreement với manager,
  false escalation, cost/latency, tách theo skill/spec/employee/depth.
- Governance: draft, evaluation results, approver, publish time, canary cohort,
  rollback và changelog.

Manager nhìn scope/version áp dụng cho task, thấy assessment, có thể request
reanalysis hoặc đề xuất skill improvement. Manager không đổi global scope, publish
version, capability hoặc employee binding nếu founder chưa delegate.

### 10.2 Thay đổi an toàn

Founder không edit production version tại chỗ. UI tạo DRAFT gồm changed field,
hypothesis, risk/cost impact, eval cohort và rollback plan. Chỉ version PUBLISHED
qua validation capability/schema + evaluation mới được pin cho run mới.
Capability write, autonomy, model/provider cost limit hoặc rollout toàn workspace
cần founder approval rõ ràng. Rollback đổi policy/version cho request mới, không
viết lại run/assessment cũ.

Trong v1, UI quản trị configuration của built-in skillpack. Authoring raw
AgentSpec/prompt runtime phải đi qua registry/release pipeline có validation; nếu
pipeline chưa implemented, UI chỉ tạo proposal/draft và không hiển thị như thay
đổi đã có hiệu lực.

## 11. UI nghiệp vụ và badges

### 11.1 Task Detail

Task Detail có các section theo thứ tự audit:

~~~
Why this task?        Initiative / KR links / impact hypothesis
Expected outcome      Outcome Contract revision + criteria + evidence required
Work                  work packages / attempts / queue priority
Actual result         Task Result revisions + artifacts/evidence
AI assessment         status, evidence gaps, recommendation, confidence
Manager decision      accept/rework/reject and reason
KR contribution       proposed/verified/rejected, never inferred as actual
~~~

Badge là read model, không là authority:

~~~
Outcome required | Contract confirmed | Evidence missing | Analysis queued
Analysis ready | Analysis failed | Manager review required | KR proposed
KR verified | Contract/result superseded | Founder escalation
~~~

### 11.2 Founder Hub và dashboards

- Queue Board: requested/effective priority, override reason, dependency,
  capacity, contract completeness và analysis state.
- Manager Review Inbox: artifact/result/assessment side by side, SLA, decision.
- AI Employee Profile: workload, attempts, accepted/rework/rejected work,
  pinned spec/skill history và scorecard.
- Skill Governance: catalog/version/eval/rollout/capability matrix.
- KR/Project dashboard: task lineage, verified versus proposed contribution,
  evidence coverage và outcome-risk rollup. Không cộng metric từ unverified
  proposal.

UI phải render riêng unavailable, forbidden, not configured, pending và empty;
không suy diễn state từ zero/null hoặc tự hiển thị task finished.

## 12. Audit, scorecard và cải tiến có kiểm soát

Mọi command, contract revision, result, request, assessment, review, priority
override, capability/publish change đều có event append-only với actor, principal
kind, correlation ID, timestamp, before/after, reason và exact version references.
Không đưa credential/raw confidential prompt/delegation token vào event/UI.

Scorecard AI employee chỉ tính result đã manager/founder review và tách theo
agent_instance_id, assignment, spec hash, skill version, outcome type, analysis
depth, work package type và time window. Metrics gồm acceptance/rework, quality
rubric, evidence coverage, SLA, retry, cost, manager agreement và false
escalation. Không tạo global rank cho agent khác scope/rubric.

Manager scorecard gồm review latency/SLA, brief ambiguity, rework attribution,
review consistency và tỷ lệ contribution bị later invalidated. Evaluation Owner
tạo improvement proposal từ cohort/evidence; proposal không tự thay skill/model
hay quyền.

## 13. Authorization, tenancy và integrity invariants

1. Server derive workspace/principal/role từ authenticated identity; client không
   cung cấp workspace/owner/role trusted.
2. Mọi lookup, contract/result/assessment/review/employee event đều tenant-scope.
3. State command có idempotency key + optimistic/CAS version; duplicate event/retry
   không tạo active attempt, lease hoặc assessment duplicate.
4. Task Result, Outcome Assessment, review và contribution reference exact
   contract/result/assignment/spec/skill version. Cross-workspace IDs bị reject.
5. Agent không submit human review, đổi priority, complete task hay write KR.
6. Manager/founder decision bind artifact/result revision; review không sửa im
   lặng, bản mới links supersedes_review_id.
7. Approval risky tool call bind run_id + tool_call_id + checkpoint_ref; không
   lookup theo tên action hoặc LLM text.

## 14. Migration và rollout

1. Expand-only migrations: employee identity/assignment linkage; Outcome Contract
   + KR links; task result; analysis request/assessment/contribution; package,
   attempt/review/event. Có down migration cho toàn bộ object mới.
2. Backfill task lịch sử với legacy_missing_contract; không bịa expected outcome
   hay KR attribution. UI hiển thị cần remediation; policy chỉ bắt buộc với task
   tạo mới trước.
3. Backfill employee deterministic từ active assignment; run cũ thiếu evidence là
   legacy_unattributed, không dùng làm scorecard so sánh.
4. Deploy read models/UI dưới flags: TASK_OUTCOME_CONTRACT_ENABLED,
   TASK_OUTCOME_ANALYSIS_ENABLED, AI_WORKFORCE_V2_ENABLED, mặc định false.
5. Pilot một workspace với AUTO_ALL_TASKS, budget cap và rollback. Chỉ enable
   dispatch/queue sau PostgreSQL/process E2E thực. Existing WGA path giữ nguyên
   đến khi hardening độc lập được chứng minh.
6. Rollback bằng disable policy/dispatch cho request mới; không xóa contract,
   result, assessment, review, event hay scorecard history.

## 15. Non-goals

- Không để agent tự thay model/prompt/tool/capability hay tự chọn role.
- Không tự cộng/cập nhật actual KR dựa trên LLM assessment.
- Không cho concurrent free-form execution của nhiều agent cùng một work package.
- Không có global cross-workspace AI identity/rank hoặc diễn giải legal employment.
- Không thay human approval/capability governance bằng prompt hoặc badge UI.

## 16. Acceptance evidence

Không coi lint/unit mock là đủ. Disposable PostgreSQL + process E2E phải chứng
minh tối thiểu:

1. AI proposal có contract DRAFT và không queue; manager/founder create trực tiếp
   hoặc confirm proposal atomically tạo CONFIRMED contract + queued package; task
   thiếu contract không queue; founder emergency exception có expiry/audit; legacy
   task không bị bịa contract.
2. Non-BAU task chỉ confirm khi Initiative/KR đúng workspace và policy approved;
   BAU có SLO; foreign workspace không đọc/sửa được chain này.
3. Result revision tạo đúng một TASK_OUTCOME request trong AUTO_ALL_TASKS;
   duplicate delivery/retry không duplicate run/assessment; rework tạo revision
   mới và assessment cũ SUPERSEDED.
4. Router dispatch đúng Outcome Analyst/assignment/spec/skill hash; agent khác
   hoặc request thiếu capability không thể tự gọi analysis hay ghi assessment.
5. Outcome Analyst chỉ đọc permitted evidence và narrow-record assessment; mọi
   attempt advance task, write KR, external write đều bị deny.
6. Manager review mới có thể accept/rework/reject; overdue escalates founder và
   không auto-accept. Assessment recommendation không tự đổi task state.
7. KR contribution PROPOSED không đổi KR actual; chỉ reviewer có quyền chuyển
   VERIFIED, có evidence và audit.
8. Hai manager giao package cho một employee được scheduler serialize theo
   capacity/effective priority; founder reprioritize/hold thắng an toàn race
   lease; reassign giữ old attempt/approval/run provenance.
9. Founder thay policy/rubric/skill version tạo draft/evaluation/publish audit;
   run đang chạy và record cũ vẫn pin version cũ; rollback không xoá evidence.
10. Flutter UI phân biệt forbidden/unavailable/pending/empty và mọi badge mở ra
    record audit tương ứng thay vì tự suy diễn status.
