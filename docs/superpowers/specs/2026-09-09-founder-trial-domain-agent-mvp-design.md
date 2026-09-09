# Founder Trial Domain-Agent MVP & Truthful Module Roadmap — Design

Ngày: 2026-09-09

Trạng thái: Approved — product/design specification

## 1. Mục tiêu phát hành

Phát hành sớm cho founder một vòng lặp vận hành có dữ liệu thật, giúp họ trả lời
được mỗi tuần:

1. Ta đang kiểm chứng giả thuyết nào về khách hàng và vấn đề?
2. Bằng chứng CRM, marketing và dòng tiền thực đang ủng hộ hay bác bỏ gì?
3. Việc hoặc quyết định nào cần làm tiếp?

Sản phẩm không hứa dự đoán một dự án chắc chắn sẽ thành startup. COSA đánh giá
**mức sẵn sàng theo evidence** trên năm trục: problem, solution, traction,
economics và compliance. Founder giữ quyền chọn chu kỳ, sửa kế hoạch, chấp nhận
evidence, chuyển phase, chi tiền và dừng dự án.

## 2. Quyết định sản phẩm đã chốt

1. `12 Week Year` không là luật hay tên lifecycle chính. COSA gọi chung là
   **Operating Cycle**; 12 tuần chỉ là một template AI có thể đề xuất.
2. Founder chọn hoặc sửa duration, phase, mục tiêu, lịch review và gate của
   project. Hệ thống chỉ tạo proposal có giải thích/evidence, không tự activate
   phase hoặc tự ghi quyết định chiến lược.
3. Release 1 là **Founder Trial Loop**, không yêu cầu Vision, Mission, Value,
   PESTEL, SWOT/TOWS, BSC hay full business plan trước khi founder có dữ liệu.
4. Strategy, Operations, Marketing, CRM và Finance/CAS là một flow chung của
   MVP, không phải các ứng dụng rời nhau. Legal có guard tối thiểu trong MVP;
   legal workflow sâu là release sau.
5. Agent domain điều phối qua work packet bền vững, evidence và capability
   hẹp. Agent không tự giao quyền, không ghi business database trực tiếp, không
   ra quyết định hoặc external action chỉ bằng prompt.
6. Functional activity mặc định là skill/workflow typed; chỉ thành agent độc
   lập khi cần identity, lịch chạy, capacity, dashboard và audit riêng.
7. UI chỉ hiển thị thao tác có backend contract/capability thật. Feature chưa
   phát hành phải hiện `PLANNED`, không giả data rỗng hoặc CTA thao tác được.
8. Finance Release 1 lấy CAS làm nguồn giao dịch ngân hàng, còn việc phân loại,
   điều chỉnh, chứng từ và xác nhận sổ do founder/kế toán chịu trách nhiệm.
   Không quảng bá COSA như hệ thống tự động quyết toán hoặc thay thế chuyên gia.

## 3. Phạm vi và ngoài phạm vi Release 1

### 3.1 Trong phạm vi

- Một founder tạo project bằng problem, target customer, mục tiêu gần, nguồn lực
  ban đầu tùy chọn và nhịp review.
- Project Orchestrator tạo một `Venture Lifecycle Plan` ở trạng thái proposal:
  hypothesis, evidence threshold, Operating Cycle đề xuất, first actions,
  metric/decision cần review và các dependency domain.
- Founder xác nhận/chỉnh sửa plan, chọn duration 1–12 tuần hoặc một template
  nhiều phase. Một proposal 12 tuần có thể gồm Discovery → Problem validation →
  Solution validation → Build/validate → Go-to-market, nhưng không tự biến thành
  lịch bắt buộc.
- CRM tối thiểu: contact, interview, lead, outcome và liên kết với project,
  hypothesis/experiment.
- Marketing tối thiểu: experiment, campaign/asset draft, metric quan sát và
  evidence-linked learning. Không có autonomous paid spend hoặc outbound send.
- Finance tối thiểu: kết nối CAS, transaction ingest, proposal phân loại,
  adjustment của founder/kế toán, cash snapshot và runway/budget proposal.
- Operations: task/approval/blocker/review, tạo từ work packet đã được founder
  hoặc manager xác nhận.
- Weekly/end-cycle review gộp evidence, biến động cash, CRM/experiment outcome,
  blocked work và next decision thành một Founder Brief.

### 3.2 Ngoài phạm vi Release 1

- Bắt founder hoàn thiện Vision, Mission, Value, PESTEL, SWOT/TOWS, BSC,
  portfolio strategy hoặc fundraising dossier.
- Tự thực hiện chuyển tiền, nộp thuế, ký hợp đồng, gửi campaign/outreach, thay
  đổi deal stage quan trọng hoặc tự xác nhận sổ kế toán.
- RAG/Vault retrieval, workflow builder tự do, voice agent, multi-channel
  autopilot, legal applicability engine sâu, ERP/banking/CRM integration ngoài
  CAS.
- Một verdict AI về việc dự án “chắc chắn thành startup”.

## 4. Founder Trial Loop

~~~text
Founder tạo Project
  -> nhập problem, customer, goal, optional cash baseline/CAS, review cadence
  -> Project Orchestrator tạo Venture Lifecycle Plan proposal
  -> Founder chọn/chỉnh cycle + xác nhận hypotheses và first actions
  -> Marketing/Research tạo interview + experiment drafts
  -> CRM lưu contact, interview, lead và observed outcome
  -> Finance lấy CAS transaction, đề xuất classification/budget/runway
  -> Operations materialize approved work, theo dõi blocker và approval
  -> Weekly/End-cycle Founder Brief tổng hợp evidence
  -> Founder: continue | revise | pivot | pause | advance phase
~~~

### 4.1 Venture Lifecycle Plan

`VentureLifecyclePlan` là business record thuộc Company Plane, project-scoped và
versioned. Nó không thay thế project, initiative, cycle hay task hiện có; nó nối
chúng vào một proposal/lifecycle có thể audit.

~~~text
plan_id, workspace_id, project_id, revision, status
cycle_duration_weeks, review_cadence, timezone
problem_statement, target_customer, near_term_goal
hypotheses[]                 question, risk, evidence threshold, owner domain
phases[]                     type, duration, entry gate, exit gate, owner
metrics[]                    definition, baseline, target, source domain
budget_assumptions[]         currency, amount, source, approval requirement
decision_log[]               continue/revise/pivot/pause/advance + rationale
created_by, proposed_by_run_id, confirmed_by, timestamps, supersedes_plan_id
~~~

`DRAFT` là AI proposal hoặc founder input chưa đủ. `CONFIRMED` chỉ được tạo bởi
founder/manager có authority. Sửa hypothesis, threshold, phase, duration, metric
hoặc budget sau confirmation tạo revision mới với `change_reason`; lịch sử không
bị ghi đè.

Phase đầu không còn bị giới hạn sản phẩm vào hai lựa chọn P0/P1. Các project có
thể dùng phase template hoặc custom phase, nhưng server validate duration dương,
thứ tự phase, evidence gate, workspace scope và review schedule. Cycle hiện có
vẫn là cơ chế lịch review; plan chỉ nói cycle đó phục vụ hypothesis/gate nào.

### 4.2 Evidence model

Một evidence item phải tham chiếu `workspace_id`, `project_id`, source domain,
time observed và subject/source record. Các source đầu tiên:

| Source | Evidence tối thiểu | Điều nó có thể ảnh hưởng |
|---|---|---|
| CRM | interview outcome, lead state, customer response | problem/traction hypothesis |
| Marketing | experiment outcome, campaign metric, learning | positioning/channel hypothesis |
| Finance | CAS transaction, classification/reconciliation, cash snapshot | budget/runway/economics |
| Operations | task result, blocker, approval outcome | delivery feasibility |
| Founder | decision và rationale được xác nhận | plan/cycle/phase change |

LLM summary, web research và marketing copy chỉ là artifact/proposal. Chúng không
tự trở thành evidence đã xác nhận, không tự thay metric actual và không tự cho
phép phase transition.

## 5. Agent và workflow boundary

### 5.1 Cấu trúc điều phối

| Layer | Thành phần | Trách nhiệm | Không được làm |
|---|---|---|---|
| Founder | Decision owner | xác nhận plan, budget, gate, action risk cao | bị agent thay quyền |
| Project Orchestrator | one per project | lập/sửa proposal, route work packet, tạo Founder Brief | direct business write, tự advance phase |
| Domain agent | Marketing/Research, CRM/Growth, Finance/Cash, Operations | tạo proposal/artifact trong capability scope | tự cấp capability, action external/risk cao |
| Skill/workflow | interview synthesis, experiment design, lead scoring, CAS categorization, runway forecast, review synthesis | input/output typed, retry, evaluation | có persona/quyền mơ hồ |
| Capability/governance | Company services + Agent Platform | authorization, idempotency, approval, audit, execution | suy luận policy từ model text |

Project Orchestrator không gọi các agent con bằng prompt tự do. Nó tạo
`DomainWorkPacket` có input refs, expected artifact/evidence, allowed capability
IDs, budget/time ceiling, owning project và risk class. Scheduler/lease/approval
hiện có thực thi packet; domain agent trả artifact hay proposal có provenance.

### 5.2 Domain agent MVP

| Domain agent | MVP capability/output | Autonomy |
|---|---|---|
| Project Orchestrator | lifecycle proposal, packet routing, Founder Brief, next-decision proposal | L0/L1, no direct write |
| Marketing & Research | interview guide, positioning/experiment/campaign draft, learning synthesis | L0/L1; campaign send/spend blocked |
| CRM & Growth | contact/lead/interview proposal, scoring/follow-up draft, pipeline evidence | L0/L1; no send or irreversible conversion |
| Finance & Cash | CAS classification proposal, cash/budget/runway, accounting document draft | L1; confirm/payment blocked |
| Operations | task/work packet draft, blocker and review synthesis | L0/L1; completion/phase transition reviewed |
| Legal Guard | flag missing legal/consent evidence and route human review | L0; no legal opinion or legal record approval |

`CRM & Growth` là AgentSpec/assignment độc lập, không tái sử dụng Customer
Support chỉ vì cùng đọc customer data. Current Customer Support vẫn là support
copilot/autopilot hẹp và chỉ được nối vào lifecycle sau khi knowledge/engagement
đủ sẵn sàng.

AgentSpec là definition versioned; AI employee/assignment là identity vận hành
theo workspace. Thiết kế này phụ thuộc vào Persistent AI Workforce Governance
cho employee identity, work package, attempt, pinned skill và review. Khi phần
đó chưa phát hành, Release 1 chỉ expose domain action theo static AgentSpec và
không giả vờ cung cấp đội ngũ AI persistent có capacity/scorecard.

### 5.3 Cấp quyền và trạng thái packet

~~~text
DRAFT -> CONFIRMED -> QUEUED -> LEASED -> RUNNING
RUNNING -> PROPOSAL_READY | BLOCKED | CANCELLED | FAILED
PROPOSAL_READY -> PENDING_FOUNDER_OR_MANAGER_REVIEW
PENDING_REVIEW -> ACCEPTED -> committed Company command
PENDING_REVIEW -> REWORK | REJECTED
~~~

Chỉ Company command được review/approved mới ghi task, CRM record, campaign,
classification, accounting document hoặc decision. Mỗi command mang workspace,
project, packet/run, capability, actor, idempotency key và evidence refs. Cross
plane dùng signed delegation hẹp, không dùng client-provided workspace authority.

## 6. Finance/CAS và TT58 Release 1

CAS là producer giao dịch ngân hàng, không là accounting authority. Luồng bắt
buộc là:

~~~text
CAS webhook signed
  -> server resolve bank connection/workspace
  -> durable inbox + dedupe/quarantine
  -> normalize bank transaction
  -> Finance Agent classification proposal
  -> founder/accountant correct + confirm
  -> accounting document/ledger draft
  -> authorized confirmation/reconciliation
  -> cash snapshot + runway/budget evidence for project review
~~~

Unknown/revoked bank connection phải quarantine; transaction không được tự gán
workspace. Số tiền, currency, allocation, approval version và reconciliation
remain server-validated. CAS connection failure/degraded sync hiển thị trạng thái
rõ ở UI, không hiển thị cash snapshot cũ như số liệu live.

Release 1 giới hạn rõ: hỗ trợ chứng từ/sổ và reporting **theo TT58 pack đã chọn
và được xác nhận cho workspace**. Nếu accounting regime, jurisdiction hoặc
mapping chưa được duyệt, UI chỉ cho finance tracking/pilot và không gọi báo cáo
đó “compliant”. Founder confirmation không thay thế legal/accounting review.

## 7. UI truthful capability contract

### 7.1 Backend-owned manifest

Control Plane/Company trả `WorkspaceCapabilityManifest` có version và ít nhất:

~~~text
module_key, feature_key, surface_status
surface_status = AVAILABLE | PILOT | PLANNED | CONFIGURATION_REQUIRED | UNAVAILABLE
required_capabilities[], required_connector_keys[], entitled, reasons[]
contract_endpoint, release_note, updated_at
~~~

Server là authority của `surface_status`; client không suy luận từ route, role
cache hoặc dữ liệu rỗng. Frontend refresh manifest khi đổi workspace, sau login,
connector change và entitlement change; chưa có snapshot hoặc API lỗi thì
optional/risk module fail closed.

### 7.2 Quy tắc UI

| Status | Hiển thị | Tương tác |
|---|---|---|
| AVAILABLE | module/action live, state loading/error/empty phân biệt | gọi canonical contract endpoint |
| PILOT | badge Pilot, scope/limitation, audit-friendly note | chỉ workspace đã enable được action |
| PLANNED | roadmap card, expected value, optional interest capture | không render form/data/action giả |
| CONFIGURATION_REQUIRED | connector/regime/permission thiếu và next step | CTA tới setup phù hợp, không lộ secret/policy nhạy cảm |
| UNAVAILABLE | unavailable surface + retry/support path | không gọi mutation |

Mỗi route/CTA live phải có `feature_key` và canonical endpoint trong shared
contract. Backend `404`, `409`, `501`, `503` và capability denial map thành UI
state có nghĩa; không `catchError(() => [])` hoặc fake zero state. Frontend API
contract gate phải cấm URL legacy không có backend endpoint/manifest entry.

## 8. Module roadmap

| Release | Module/surface | Backend requirement | UI status trước release |
|---|---|---|---|
| R1 Founder Trial | Project lifecycle, task/review, Marketing experiment, CRM interview/lead, Finance cash/CAS | canonical project refs, evidence links, signed packet, CAS ingest, basic CRM/marketing contracts | AVAILABLE/PILOT theo capability |
| R1.1 Finance activation | classification confirmation, payment request, reconciliation, TT58 documents/reports where confirmed | regime/jurisdiction validation, accountant review, reconciliation commands | PILOT until verified per workspace |
| R1.2 Growth activation | campaign asset lifecycle, CRM pipeline, attribution/import, approved outreach drafts | canonical commercial contracts and evidence/event linkage | PILOT; no legacy revenue/marketing calls |
| R2 Strategic intelligence | Vision/Mission/Value, PESTEL, SWOT/TOWS, BSC, strategy canvas, funding | versioned strategy artifacts, evidence provenance, human-confirmed gates | PLANNED |
| R2 Legal workflow | entity/jurisdiction, regulation applicability, contract review workflow | approved/versioned regime packs and legal review authority | PLANNED or PILOT only |
| R3 Knowledge & automation | Vault retrieval, workflow builder, connector automation, customer-support autopilot | retrieval authorization, workflow governance, connector grants, durable execution E2E | PLANNED |
| R3 Enterprise | voice, advanced workforce, portfolio, scale governance | policy/capacity/observability/SLO evidence | PLANNED |

Academy stays acquisition/enablement and can deep-link into Founder Trial setup;
it is not a parallel business-truth system. Organization, Skill Registry and
advanced Workforce UI remain admin/pilot surfaces until persistent workforce
governance is implemented and verified.

## 9. Implementation sequence and release gates

### Slice A — lifecycle and truthful shell

Create the versioned project lifecycle proposal/confirmation contract, configurable
Operating Cycle, Founder Brief read model and backend manifest statuses. Replace
the initial dashboard/navigation with stage-aware cards: `Start`, `This week`,
`Evidence`, `Cash`, `Decision`; hide deep strategy analysis behind `PLANNED`.

**Acceptance:** founder can create a project, select a 1–12 week cycle, confirm
one hypothesis and first actions, then see no false live module/action.

### Slice B — CRM/marketing evidence flow

Make contact/interview/lead, hypothesis, experiment, campaign/asset and observed
metric reference a project. Create Marketing/Research and CRM/Growth work packet
templates; every result has evidence source and can surface in Founder Brief.

**Acceptance:** an interview and one experiment produce traceable evidence; the
brief identifies the hypothesis affected and proposes, never auto-applies, a
next decision.

### Slice C — Finance/CAS cash flow

Finish connector readiness, inbox observability, transaction classification
review, project budget mapping, cash snapshot and runway calculation. Connect
approved/reconciled finance data to plan/review without allowing the model to
confirm ledger records or payments.

**Acceptance:** a signed CAS event for a mapped workspace is ingested exactly
once; an unknown connection is quarantined; a corrected/confirmed classification
changes the project cash evidence; stale/degraded sync is visible.

### Slice D — domain orchestration and workforce identity

Implement Project Orchestrator and domain assignment on top of persistent AI
workforce/work package governance. Add CRM/Growth AgentSpec; route every packet
through exact spec/skill pins, budget/capability checks and review.

**Acceptance:** an orchestrator cannot execute a forbidden capability; each
domain proposal has run/packet/evidence provenance; founder approval is required
before any business command outside low-risk draft creation.

### Slice E — R1.1/R1.2 and planned surfaces

Expose finance activation and growth activation only after their backend contracts
and cross-plane E2E pass. Render R2/R3 modules through the manifest with roadmap
state, not empty screens. Add strategic analysis only after evidence artifacts
and lifecycle gates support it.

## 10. Verification requirements

- Public handler tests: unauthenticated, wrong-workspace, wrong-role,
  unavailable capability, stale approval and idempotency/race cases.
- Company/Agent cross-plane E2E on disposable PostgreSQL/processes: lifecycle
  proposal → confirmed packet → domain run → evidence → Founder Brief; no mock
  shortcut for authority, scheduler or finance callback.
- CAS tests: HMAC raw body, duplicate, unknown/revoked connection quarantine,
  currency/allocation/approval constraints, retry and stale sync state.
- Frontend widget/integration tests: all five `surface_status` values; manifest
  failure hides optional modules; backend error never appears as empty data;
  each live CTA uses a declared canonical endpoint.
- Release evidence records IMPLEMENTED, WIRED and VERIFIED separately. A module
  cannot move from `PLANNED`/`PILOT` to `AVAILABLE` on documentation, mock,
  static test or UI-only evidence.

## 11. Migration and compatibility constraints

- All schema changes are expand-first, tenant-scoped, versioned and have a
  reviewed rollback strategy. Historical projects/cycles/tasks remain readable;
  do not invent lifecycle evidence for them.
- Keep existing routes while migrating only through explicit compatibility
  adapters. Remove legacy frontend calls only after contract inventory confirms
  the canonical replacement; never hide route drift in an allowlist.
- Agent Platform does not import or write Company database tables. It reaches
  Company only through narrow capability endpoints with signed delegation.
- Secrets, CAS credentials, webhook headers, prompts containing sensitive input
  and delegation tokens never enter plan/evidence/analytics/UI records.

## 12. Success measures for the trial

The first founder cohort is successful when a workspace can complete, with real
records rather than demo data:

1. create project → confirm a cycle/hypothesis → complete one weekly review;
2. record at least one CRM evidence item and one marketing experiment outcome;
3. connect/import finance data or explicitly mark finance setup incomplete;
4. make one founder decision with its evidence/rationale visible later; and
5. encounter zero UI actions advertised as live that lack a reachable,
authorized backend contract.
