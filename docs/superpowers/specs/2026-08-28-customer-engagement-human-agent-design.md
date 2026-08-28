# Thiết kế Customer Engagement native, human-led và agent-augmented cho COSA

**Trạng thái:** Proposed — cần được chủ sở hữu sản phẩm/kiến trúc duyệt trước khi triển khai

**Ngày:** 2026-08-28

**Phạm vi:** Customer Support, Customer Success và Sales-assist trong COSA

**Không phải dependency:** Chatwoot chỉ là tài liệu tham khảo mô hình nghiệp vụ; COSA không self-host, không fork, không gọi API Chatwoot và không phụ thuộc runtime của Chatwoot.

## 1. Tóm tắt quyết định

COSA sẽ phát triển một domain **Customer Engagement** native, tích hợp trực tiếp với CRM và Agent Platform hiện có. Hệ thống không phải “một chatbot”, cũng không phải một CRM thứ hai: đây là nơi điều hành inbox, hội thoại, hỗ trợ khách hàng, phối hợp CS/Sales và các quyết định chính sách liên quan đến khách hàng.

Nguyên tắc chủ đạo là **human-led, agent-augmented**:

1. Nhân sự nội bộ là chủ thể vận hành và ra quyết định; agent chỉ tự hành trong phạm vi policy đã cấp.
2. `Workspace` là tenant duy nhất. Không có tenant, company ID hay mapping ngầm khác trong hợp đồng nghiệp vụ.
3. CRM hiện có trong `services/company/commercial` là business truth của Account, Contact, Lead, Opportunity, Customer, Billing và Marketing.
4. Customer Engagement sở hữu trạng thái vận hành hội thoại; nó tham chiếu CRM, không nhân bản CRM.
5. Automation xác định (routing, SLA, labels, tạo task) tách biệt với reasoning của agent.
6. Mọi message ra ngoài, CRM write, chính sách ngoại lệ và tác vụ tài chính đều đi qua Capability + Governance + Audit. Không có prompt nào tự cấp quyền.
7. Người dùng nội bộ có thể tiếp quản ngay một hội thoại; agent chuyển sang chế độ copilot và không được gửi tin hay ghi dữ liệu ngoài phạm vi đã ủy quyền.

## 2. Nền tảng hiện có và ranh giới thiết kế

Các phần hiện có sẽ được tái sử dụng, không thay thế:

| Nền tảng COSA | Vai trò trong thiết kế này |
| --- | --- |
| `services/company/identity` và `WorkforceMember` | Danh tính duy nhất cho nhân sự con người và agent profile. Không lập bảng nhân sự riêng cho CS/Sales/AI. |
| `services/company/commercial` | CRM business truth: Account, Contact, Lead, Opportunity, Customer, Invoice, Subscription và marketing context. |
| `packages/agent_core` | Run bền, checkpoint, capability gateway, governance, approval và audit event. Không import business service. |
| `apps/cosa` | Composition của Customer Support Copilot, Sales Qualifier và Customer Success Agent. |
| `services/cosa` | Control-plane cho tenant, secrets, connector grants và policy wiring; không sở hữu transcript hay CRM truth. |
| Event intake và trigger rule hiện có | Kích hoạt run bằng event tham chiếu, có deduplication, quota và promotion gate. |

Các bảng CRM hiện có không có mô hình chuẩn cho thread hội thoại, message, ownership history, policy decision hoặc external channel mapping. Customer Engagement bổ sung các aggregate này, nhưng phải liên kết tới `sales.accounts`, `sales.contacts`, `sales.sales_leads`, `sales.sales_opportunities` và `sales.customers` bằng workspace-scoped references.

## 3. Thuật ngữ chuẩn

| Thuật ngữ | Nghĩa |
| --- | --- |
| Khách hàng | Người bên ngoài trao đổi với doanh nghiệp qua một channel. Không phải `User` nội bộ của COSA. |
| Người dùng nội bộ | Nhân sự sử dụng COSA: CS, sales, manager, policy owner, finance reviewer. Khi có hồ sơ nghiệp vụ, dùng `WorkforceMember`. |
| Inbox | Điểm nhận một luồng giao tiếp: web chat, email, Zalo, WhatsApp, Facebook, điện thoại hoặc API channel. |
| Conversation Thread | Vòng đời hỗ trợ cho một khách hàng trong một inbox; gồm message, assignment, SLA, status và outcome. |
| Public Message | Nội dung có thể gửi/đã gửi cho khách hàng. |
| Internal Note | Nội dung chỉ cho workforce; tuyệt đối không được gửi qua delivery channel. |
| Copilot | Agent đọc context, tóm tắt, tìm knowledge, chuẩn bị draft hoặc proposal; không tự side effect. |
| Autopilot | Agent thực thi một workflow đã được policy cho phép. Phạm vi luôn hẹp, versioned và có thể thu hồi. |
| Decision Request | Hồ sơ quyết định có cấu trúc cho ngoại lệ chính sách, giá, chiết khấu, refund, hợp đồng hoặc hành động cần thẩm quyền. |
| Takeover | Hành động một WorkforceMember tiếp quản thread từ agent/automation. |

## 4. Kiến trúc mục tiêu

```text
Experience Plane
  Flutter Customer Desk / Customer 360 / Approval Queue
                 │
Company Business Plane
  Identity ── Commercial CRM ── Customer Engagement
                 │                    │
                 │          transactional outbox + projections
                 ▼                    ▼
Agent Platform
  event intake → policy trigger → durable run → capability gateway
                                           │
                                           ▼
                                  proposal / approval / audited action
                 │
Control Plane
  tenant, connector installation, secret reference, connector grant
```

### 4.1. Ownership theo layer

| Thành phần | Sở hữu | Không được làm |
| --- | --- | --- |
| Customer Engagement trong Company Service | Inbox, thread, message metadata, assignment, SLA, decision request, support/sales outcome | Không chạy LLM trực tiếp, không chứa raw secret của provider. |
| Commercial CRM | Hồ sơ khách hàng và commercial truth | Không suy ra quyền hay tự gửi message từ dữ liệu CRM. |
| Agent Core | Run, tool call, checkpoint, approval, governance history | Không ghi trực tiếp vào business DB, không biết schema CRM cụ thể. |
| Capability layer | Thực thi side effect đã kiểm soát | Không tự quyết policy nghiệp vụ. |
| Control Plane | Secret reference, connector authorization/grant | Không lưu transcript, PII business hoặc quyết định thương mại. |
| Flutter | Hiển thị, nhập lệnh từ con người | Không là authority cho state transition hay permission. |

### 4.2. Ranh giới tenant

Mọi aggregate mới có `workspace_id` bắt buộc. Query, update, link và delete luôn ràng buộc `id AND workspace_id`; không load toàn cục rồi so sánh trong application code. Các link chéo CRM phải được database và service layer chặn nếu khác workspace.

`Workspace` là sản phẩm-facing tenant duy nhất. Platform company ID, provider account ID hoặc channel account ID chỉ là external reference, không thay thế `workspace_id` trong API business hay Agent Core.

## 5. Mô hình domain Customer Engagement

Đề xuất bắt đầu trong `services/company/commercial` để tái sử dụng trực tiếp CRM và tenant guard. Chỉ tách thành service riêng sau khi có bằng chứng về scale, ownership hoặc deployment boundary cần thiết.

### 5.1. Aggregate và dữ liệu mới

| Aggregate / bảng đề xuất | Dữ liệu cốt lõi | Liên kết |
| --- | --- | --- |
| `engagement_inboxes` | channel type, locale, business hours, SLA policy, default team, allowed agent profiles | Workspace, connector installation. |
| `engagement_channel_endpoints` | provider ref, delivery capability, verification config reference, status | Một Inbox; secret chỉ qua `secret_ref`. |
| `conversation_threads` | inbox, contact ref, status, priority, owner, active mode, timestamps, correlation ID | Workspace; optional Account/Lead/Opportunity/Customer refs. |
| `conversation_messages` | direction, visibility, sender kind/ref, body reference, content hash, delivery state, idempotency key | Một Thread. |
| `conversation_assignments` | assigned team/member/agent profile, reason, assigned/ended timestamps | Một Thread; append-only lịch sử. |
| `conversation_labels` | label taxonomy version và source của label | Một Thread; labels có schema, không là string tự do cho reporting quan trọng. |
| `conversation_outcomes` | intent, resolution code, escalation reason, CSAT reference, sales signal evidence | Một Thread; có thể tham chiếu Decision Request. |
| `customer_interactions` | timeline summary có cấu trúc, source/evidence refs, confidence | Liên kết Contact/Lead/Opportunity/Customer. |
| `decision_requests` | loại quyết định, facts, policy version, options, authority, deadline, status | Thread và các CRM record liên quan. |
| `decision_request_events` | proposal, review, approval/rejection, execution/error | Append-only audit của Decision Request. |

`conversation_messages` không thay thế knowledge store hoặc CRM notes. Nội dung nguyên gốc phải được quản lý theo classification/retention; `customer_interactions` chỉ lưu fact hoặc summary có cấu trúc cần cho CRM, không tự động copy nguyên transcript.

### 5.2. Liên kết identity và CRM

Một thread có thể bắt đầu trước khi biết khách hàng. Vì thế `contact_id`, `account_id`, `lead_id`, `opportunity_id`, `customer_id` phải cho phép null tại thời điểm tạo; mọi record vẫn bắt buộc thuộc workspace.

Quy tắc resolution:

1. Email chuẩn hóa và được xác thực là khóa chính để match Contact khi có mặt.
2. Phone E.164 là tín hiệu bổ sung; không tự gộp nếu có xung đột.
3. Multiple candidates, dữ liệu chưa xác thực, contact bị `do_not_contact`, hoặc account conflict tạo một review item cho con người.
4. Agent có thể đề xuất link/merge, nhưng không tự merge Contact hoặc Account.
5. Khi một thread phát hiện sales intent, chỉ tạo `Lead`/`Opportunity` theo policy. Nếu chưa đủ authority, agent tạo proposal hoặc Decision Request.

## 6. State machine của Conversation Thread

Không suy diễn trạng thái bằng việc dò từ như “đã xử lý” trong nội dung message. State transition là command có validation và event đã version.

### 6.1. Trạng thái nghiệp vụ

| Trạng thái | Nghĩa | Người có thể chuyển |
| --- | --- | --- |
| `open` | Doanh nghiệp còn nợ một hành động/phản hồi. | Assigned WorkforceMember, automation được cấp quyền, agent policy. |
| `pending_customer` | Đã phản hồi hoặc yêu cầu thông tin và đang chờ khách. | WorkforceMember/agent policy. |
| `pending_internal` | Chờ phê duyệt, sales review, billing/ops hoặc dependency nội bộ. | WorkforceMember, Decision Request workflow. |
| `snoozed` | Tạm hoãn đến thời điểm cụ thể; hệ thống phải schedule re-open. | WorkforceMember/automation. |
| `resolved` | Case hoàn tất theo resolution code có cấu trúc. | WorkforceMember; agent chỉ khi policy cho phép resolution code cụ thể. |
| `reopened` | Khách/nhân sự mở lại một case đã resolved. | Inbound message hoặc WorkforceMember. |

`reopened` là event/audit outcome; persisted status có thể trở về `open` để tránh hai định nghĩa “đang active”. Mọi transition phải ghi `actor`, reason code, previous state, current state và correlation ID.

### 6.2. Mode và ownership

`active_mode` độc lập với status:

| Mode | Ý nghĩa | Quyền agent |
| --- | --- | --- |
| `human_assigned` | Một WorkforceMember chịu trách nhiệm trực tiếp. | Read, summarize, draft; không gửi hoặc mutate nếu không được ủy quyền riêng. |
| `team_queue` | Case đang chờ team nhận. | Triage/routing trong policy đã duyệt; không tự hứa hẹn chính sách. |
| `agent_autopilot` | Agent xử lý use case hẹp đã promotion. | Chỉ capability/action trong rule đã pin. |
| `agent_copilot` | Agent hỗ trợ con người. | Chỉ artifact/proposal. |
| `awaiting_decision` | Có Decision Request chưa đóng. | Chuẩn bị context và nhắc SLA; không thực thi action bị khóa. |

Takeover là command atomic: kết thúc assignment agent, tạo assignment mới cho WorkforceMember, đặt `active_mode=human_assigned`, revoke mọi pending send command chưa delivery và append event `engagement.thread.taken_over.v1`. Khi người dùng giao lại agent, action đó cũng được audit với scope và expiry rõ ràng.

### 6.3. Public message và internal note

Message có hai trục tách biệt:

- `direction`: `inbound`, `outbound`, `system`.
- `visibility`: `customer`, `internal`.

Chỉ `outbound + customer` mới được delivery ra external channel. `internal` có thể chứa handoff context hoặc rationale rút gọn, nhưng không lưu private chain-of-thought của model. Một API/model không được mặc định map note nội bộ thành outbound text.

## 7. Human-in-the-loop và quyết định chính sách

Con người không chỉ là fallback khi agent thất bại. Hệ thống phải hỗ trợ nhân sự CS/Sales trả lời trực tiếp, tiếp quản case, yêu cầu ý kiến liên phòng ban và thực thi quyết định sau khi được cấp quyền.

### 7.1. Decision Request

`DecisionRequest` được tạo khi thread cần một quyết định có thẩm quyền, ví dụ:

- Giá ngoại lệ, discount, credit hoặc điều kiện thanh toán.
- Đổi/trả/refund, hủy hợp đồng hoặc service recovery vượt policy chuẩn.
- Ngoại lệ hợp đồng, cam kết SLA, điều khoản data/privacy.
- Thay đổi chính sách bán hàng hoặc quyết định ảnh hưởng nhiều khách hàng.
- Thay đổi trạng thái Opportunity/Customer có hậu quả tài chính mà agent không được tự làm.

Record tối thiểu:

```text
id, workspace_id, request_type, status
thread_id, contact_id, account_id, lead_id, opportunity_id, customer_id
policy_id, policy_version, policy_snapshot_ref
facts_ref, evidence_refs, options, recommendation_ref
requested_by_actor, assigned_authority, approval_deadline
decision, decided_by_workforce_member_id, decided_at, decision_reason
execution_ref, correlation_id, created_at, updated_at
```

`facts_ref` và `evidence_refs` chỉ tới snapshot/artifact có classification phù hợp; record không lặp secret hay raw credentials. `policy_snapshot_ref` bảo đảm người duyệt biết chính xác policy version tại thời điểm ra quyết định.

### 7.2. State machine Decision Request

```text
draft
  → submitted
  → under_review
  → approved ──→ execution_pending ──→ executed
  ├→ rejected
  ├→ needs_information ──→ submitted
  └→ expired
```

Approval nghiệp vụ và approval tool invocation là hai tầng khác nhau:

- `DecisionRequest` ghi nhận **quyết định kinh doanh/chính sách** của người có thẩm quyền.
- Durable approval trong Agent Core bind đúng `(run_id, tool_call_id, checkpoint_ref)` trước một lần side effect.

Một Decision Request được approved không phải token vĩnh viễn cho mọi tool call. Khi agent thực thi, hệ thống phải kiểm tra decision còn hiệu lực, target chưa drift, người quyết định phù hợp authority và governance hiện tại vẫn cho phép.

### 7.3. Ma trận thẩm quyền mặc định

| Tình huống | Owner quyết định | Agent được làm | Action bị cấm tự động |
| --- | --- | --- | --- |
| FAQ/policy chuẩn | CS hoặc policy đã publish | Tìm knowledge, draft/trả lời trong allowlist | Sáng tạo policy hoặc cam kết ngoại lệ. |
| Khiếu nại/case nhạy cảm | Assigned CS/CS lead | Summary, sentiment/intent, đề xuất escalation | Tự resolve, hứa bồi thường. |
| Lead qualification | Sales owner | Trích xuất facts, score, draft Lead proposal | Tự tạo Opportunity hoặc gửi báo giá tự do. |
| Discount/pricing exception | Sales manager/policy owner | Chuẩn bị options và pipeline impact | Tự chấp thuận giá, sửa commercial truth. |
| Refund/cancel/service recovery | Policy owner + finance/authorized reviewer | Thu thập evidence, tạo request, draft message | Tự hoàn tiền, hủy subscription, gửi xác nhận cuối cùng. |
| Chính sách mới | Policy owner/management | Tổng hợp insight, mô phỏng, draft | Tự publish policy. |

Quyền thực tế phải là permission/capability cụ thể, không suy ra chỉ từ title công việc.

## 8. Event, automation và agent execution

### 8.1. Business events

Customer Engagement phát business fact qua transactional outbox cùng transaction ghi state. Event mẫu:

```text
engagement.inbox.created.v1
engagement.thread.opened.v1
engagement.thread.assigned.v1
engagement.thread.taken_over.v1
engagement.message.received.v1
engagement.message.sent.v1
engagement.thread.status_changed.v1
engagement.decision_request.submitted.v1
engagement.decision_request.decided.v1
engagement.thread.resolved.v1
```

Event tuân theo canonical envelope hiện có: event ID, schema version, correlation/causation ID, actor, producer và classification. Với `restricted`, payload chỉ mang ID/reference/hash; agent muốn đọc nội dung phải gọi capability đã được policy cho phép. Không nhúng access token, secret, full transcript hay PII không cần thiết vào event.

### 8.2. Deterministic automation trước, agent sau

Automation rules dùng condition/action typed và versioned. Ví dụ phù hợp:

- Route inbox theo ngôn ngữ, giờ làm việc, tier khách hàng hoặc priority đã xác định.
- Áp SLA, nhãn taxonomy, tạo follow-up task, snooze/re-open.
- Escalate thread khi deadline, negative CSAT hoặc customer health đã xuống ngưỡng.
- Tạo Decision Request khi một command thuộc nhóm policy exception.

Automation không gọi LLM để quyết định một rule có khớp hay không. Các điều kiện phải kiểm tra trên structured facts. Rule delayed phải re-check state khi đến hạn, không thực thi action dựa trên snapshot cũ.

### 8.3. Ba mode agent

1. **Copilot (`artifact_only`)**: tạo summary, draft response, response checklist, extracted facts, sales signal hoặc Decision Request proposal. Không side effect.
2. **Proposal (`proposal`)**: đề xuất label, assignment, lead/opportunity change hay action customer-facing. Con người quyết định/approve trước khi execute.
3. **Autopilot (`write`)**: chỉ cho use case hẹp có spec pin, eval evidence tươi, capability grant, rate limit, fallback/handoff và policy code. Ví dụ: trả lời FAQ đã approved hoặc request thông tin qualification.

Input của run là thread/message reference, not raw event payload. Agent load context qua read capability: Customer Engagement repository, Commercial read API và knowledge snapshot. Agent Core không import trực tiếp Company Service.

### 8.4. Capability boundary

| Capability | Ví dụ | Governance mặc định |
| --- | --- | --- |
| `engagement.thread.read` | Đọc thread, message metadata, assignment, SLA | Allow khi workspace/member grant hợp lệ. |
| `commercial.customer.read` | Customer 360, invoice/subscription summary cần thiết | Allow có data classification phù hợp. |
| `engagement.message.draft` | Tạo artifact draft | Allow; không delivery. |
| `engagement.message.send` | Gửi public message | Require approval trừ template/policy được pre-authorize chính xác. |
| `engagement.assignment.write` | Route/handoff/label | Allow hoặc approval theo rule scope. |
| `commercial.lead.write` | Tạo/đổi Lead | Require approval trừ workflow deterministic đã được cấp rõ ràng. |
| `commercial.opportunity.write` | Create/change Opportunity | Require approval. |
| `billing.*` | Refund, cancel, invoice adjustment | Require approval hoặc deny theo default. |
| `policy.publish` | Publish chính sách mới | Require multi-role approval. |

Mọi write phải dùng idempotency key, correlation ID và actor attribution. Hệ thống kiểm tra takeover/ownership ngay trước delivery để tránh agent gửi một response cũ sau khi con người đã tiếp quản.

## 9. Channel adapter: mô hình đa kênh không phụ thuộc nhà cung cấp

Customer Engagement không hard-code schema của một helpdesk hay một kênh truyền thông. Mỗi provider được bọc bởi một Channel Adapter chuẩn:

```text
verifyInbound(request) -> verified external event
normalizeInbound(event) -> Customer Engagement command
sendOutbound(command) -> provider delivery result
getDeliveryStatus(ref) -> status
resolveExternalIdentity(ref) -> verified identity signals
```

Inbound delivery phải:

1. Xác thực chữ ký/mTLS theo provider trên raw request khi provider yêu cầu.
2. Dedupe theo delivery/message ID trong inbox riêng của adapter.
3. Ghi command/business state và outbox atomically.
4. Trả acknowledgement nhanh; model call, enrichment và external retry chạy bất đồng bộ.
5. Không tự tin cậy data do client/browser gửi.

Outbound delivery dùng outbox/command log riêng, có idempotency key, retry/backoff, status `queued | sent | delivered | failed`, dead-letter và khả năng hiển thị lỗi cho WorkforceMember. Agent không giữ raw provider credential; Control Plane chỉ trả `secret_ref` cho worker được cấp grant phù hợp.

## 10. Trải nghiệm người dùng nội bộ

Customer Desk cần phục vụ người thật trước, không thiết kế như màn hình theo dõi agent.

### 10.1. Các bề mặt chính

| Bề mặt | Nội dung cần có |
| --- | --- |
| Inbox queue | Open/pending/snoozed, SLA, priority, team, assignee, customer tier, bot/human mode. |
| Conversation workspace | Public messages tách rõ internal notes; composer, attachments, canned/approved response, takeover/delegate, delivery status. |
| Customer 360 | Contact, Account, consent/DNC, Lead/Opportunity, Customer health, subscription/invoice summary, interactions gần đây. |
| Copilot panel | Summary có evidence refs, recommended response, intent, missing information, sales signal; người dùng edit/accept/reject. |
| Decision queue | Pricing/refund/policy cases, authority, deadline, evidence, options, decision history, execution status. |
| Policy/QA review | Lý do handoff, automation/agent evaluation, unsafe proposal, customer feedback và lỗi delivery. |

### 10.2. Hành vi takeover

Nút `Take over` luôn hiện khi agent/automation đang active. Sau khi takeover thành công:

- Thread có owner là WorkforceMember và timeline ghi event không thể mơ hồ.
- Composer thuộc người dùng; agent chỉ tạo draft sau khi người dùng yêu cầu hoặc policy cho phép copilot.
- Pending external sends từ agent bị cancel/invalidated nếu chưa delivery.
- UI hiển thị rõ mode hiện tại để tránh cả agent và người gửi hai câu trả lời.

Người dùng có thể `Delegate to agent` trở lại nhưng phải chọn workflow/skill, scope hành động và thời hạn. Không có việc giao quyền vô thời hạn theo một click mơ hồ.

## 11. Privacy, security và audit

1. Mọi record và artifact scope theo workspace; kiểm tra membership ở service boundary và workspace condition trong query.
2. Không truyền raw secrets, access token hoặc credential-shaped fields trong event payload, run event hay UI event.
3. Raw transcript, file đính kèm, knowledge snapshot và CRM data phải có classification/retention rõ; chỉ cung cấp minimum necessary context cho agent.
4. Khi identity khách chưa được xác thực, agent không tiết lộ account, invoice, subscription hoặc PII; nó chuyển sang identity-verification flow hoặc human handoff.
5. Message outbound phải lưu actor (`WorkforceMember`, agent profile hoặc automation), correlation ID, policy/rule version, idempotency key và delivery status.
6. Decision Request lưu authority, policy version, evidence reference, rationale và execution reference. Không cho phép “approved=true” chung chung.
7. No model chain-of-thought trong transcript, internal note, approval hoặc audit ledger. Lưu summary/reason code/evidence cần thiết thay vì reasoning private.
8. Retention/delete/export phải chạy qua policy và audit; không để một connector xóa trực tiếp CRM hoặc transcript ngoài workflow đã duyệt.

## 12. Reporting và chất lượng

Phân biệt hai lớp metric:

| Nhóm | Metric khuyến nghị |
| --- | --- |
| Support operations | First response time, resolution time, SLA breach, backlog aging, reopen rate, transfer rate, CSAT, delivery failure. |
| Human/agent collaboration | Draft acceptance, override/takeover rate, escalation rate, approval latency, unsafe proposal rate, automation rollback. |
| Sales | Conversation-to-qualified-lead, qualified lead-to-opportunity, pipeline attribution, sales cycle contribution, next-action SLA. |
| Customer success | Onboarding completion, health change, renewal-risk escalation, recurring issue themes. |

Metric là projection của immutable business events và outcomes đã chuẩn hóa. Không dùng raw LLM output hoặc các field tự do làm basis trực tiếp cho KPI quan trọng.

## 13. Lộ trình triển khai đề xuất

### P0 — Foundation và human desk tối thiểu

- Chốt vocabulary, ownership, state machine, message visibility và workspace boundary.
- Thêm schema/migration Customer Engagement cùng tenant/composite constraints cần thiết.
- Xây Inbox, Thread, Message, Assignment, Internal Note và audit event; chưa có autonomous agent.
- Xây Customer 360 read model dùng CRM hiện có.
- Xây Decision Request và approval UX tối thiểu cho pricing/refund/policy exception.
- Viết tenant isolation, idempotency, concurrency/takeover và state-transition tests.

### P1 — Deterministic workflow và CS/Sales copilot

- Routing, SLA, labels, work queues, snooze/reopen và escalation typed.
- Customer Support Copilot ở `artifact_only`: summary, draft, knowledge citations, sales signal extraction.
- Hiển thị proposal/evidence, edit/accept/reject feedback; chưa auto-send.
- Xây quality review và dashboard cơ bản.

### P2 — Channel adapters và controlled proposals

- Bổ sung từng provider theo Channel Adapter contract, bắt đầu từ channel có nhu cầu thật.
- Delivery outbox, idempotency, retry, provider verification và failure queue.
- Agent đề xuất routing/labels/Lead action; human approval trước write/send.

### P3 — Autopilot hẹp có promotion gate

- Chỉ enable workflow đã có evaluation evidence, agent spec pin và rollback/handoff path.
- Ví dụ đầu tiên: FAQ theo knowledge đã duyệt hoặc form qualification giới hạn.
- Theo dõi containment, error, takeover, CSAT và policy violation; disable ngay khi vượt ngưỡng.

### P4 — Tối ưu hóa theo evidence

- Bổ sung policy/version management, advanced SLA, QA sampling và customer-success workflows.
- Mở rộng tự động hóa theo use case riêng lẻ; không “mở toàn bộ agent” theo role chung.

## 14. Vị trí code dự kiến khi triển khai

Đây là định hướng placement, không phải danh sách file đã được tạo:

```text
services/company/commercial/
  handlers/customer-engagement/       # public business APIs qua tenant guard
  services/customer-engagement/       # business logic, transactions, outbox
  models/customer-engagement/         # typed model re-export

services/company/shared/db/schema/
  customer-engagement.ts              # Drizzle schema; workspace/composite constraints

services/company/shared/events/
  customer-engagement-events.ts       # canonical business-event builders

apps/cosa/
  agents/                              # support/sales/customer-success profile specs
  capabilities/                        # engagement_read, message_draft, message_send, commercial_read/write
  workflows/                           # approved workflow compositions only

packages/agent_core/
  # giữ generic: run, policy, approval, eval; không import commercial/engagement

services/cosa/
  # connector installation, secret ref, service grant; không business transcript
```

Mọi handler business mới phải lấy workspace từ `TenantContext` server-authoritative, không nhận `workspaceId` tin cậy từ body. Handler chỉ parse input và gọi service; query/transaction nằm ở service theo convention Encore hiện có.

## 15. Required test matrix

| Scenario | Kết quả bắt buộc |
| --- | --- |
| User ở Workspace A truy cập thread ở B | `not found`/permission denied không tiết lộ record. |
| Concurrent assignment/takeover | Chỉ một assignment active thắng; command agent cũ bị invalidated. |
| Retry inbound/outbound | Một delivery/message idempotency key không tạo duplicate message hay duplicate CRM effect. |
| Internal note | Không có đường delivery customer; không xuất hiện trong customer-facing export. |
| Agent gửi khi human takeover | Bị deny/cancel trước delivery. |
| Thread chứa customer chưa xác thực | Không đọc/tiết lộ billing/account dữ liệu restricted. |
| Proposal tạo Opportunity | Không write nếu chưa có approval đúng tool call/checkpoint. |
| Decision Request hết hạn | Không execute dù từng được đề xuất/approve trước đó nếu policy yêu cầu còn hiệu lực. |
| Delayed automation | Re-check state, owner và policy trước lúc execute. |
| Provider delivery lỗi | Outbox retry/die có audit; WorkforceMember thấy lỗi và có đường retry an toàn. |
| Autopilot rule bị disable | Không nhận event mới và không chạy command còn chờ ngoài policy. |

## 16. Non-goals

- Tái hiện toàn bộ feature hoặc codebase của Chatwoot.
- Xây một CRM song song bên trong Customer Engagement.
- Cho phép agent tự ra chính sách bán hàng, tự thỏa thuận giá hoặc tự thực thi finance action.
- Cho phép mọi channel hoặc mọi use case tự động ngay từ P0.
- Dùng LLM/text heuristics làm authorization, state machine hoặc source of business truth.
- Tách microservice mới trước khi có operational evidence cho thấy `commercial` không còn là boundary phù hợp.

## 17. Câu hỏi cần quyết định trước P0 implementation

1. Channel đầu tiên cần ship là gì: web chat, email, Zalo, WhatsApp hay API channel?
2. Ai là authority cụ thể cho discount, pricing exception, refund, cancellation và contract exception ở từng workspace?
3. Policy nào được phép trả lời tự động ngay từ đầu, bằng ngôn ngữ nào và với knowledge source/version nào?
4. Retention, data residency và export/delete obligations cho transcript/attachment là gì?
5. SLA mục tiêu cho từng inbox/tier khách hàng, và ai nhận escalation ngoài giờ?
6. Sales stage transitions nào chỉ do con người, transition nào có thể là deterministic workflow sau approval?
7. Có cần dual-control cho finance/legal decision không, hay một policy owner là đủ?

## 18. Definition of Done cho design này

Thiết kế chỉ được coi là ready để lập implementation plan khi chủ sở hữu xác nhận:

1. Cosa sẽ phát triển Customer Engagement native và không dùng Chatwoot như product/runtime dependency.
2. Workspace, CRM ownership và `WorkforceMember` boundaries trong tài liệu này đúng với product direction.
3. State machine thread, takeover semantics và Decision Request authority được chấp nhận.
4. P0 scope, channel ưu tiên, retention và policy owner đã được trả lời.
5. Mọi side effect của agent đi qua capability/governance/approval, không có bypass từ UI, prompt hay direct database access.

Sau khi được duyệt, bước tiếp theo là tạo implementation plan tách P0 thành các lát nhỏ: schema + service, event/outbox, human desk, Decision Request, rồi mới đến copilot.
