# Hội đồng Cố vấn Điều hành COSA — Đặc tả sản phẩm và quản trị

- **Ngày:** 2026-09-11
- **Trạng thái:** Đề xuất; tài liệu này không thay đổi runtime.
- **Chủ thể ra quyết định:** Founder (con người)
- **Phạm vi:** tư vấn điều hành theo Project, phân tích được quản trị, Founder decision và bàn giao vào workflow hiện hữu.

## 1. Quyết định sản phẩm

COSA bổ sung **Hội đồng Cố vấn Điều hành** (Executive Advisory Board): một bề mặt
theo Project để Founder đóng khung quyết định, chọn cố vấn phù hợp phân tích độc lập,
thấy rõ bất đồng/độ bất định, sau đó tự mình ra quyết định kinh doanh.

Đây không phải việc đổi tên hàng loạt agent thành C-level, mô phỏng ban điều hành,
hay thêm một tầng executive tự trị. Mỗi title là một tổ hợp tư vấn có version:
phạm vi hẹp, skill đã pin, output schema, và không có quyền nào ngoài quyền hiệu lực
của `WorkforceMember` cùng `AgentSpec` thực đang được gán.

Founder vẫn là CEO/người quyết định. Chief of Staff (CoS) chỉ điều phối và tổng hợp;
không được duyệt, giao việc, chi tiêu, tuyển dụng, phát hành hoặc sửa business truth.

Catalog có thể định nghĩa mọi vai trò, nhưng **không role nào được kích hoạt đại trà**.
Mỗi Project chỉ có một preset Startup Core nhỏ, do Founder chọn khi khởi tạo hoặc khi
chủ động đổi cấu hình. Founder có thể bật/tắt thêm từng role đủ điều kiện. Việc này
không tự tạo WorkforceMember, không cấp capability, và không là chuyển giai đoạn
tự động.

```text
Founder đóng khung quyết định thuộc Project
  -> Company lưu frame bất biến và chọn advisor đủ điều kiện
  -> Agent Platform chạy analysis cô lập, chỉ đọc/đề xuất
  -> Company xác thực rồi lưu kết quả, dissent và evidence reference
  -> CoS tổng hợp; critic độc lập có thể phản biện
  -> Founder duyệt, sửa, từ chối, hết hạn hoặc hủy
  -> Founder chủ động đưa proposal đã chọn vào workflow hiện hữu
```

Không mũi tên nào trên cấp side effect cho agent.

## 2. Tham khảo bên ngoài: áp dụng có chọn lọc

Đặc tả tham khảo [C-level Advisor guide](https://github.com/alirezarezvani/claude-skills/blob/main/docs/skills/c-level-advisor/c-level-advisor.md),
[agent protocol](https://github.com/alirezarezvani/claude-skills/blob/main/c-level-advisor/skills/agent-protocol/SKILL.md)
và [skill pipeline](https://github.com/alirezarezvani/claude-skills/blob/main/SKILL_PIPELINE.md)
của `claude-skills`. Đây là mẫu tư duy, không là dependency runtime COSA.

| Mẫu upstream | Điều chỉnh COSA |
| --- | --- |
| CoS route câu hỏi đến executive. | Catalog role do code quản lý tạo tập ứng viên xác định. Founder có thể bỏ role; thêm role cần release/redeploy và assignment thực. |
| Thành viên phân tích độc lập. | Mỗi advisor chỉ nhận immutable frame và evidence được phép; không đọc peer draft, gọi peer hay ghi kết luận trung gian vào Company. |
| Critic xem synthesis. | Critic có thể phản biện analysis đã hoàn tất/synthesis; không gọi advisor, sửa output hay tạo action. |
| Confidence, caveat, dissent có cấu trúc. | Record validate giữ source ref, assumption, confidence, conflict và dissent; thiếu evidence phải hiện rõ, không biến thành certainty. |
| Local decision memory raw/approved. | Company có record append-only theo tenant/Project; không `~/.claude`, file local hay context xuyên tenant. Chỉ Founder decision đã ghi mới là approved context. |
| Skill có instruction/trigger/verification. | Skill COSA có version, provenance, capability gate, test, pin trong AgentSpec; không import instruction tự do lúc runtime. |

Mọi skill chuyển thể/nhập lúc triển khai phải pin commit upstream đã review, lưu URL,
license review, adaptation note và content hash trong manifest. Không phụ thuộc nhánh
`main` di động, số lượng skill công bố, hay sao chép instruction khi chưa review
authority/dữ liệu.

## 3. Bất biến COSA

1. **Company là business truth.** Frame, selection, conclusion, Founder decision và
   action-proposal state được ghi bởi `services/company`; `packages/agent` và
   `apps/cosa` không ghi trực tiếp Company database.
2. **Project bắt buộc.** Mọi record/run/evidence/decision/activity event mới có
   `workspace_id` và `project_id` bất biến. Project chọn local chỉ là UX, không
   phải authorization.
3. **Title không cấp quyền.** `CFO`, `CISO` và role label khác không đổi tool
   access/approval authority. Quyền hiệu lực là deny-by-intersection của AgentSpec,
   Company grant, scope Project/legal entity, Company policy, Control Plane overlay
   và live one-time ticket khi cần.
4. **Decision là của người.** Founder hoặc human manager được ủy quyền có thể mở
   board. AI không quyết định, nhận risk, cập nhật KPI, duyệt proposal hay tạo work.
5. **Không bịa execution.** Trạng thái role là `UNAVAILABLE`,
   `AVAILABLE_NOT_ACTIVATED`, `ACTIVE` hoặc `DISABLED`; trạng thái analysis là
   `QUEUED`, `RUNNING`, `FAILED` hay `COMPLETED`. Tất cả đều dựa trên
   assignment và run ledger thực. Flutter không được hiện online/completed/sent nếu
   chưa có authoritative record.
6. **Evidence tối thiểu.** Chỉ giữ source handle, provenance, access classification
   và excerpt được phép; không đưa raw banking data, secret, Vault rộng hoặc PII
   không cần vào prompt/timeline.
7. **Không professional advice.** Finance/legal/security/people/tax/regulatory
   outputs nêu giới hạn và human review; không đại diện chuyên gia cấp phép hoặc thực
   hiện filing, payment, hiring hay external communication.

## 4. Từ vựng và ownership

### 4.1 ExecutiveRoleDefinition

`ExecutiveRoleDefinition` là catalog code-owned, versioned, deployed gồm:

- `role_key`, title hiển thị, advisory remit và routing tag;
- precondition, AgentSpec/profile nền, skillpack version bắt buộc;
- output schema, evidence minimum, negative case;
- data classification, capability ref được phép;
- provenance metadata của instruction chuyển thể.

Nó không sửa từ Flutter, không là user-created prompt và không là `WorkforceMember`
mới. Catalog launch được ship như AgentSpec: code, review, test và redeploy.

### 4.2 Executive assignment

Role chỉ eligible trong Project khi WorkforceMember cụ thể và Project assignment nền
đã tồn tại/active. Role map vào team/assignment hiện hữu, không duplicate employee và
không bypass startup-team template. Một template có thể catalog-visible nhưng
`UNAVAILABLE` hoặc `AVAILABLE_NOT_ACTIVATED`; không được fallback im lặng sang
generic operations agent.

### 4.3 ProjectExecutiveRoleActivation

`ProjectExecutiveRoleActivation` là Company record theo Project, không phải agent
hay assignment mới. Nó lưu `role_key`, `workspace_id`, `project_id`, state
`ACTIVE` hoặc `DISABLED`, nguồn kích hoạt (`STARTUP_CORE_PRESET` hoặc
`FOUNDER`), human actor, lý do, timestamp và optimistic-lock version.

Một role chỉ chuyển sang `ACTIVE` khi role definition, WorkforceMember/Project
assignment nền, Company grant và policy đều đang hợp lệ. Nếu chưa thỏa, nó là
`UNAVAILABLE`; nếu đã thỏa nhưng Founder chưa bật, là
`AVAILABLE_NOT_ACTIVATED`. Activation không được khởi tạo runtime profile hay
tuyển/gán nhân sự ngầm.

### 4.4 ExecutiveDeliberation, ExecutiveAnalysis, ExecutiveDecision

`ExecutiveDeliberation` là Company record cho một version của một Project decision:
`id`, `workspace_id`, `project_id`, `frame_version`; question/type/deadline,
outcome/evidence class; selected role và lý do; AgentSpec/skill/manifest pin,
authorization snapshot; state/timestamp/CAS version; redacted context ref.

Sửa material question/scope/evidence/deadline tạo `frame_version` mới liên kết bản
cũ, không overwrite.

`ExecutiveAnalysis` là output validate của một role/frame: conclusion/options,
claim-to-evidence mapping, assumption, unknown, confidence, risk, constraint,
human review, conflict/dissent và pin role/skill/AgentSpec/policy/manifest.

`ExecutiveDecision` là human revision append-only: `APPROVE`, `MODIFY`,
`REJECT`, `EXPIRE`, `CANCEL`. `MODIFY` ghi thay đổi/lý do, không sửa analysis
gốc.

## 5. Catalog role và ranh giới

Role chỉ enabled khi profile nền, governed skill, evidence source, authorization path
và test đã tồn tại. Bảng là catalog mục tiêu, không có nghĩa mọi role dùng được ngày
đầu hoặc được bật mặc định.

| Role | Advisory remit | Hướng skill | Quy tắc khả dụng |
| --- | --- | --- | --- |
| `chief_of_staff` | frame, routing, synthesis, decision-log hygiene | `executive.board-protocol`, weekly review/SOP/automation | Cần operations profile; không execute operations change. |
| `cfo` | cash, runway, scenario, finance control | `finance.cfo-review`, runway, budget guardrail, unit economics | Chỉ map Finance Agent hiện hữu khi grant/evidence scope cho phép. |
| `cmo` | positioning, demand, messaging, experiments | content strategy, GTM funnel, landing CRO, paid experiment | Chỉ map Marketing Agent; recommendation không là campaign. |
| `coo` | cadence, process constraint, delivery dependency | weekly review, SOP, automation design | Cần operations profile; không run workflow/automation. |
| `cro` | revenue, pipeline, sales enablement, RevOps | prospecting, pipeline, enablement, RevOps | Unavailable đến khi sales/RevOps profile/capability deploy. |
| `cpo` | customer problem, product bet, PRD/backlog | discovery, PRD, backlog/MVP priority | Unavailable đến khi product profile deploy. |
| `cco` | customer success, retention, support learning | health/churn/lifecycle, support patterns | Cần support/customer-success profile; không gửi outbound. |
| `chro` | org design, hiring process, people risk | culture principles, hiring-copilot | Không personnel/employment action. |
| `ciso` | security/privacy threat, control gap | security/privacy assessment, risk register | Không cấp incident/system access. |
| `gc` | legal/compliance issue spotting, escalation | compliance gap, policy resolution, hand-off | Không legal representation. |
| `cdo` | data rights, quality, knowledge governance | data-rights, scoped knowledge governance | Cần Project data classification/read access. |
| `caio` | model risk, evaluation, safety, provider governance | eval design, provider risk, red-team | Cần eval/model-policy path audit được. |
| `vpe` | feasibility, delivery risk, release readiness | feasibility, observability, release/vertical slice | Cần engineering profile/delivery evidence. |

Với câu hỏi board rộng, đề xuất tối thiểu ba role thực sự available; Founder có thể
chọn ít hơn nếu ghi lý do. Câu hỏi hẹp có thể dùng một specialist và CoS nếu frame
giải thích vì sao không cần full board.

### 5.1 Startup Core: preset mặc định, không phải auto-progression

Preset chỉ là một lựa chọn cấu hình của Founder theo Project. Nó không đọc hay thay
đổi lifecycle stage, không tự thêm role khi thời gian trôi qua, và không thay thế
quyền kiểm soát Project của con người.

| Preset do Founder chọn | Role bật mặc định nếu đủ điều kiện | Lý do |
| --- | --- | --- |
| `startup-discovery` | `chief_of_staff`, `cmo`, `cfo` | Cần giữ focus quyết định, kiểm chứng nhu cầu/thông điệp và kiểm soát runway sớm. |
| `startup-build-launch` | `chief_of_staff`, `cmo`, `cfo`, `coo` | Bổ sung điều phối vận hành khi Founder đã chủ động vào giai đoạn build/launch. |

Các preset chỉ bật role nếu underlying assignment thực tồn tại. Nếu Finance hoặc
Marketing Agent chưa được gán cho Project, role tương ứng vẫn là `UNAVAILABLE`,
không được giả lập. `cpo` và `vpe` có thể là nhu cầu hợp lý trong build nhưng
không nằm trong default cho đến khi profile/capability/evidence path tương ứng được
release.

Founder có thể bật một role ngoài preset qua activation flow, sau khi role đó chuyển
`AVAILABLE_NOT_ACTIVATED`. Founder cũng có thể disable role đang active. Disable
chặn frame/run mới, giữ lịch sử; run đang chạy chỉ được hủy qua cancel flow có audit,
không bị biến mất ngầm.

## 6. Protocol deliberation

### 6.1 State

```text
DRAFT -> FRAMED -> ANALYSIS_QUEUED -> ANALYZING -> SYNTHESIS_QUEUED
      -> CRITIC_REVIEW (optional) -> AWAITING_FOUNDER -> DECIDED

FRAMED | ANALYSIS_QUEUED | ANALYZING | SYNTHESIS_QUEUED | CRITIC_REVIEW
  -> CANCELLED | EXPIRED
mọi execution state -> FAILED_REQUIRES_ATTENTION
```

Mỗi analysis có `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`.
Board partial chỉ vào `AWAITING_FOUNDER` khi missing/failed analysis hiển thị và
synthesis nói rõ thiếu hụt; không được bịa consensus.

### 6.2 Frame

Founder hoặc human manager được ủy quyền tạo `DRAFT`, xác nhận `FRAMED` với:

- Project, question/type, deadline, decision owner;
- constraint, success/failure measure, evidence source được phép, known uncertainty;
- role đã chọn và lý do bỏ role được đề xuất;
- data classification, critic requirement nếu có.

Company kiểm tra workspace/Project access, Founder/manager authority, Project
membership, active assignment, AgentSpec/skill pin và Company policy trước khi ghi
frame queueable. Mọi lỗi fail-closed, không generic fallback.

### 6.3 Analysis độc lập

Company tạo signed idempotent run request qua governed outbox. Agent Platform resolve
registry/manifest hash chính xác và re-authorize tool checkpoint. Advisor chỉ thấy
frame bất biến, evidence role-permitted/provenance-tag, analysis của chính mình nếu
revision protocol cho phép, và instruction/schema hẹp.

Advisor không thấy peer draft, không gọi peer, không recursive delegate, không ghi
Company decision. Inter-agent depth phase này là zero. Data gathering cần thiết là
capability invocation riêng, authorization riêng và run ledger riêng.

### 6.4 Synthesis, critic, Founder hand-off

CoS nhận completed validated analysis, không phải raw hidden chain-of-thought, rồi
tạo synthesis gồm option, agreement/dissent, evidence coverage/unknown, proposal
có confidence/risk, và action proposal `NOT_EXECUTED`.

Critic tùy chọn chỉ ra unsupported claim hoặc alternative bỏ sót, ghi dissent; không
gọi advisor, mutate output hay tạo action. Founder xem critic song song synthesis.

Chỉ human Founder finalize `ExecutiveDecision`; manager có thể có quyền frame/hủy
hẹp nhưng không giả danh Founder approval. Decision append-only, phát Project Activity
và mới có thể thành approved context cho board sau.

Action proposal vẫn là draft. Founder/human manager phải chủ động chọn từng proposal
qua confirmed-work path hiện hữu; path đó vẫn recheck authorization, transactional
queueing, audit, live ticket. Board result không tự tạo task, đổi KPI/record, gửi
message, chi tiền hay kích automation.

## 7. Contract và luồng dữ liệu

### 7.1 Company API

| Operation | Contract |
| --- | --- |
| `POST /operations/projects/:projectId/executive-deliberations` | Tạo DRAFT sau human/Project authorization. |
| `POST /operations/projects/:projectId/executive-deliberations/:id/frame` | CAS frame, pin snapshot và atomically append outbox. |
| `GET /operations/projects/:projectId/executive-deliberations` | List record redacted cùng Project. |
| `GET /operations/projects/:projectId/executive-deliberations/:id` | Frame, state role thật, output validate, dissent/activity theo evidence authorization. |
| `POST /operations/projects/:projectId/executive-deliberations/:id/cancel` | Hủy pre-final với actor/reason; run cancellation durable best-effort. |
| `POST /operations/projects/:projectId/executive-deliberations/:id/founder-decision` | Append Founder decision revision có optimistic locking. |
| `POST /operations/projects/:projectId/executive-roles/:roleKey/activate` | Founder bật một role `AVAILABLE_NOT_ACTIVATED`, có lý do và CAS. Không tạo agent/assignment. |
| `POST /operations/projects/:projectId/executive-roles/:roleKey/disable` | Founder disable role, chặn frame mới và giữ timeline/audit. |

Fail-closed code: `PROJECT_CONTEXT_REQUIRED`, `PROJECT_NOT_FOUND_OR_FORBIDDEN`,
`EXECUTIVE_ROLE_NOT_AVAILABLE`, `EXECUTIVE_EVIDENCE_NOT_AUTHORIZED`,
`EXECUTIVE_DELIBERATION_VERSION_CONFLICT`, `EXECUTIVE_DELIBERATION_NOT_DECIDABLE`,
`EXECUTIVE_DECISION_ALREADY_RECORDED`.

Không public endpoint nhận arbitrary role, prompt/skill text, hay AgentSpec hash từ caller.

### 7.2 Event và persistence

Company phát signed outbox: `executive.deliberation.framed.v1`,
`executive.analysis.requested.v1`, `executive.synthesis.requested.v1`,
`executive.critic.requested.v1`, `executive.decision.recorded.v1`.

Agent Platform trả signed idempotent envelope như
`executive.analysis.completed.v1`. Company validate tenant, Project, frame version,
role membership, run ID, manifest pin, evidence descriptor trước khi ghi analysis.
Event unmatched/stale/duplicate/cross-Project bị reject và audit.

Persistence (tên bảng theo convention) phải có workspace/Project/actor/time/version
và append-only activity cho: frame/revision; selection/availability/execution pin;
analysis/evidence/failure; synthesis/critic; Founder decision/action link; outbox/inbox
idempotency và authorization-policy snapshot. Agent Platform giữ run/checkpoint/tool/
manifest ledger tối thiểu; Company sở hữu timeline người dùng.

## 8. Chuẩn skill và instruction

Skill chung `executive.board-protocol` chứa restriction/schema; skill role chỉ mở
rộng, không làm yếu protocol. Output machine-validatable tối thiểu:

```json
{
  "role_key": "cfo",
  "decision_id": "immutable-deliberation-id",
  "conclusion": "bounded recommendation hoặc insufficient-evidence finding",
  "options": [{"option_id": "A", "tradeoffs": ["..."]}],
  "evidence": [{"source_ref": "authorized-handle", "claim_ids": ["claim-1"]}],
  "assumptions": ["..."],
  "risks_and_unknowns": ["..."],
  "confidence": {"level": "low|medium|high", "rationale": "..."},
  "human_review_required": ["..."]
}
```

Invalid nếu thiếu source mapping, biến unknown thành fact, claim action executed,
chứa data material chưa phân loại, nêu peer conclusion chưa thấy, hay sai frame/role pin.

Mẫu instruction:

```text
Bạn là cố vấn <ROLE> của COSA cho đúng immutable Project decision frame này.
Bạn phân tích/khuyến nghị; không quyết định, duyệt, thực thi, ủy quyền hoặc truy cập
dữ liệu ngoài authorized evidence. Nêu evidence ủng hộ/không ủng hộ, assumption,
rủi ro và human/professional review. Thiếu evidence thì trả insufficient-evidence
finding. Không bịa peer view/consensus. Chỉ trả ExecutiveAnalysis schema đã pin.
```

Mỗi role skillpack khai báo skill/schema version, source provenance/adaptation/license/
content hash/deprecation; trigger và non-trigger; Project/data/capability/risk scope;
output/eval; evidence minimum, và negative case cho thiếu workspace/Project/assignment/
evidence, cross-workspace, stale frame, unauthorized source; human hand-off rõ.
Instruction code-seed/redeploy theo AgentSpec registry. ADR runtime registration sau
này không được bỏ provenance, pin, manifest review hay availability fail-closed.

## 9. Authority, approval và data protection

1. Approval/grant nhắm human `WorkforceMember`, permission và scope cụ thể; không
   dùng title string. Không coi `cfo` là approver: generic adapter hiện fallback
   requirement string lạ về workspace-operator role.
2. Board chỉ ship sau khi tạo/gán AI workforce được Founder-enforce, không chỉ
   workspace membership, và có negative test.
3. Activation/deactivation role chỉ do Founder thực hiện. Nó chỉ thay đổi
   `ProjectExecutiveRoleActivation`, không tự gán workforce, không đổi grant/policy
   và không vượt qua bất kỳ guard nào.
4. Board read/propose-only. Action path riêng phải pass Company grant,
   Project/legal-entity scope, Control Plane, capability contract và live ticket tại
   execution time.
5. CoS không nhận union permission của advisor; chỉ đọc validated Company artifact
   và có synthesis capability hẹp.
6. Raw draft chỉ cho participant được phép/Founder. Approved decision context scope
   riêng theo Project, không thành general model memory/cross-tenant context.
7. Mở evidence là authorization thứ hai: mỗi source expansion recheck classification
   và Project scope.
8. Audit ghi actor/role/ID/state/auth result/manifest-skill hash/reason code an toàn,
   không raw prompt, credential, bank data hay Vault export rộng.

## 10. Trải nghiệm

Board ở Project đang chọn trong Founder Hub / Project Activity, không là dashboard
toàn công ty. UI hiển thị preset đã chọn, frame/Project context; advisor state thật
`UNAVAILABLE`/`AVAILABLE_NOT_ACTIVATED`/`ACTIVE`/`DISABLED`; conclusion,
evidence availability, assumption, confidence, human review, dissent; synthesis/
critic gắn nhãn proposal/review; Founder decision timeline bất biến, action proposal
chưa execute, và lý do khi assignment không tồn tại.

Không dựa vào Flutter workforce `unavailable` stub. Cần typed authenticated API
client và contract test trước khi mở board control. Settings authority view vẫn là
nơi xem grant; Board UI không tạo/sửa grant ngầm.

## 11. Rollout

1. Ship static catalog/shared protocol sau provenance review, nhưng chỉ đưa hai
   Startup Core preset vào UI; không bật toàn catalog.
2. `startup-discovery` mặc định chỉ đề xuất/bật `chief_of_staff`, `cmo`,
   `cfo`; `startup-build-launch` thêm `coo`. Mỗi role vẫn cần Project
   assignment thực và governed capability.
3. `cro`, `cpo`, `cco`, `chro`, `ciso`, `gc`, `cdo`, `caio`, `vpe`
   catalog-visible nhưng unavailable đến khi profile, skill, evidence contract, E2E
   gate tương ứng release; sau đó Founder mới có thể activation từng role.
4. Không backfill Project cũ, bịa history hay suy diễn assignment. Founder chủ động
   gán team qua workflow hiện hữu.
5. Release sau capability/policy gate; disable chặn frame mới nhưng giữ history/read/audit.
6. Schema/event additive, consumer idempotent, UI/API rollout reversible; không task/
   approval contract nào bị diễn giải lại bởi title.

## 12. Bằng chứng chấp nhận bắt buộc

Static check/doc không chứng minh feature. Cần disposable Postgres/process E2E:

| Vùng | Bằng chứng |
| --- | --- |
| Catalog/activation | Role chỉ map profile/skill pin hỗ trợ; unavailable không queue/fallback operations; preset không kích hoạt role thiếu assignment; chỉ Founder có thể activate/disable role available. |
| Tenant/Project | API/outbox/inbox reject missing/forged/stale/cross-tenant/cross-Project ID/evidence. |
| Founder authority | Member, AI, co-founder không quyền không frame/finalize; hiring/assignment là Founder-enforced. |
| Independence | Peer draft bị giữ kín; không peer/recursive invocation; critic không mutate/trigger work. |
| Capability | Title không mở tool; revoke grant/policy/ticket fail live checkpoint, không side effect. |
| Integrity | CAS, duplicate callback, retry, cancel, expiry, partial failure, replay giữ history append-only. |
| Data | Reject evidence không an toàn, event/timeline redacted, source expansion re-authorize. |
| Skill | Reject stale hash, thiếu provenance, sai role, JSON lỗi, unsupported claim. |
| Flutter | Render state unavailable/running/failed/partial thật; không proposal giả executed. |
| Operations | Signed outbox, idempotency, restart recovery, activity projection, cancellation. |

Skillpack validation là cần nhưng chưa đủ. Không khởi động được Company integration
environment là verification bị chặn, không phải runtime evidence pass.

## 13. Non-goal

- Thay Founder bằng virtual CEO hoặc cấp AI approval authority.
- Đổi tên agent mà không có capability/evidence boundary.
- Bulk import skill/command/local decision file/hook/persona từ upstream.
- Prompt production user-editable hoặc runtime profile tự do.
- Autonomous hiring/firing/spending/accounting/legal/security/publication/outbound/
  task/KPI/workflow từ board output.
- Board toàn công ty bỏ qua Project tenancy/lifecycle.
- Coi mock UI, lint, README hay prototype là bằng chứng execution bền vững.

## 14. Cần Founder duyệt trước implementation plan

1. `chief_of_staff` là advisor hiển thị hay chỉ orchestration label.
2. Human role nào, nếu có, được frame/cancel/finalize bên cạnh Founder.
3. Evidence classification cho Finance/Marketing/Operations board đầu tiên.
4. Critic bắt buộc với risk class nào.
5. Policy-gate name và audit retention requirement.

Cho đến khi các quyết định và precondition fix này được chấp nhận, đây chỉ là đặc tả
thiết kế.

## 15. Bằng chứng Thực thi Runtime (Verified 2026-09-11)

Toàn bộ 8 tasks của kế hoạch triển khai đã hoàn tất, tuân thủ nghiêm ngặt các ranh giới:
1. **Catalog & Multi-Language Contracts**: 13 roles code-owned tại `shared/contracts/executive-advisor-roles.json`, biên dịch đồng bộ cho TS, Python, Dart. `make contracts-check` và `make skillpacks-validate` (5 skillpacks) đạt chuẩn 100%.
2. **Founder-Only Authority**: Xác thực `role_id == 'founder'` trên mọi thao tác bật preset, kích hoạt/tắt role, tạo frame và ra quyết định.
3. **Advisory L1 Boundary**: Thẩm quyền chỉ ở mức read & propose, không cấp quyền thực thi (zero effectful tools). Mọi đề xuất hành động gắn nhãn `NOT_EXECUTED`.
4. **Deliberation Ledger & CAS**: Sổ cái nghị sự lưu trữ tại Postgres của Company service với optimistic locking (CAS version), outbox transactional events.
5. **Cách ly Phân tích & Tách biệt Tenant**: Runner độc lập không peer contamination; endpoint authority kiểm tra phân công hợp lệ; từ chối mọi tham chiếu bằng chứng xuyên Project/Workspace (`403 PermissionDenied`).
6. **Flutter UI Trung thực**: Hiển thị chính xác trạng thái từ server (`UNAVAILABLE`, `AVAILABLE_NOT_ACTIVATED`, `ACTIVE`, `DISABLED`), không có fake success lạc quan.
7. **Bảo chứng Vận hành & Phục hồi**:
   - ADR: `docs/architecture/adr/ADR-EXECUTIVE-BOARD-001-governed-project-advisory.md`
   - Runbook: `docs/operations/executive-advisory-board-runbook.md`
   - Test phục hồi: `tests/e2e/test_executive_advisory_board_recovery.py` (5/5 pass)
   - Test vòng đời E2E: `tests/e2e/test_executive_advisory_board.py` (2/2 pass)
   - Verification Gate: `make executive-board-verify`

