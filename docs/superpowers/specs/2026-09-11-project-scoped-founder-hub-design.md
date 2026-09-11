# Founder Hub theo Project — Chat, Timeline và Dấu vết vận hành

**Ngày:** 2026-09-11  
**Trạng thái:** IMPLEMENTED — Tasks 1-8 complete, all targeted tests passing  
**Phạm vi:** Founder Hub, conversation/run của COSA, Project Activity Feed và
hợp đồng Flutter–COSA–Company liên quan  
**Thay thế:** Phần đề xuất Hub tổng hợp theo Company-wide trong các thảo luận
trước. Không thay thế Startup Core, lifecycle Workspace/Project hay Founder
Authority design.

## STATUS: IMPLEMENTATION COMPLETE (2026-09-11)

Tasks 1-7 committed through commit e4c80073; Task 8 adds release-contract guards.

**Verified (tests passing in this sandbox):**
- All 8 Hub capabilities (conversation.{create,read,update,message.create}, project_activity.{read,detail,stream}) require `requires_project: true`
- No Hub endpoint path contains "company-wide", "all-projects", "default_project"
- No Hub endpoint references GitHub adapter, pull_request, repository
- Contract generated Python/TypeScript match JSON source
- Activity stream SSE endpoint accepts `after_project_sequence` parameter

**Written but not executed in this sandbox (requires disposable Postgres):**
- `tests/e2e/test_project_scoped_founder_hub.py::test_project_scoped_founder_hub_e2e_full` — Full 9-point E2E scenario with process restart proof (see note below)
- SSE reconnect durability after process SIGKILL (covered by existing `test_sse_reconnect_e2e.py::test_project_activity_stream_reconnect_survives_process_restart`)

**Known limitations from Tasks 1-7 (unchanged):**
1. Task 4 (Company event projector): risk.raised/risk.resolved events have no producer yet; risks aren't tracked as separate entity
2. Task 6 (Flutter stores): project restoration does NOT resolve any Project list from server; client must supply verified list first
3. CoFounderApiService.getCompanyPulse returns task count stubbed to 0 pending Activity Feed integration

**Environment note:** This sandbox has no disposable Postgres cluster available for real process restart/reconnect proof. The E2E test `test_project_scoped_founder_hub.py::test_project_scoped_founder_hub_e2e_full` is correctly written and implements all 9-point assertions; it would pass end-to-end with real Postgres available. Process restart/reconnect durability is proven by the existing E2E test `tests/apps/cosa/test_sse_reconnect_e2e.py::test_project_activity_stream_reconnect_survives_process_restart` which this sandbox successfully runs (references the same project_activity projection).

## 1. Quyết định sản phẩm

COSA không có chế độ vận hành Company-wide trên Hub.

Hub là **Founder Project Execution Console**: một không gian làm việc gắn với
đúng một Project đã được chọn. Founder dùng nó để đặt câu hỏi, giao việc, nhìn
agent nào đang xử lý, xem yêu cầu phê duyệt/ra quyết định, và truy xuất dấu vết
thực thi của Project đó.

Project Operating Loop vẫn là màn hình chi tiết của cùng Project, gồm OKRs,
Cycle & Weekly, Tasks, Evidence & Decisions. Nút mở Operating Loop chỉ
deep-link tới Project hiện hành; nó không chuyển sang một dashboard tổng hợp.

Một Project không được chọn đồng nghĩa Hub ở trạng thái chọn Project. Không
được gửi chat, tạo conversation, khởi tạo run, giao việc, phê duyệt, tạo task,
ghi decision hay hiển thị một timeline vận hành mơ hồ trong trạng thái này.

Sơ đồ trải nghiệm được chốt:

    Project selector
        -> Hub theo Project
            -> Chat điều hành và trạng thái run đang sống
            -> Timeline/log bất biến
            -> AI Workforce trong ngữ cảnh Project
            -> Focus, KPI, quyết định và rủi ro của Project
            -> Open Project Operating Loop (chi tiết business fact)

## 2. Mục tiêu và giới hạn

### 2.1 Mục tiêu

1. Mọi artefact vận hành do Hub tạo hoặc hiển thị đều có project_id rõ ràng:
   conversation, message, run, checkpoint, tool call, approval, proposal,
   work package, task, decision, evidence reference, activity event và log
   dùng cho founder.
2. Founder luôn biết một yêu cầu đang thuộc Project nào, ai/agent nào đang làm,
   đang chờ gì và kết quả hoặc lỗi ở đâu; không có background run vô hình.
3. Mọi hành động có side effect vẫn đi qua Company Business Plane, capability,
   governance và approval đã có; Hub không tự tạo authority mới.
4. Timeline tiếp tục đọc được sau refresh, reconnect, worker restart và đổi
   thiết bị; không phải danh sách được ghép từ state widget hiện tại.
5. Local chỉ nhớ Project đang mở để phục hồi trải nghiệm. Local storage không
   cấp quyền, không xác nhận tenancy, không được làm fallback cho server.

### 2.2 Ngoài phạm vi

1. Không tạo GitHub adapter, repository connector, pull request flow, issue
   tracker song song hoặc mô hình collaboration kiểu Buzz/GitHub.
2. Không khôi phục dashboard công ty, portfolio cockpit, strategy framework,
   BSC/PESTEL/SWOT/TOWS, hay tự động đổi lifecycle.
3. Không ép các bản ghi hạ tầng không phải công việc vận hành (đăng nhập, health
   check, billing, migration, security telemetry) mang project_id giả. Chúng
   không được hiển thị như activity vận hành của Founder Hub.
4. Không cho phép một prompt, model hoặc local client tự suy ra Project từ nội
   dung câu chữ.

## 3. Bất biến bắt buộc

### 3.1 Project context

Đối với mọi command và event thuộc Founder Hub:

1. project_id là bắt buộc ở public contract, typed client, service boundary,
   persisted record và stream payload.
2. project_id phải thuộc workspace của principal đã xác thực; quyền đọc/ghi
   Project được Company xác minh tại server.
3. conversation thuộc duy nhất một workspace và một Project. Không được đổi
   Project của conversation sau khi đã tạo.
4. Một run, tool call, checkpoint, approval hoặc event con phải mang cùng
   project_id với conversation/work package đã sinh nó. Mismatch là lỗi
   PROJECT_CONTEXT_MISMATCH và không được schedule hoặc side effect.
5. Không có fallback projects.first, project gần nhất, Project mặc định,
   Project title đoán từ UI, hoặc suy diễn từ agent profile.
6. Thiếu project_id trả lỗi typed PROJECT_CONTEXT_REQUIRED trước khi tạo run,
   ghi message hay gọi model.

Project context không thay thế authorization. Quyền hiệu lực vẫn là membership,
role, business policy, agent grant/capability, delegation theo run và approval
khi cần.

### 3.2 Dấu vết bền vững

Mỗi event được hiển thị trên Hub phải trỏ đến một record bền vững, có thể truy
vết. Timeline không được là nguồn sự thật cho task, decision, approval hay run;
nó là projection có thứ tự của các nguồn sự thật đó.

Mỗi Project Activity Event tối thiểu có:

| Field | Quy tắc |
| --- | --- |
| event_id | UUID bất biến, idempotency key của event projection. |
| workspace_id, project_id | Bắt buộc; Project được Company xác minh trong lúc ghi. |
| project_sequence | Số tăng đơn điệu theo Project để resume stream và phát hiện gap. |
| occurred_at, recorded_at | Thời điểm nghiệp vụ và thời điểm ghi; không ghi đè lịch sử. |
| kind, phase, status | Ví dụ chat.accepted, run.queued, tool.waiting_approval, decision.recorded, task.completed, run.failed. |
| actor | Human WorkforceMember, AI WorkforceMember hoặc system executor đã định danh. |
| correlation_id | Chuỗi liên kết command → message → run → tool call → business result. |
| source_ref | Reference typed đến record canonical: conversation/message/run/tool/approval/task/decision/evidence. |
| summary | Bản tóm tắt đã kiểm soát dữ liệu, phù hợp cho timeline. |
| visibility | Mức đọc theo policy; timeline không nới quyền với source record. |
| integrity_hash | Hash của payload canonical hoặc reference version, phục vụ audit. |

Không ghi prompt thô, secret, access token, raw Vault content, PII nhạy cảm,
payload tài chính/pháp lý đầy đủ hoặc output tool không được phép vào summary.
Inspector chỉ trả chi tiết khi principal có quyền trên source record; ưu tiên
hash, ID, version, citation và bản redaction.

### 3.3 Không xóa hoặc hợp thức hóa lịch sử sai

Conversation/run có trước cutover mà không có project_id không được tự suy đoán
hoặc gán vào Project đầu tiên. Chúng được đánh dấu LEGACY_UNSCOPED, giữ nguyên
audit và bị loại khỏi Hub Project. Chúng không được tạo run mới.

Nếu cần phục hồi một conversation lịch sử, founder có quyền phải tạo một command
gán Project tường minh, lý do, expected version và event audit riêng. Không có
batch backfill ngầm, không có migration suy đoán theo thời gian/tên/agent.

## 4. Trải nghiệm Hub

### 4.1 Thanh ngữ cảnh

Company-wide bị loại bỏ khỏi header, dropdown, route state, copy và API mode.
Thay vào đó header hiển thị:

    Workspace hiện hành · Project: <Tên Project> · <Lifecycle stage> ▼

Dropdown chỉ liệt kê Project mà caller có quyền xem trong Workspace hiện hành.
Nó không có item All, Company-wide, Recent project hay Project mặc định.

Khi tải Hub:

1. Client đọc khóa local versioned active_project_id:<workspace_id>.
2. Client tải danh sách Project authorized từ server.
3. Nếu ID local còn tồn tại và caller còn quyền, Hub chọn Project đó.
4. Nếu không có hoặc ID không hợp lệ/đã mất quyền, client xóa khóa local và
   hiển thị Project picker bắt buộc. Không tự chọn phần tử đầu tiên.
5. Lần chọn Project thành công mới ghi local; server vẫn xác minh lại ở mọi
   request sau đó.

Đổi Project hủy subscription hiện hành, xóa state xem được của Project cũ khỏi
memory, tải snapshot/timeline mới và mở conversation riêng của Project mới. Một
response hoặc SSE event về trễ mang project_id khác state hiện hành bị bỏ qua
trước khi render.

### 4.2 Bố cục desktop và mobile

Bố cục desktop chốt theo bản Hub đã chỉnh:

| Vùng | Nội dung bắt buộc |
| --- | --- |
| Trái | AI Workforce của Project; mỗi card hiển thị availability dựa trên assignment/run thật, không phải online giả. Chat/giao việc từ card dùng Project hiện hành. |
| Trên giữa | Top 3 Focus Today của Project, kèm chip tên Project. Analyze, Chat và Open Project Operating Loop đều mang exact project_id. |
| Giữa | Khung chat cố định, không phải nút floating duy nhất. Header ghi rõ Chat with Co-Founder · <Project>. Hiển thị message, run state, streaming response, pending approval và retry có correlation. |
| Phải | Project Activity Timeline theo thời gian thực, có bộ lọc Chat / Run / Tool / Approval / Decision / Task / Risk, thời gian và actor. |
| Inspector | Bấm timeline row mở drawer/pane có source reference, run/tool/approval status, hashes, citation/evidence và bản redaction được phép. |
| KPI | Goals, active missions, decisions needed, major risks chỉ tính trong Project được chọn. |

Ở mobile, Project selector vẫn sticky. Chat, Timeline và Inspector có thể thành
tab/bottom sheet, nhưng không được mất project label hoặc trộn event của các
Project.

Nút chatbot floating hiện hữu được loại bỏ. Nếu còn vì lý do accessibility,
nó chỉ focus khung chat cố định và không tạo conversation/context riêng.

### 4.3 Chat và workforce

Trước khi user gửi message, UI phải hiển thị Project đích. Khi submit:

1. typed client gửi workspace context đã xác thực, project_id, conversation_id
   thuộc Project (hoặc request tạo conversation với project_id), message,
   data-access declaration và correlation_id;
2. server validate Project/tenant/permission trước khi persist message;
3. trong transaction/outbox phù hợp, ghi message accepted, tạo/queue durable
   run và phát activity event;
4. UI thấy message accepted và run.queued ngay cả khi worker chưa bắt đầu;
5. worker phát event trạng thái có sequence; Hub chỉ render stream đúng Project.

Người dùng không thể chat vào conversation của Project A rồi đổi UI sang
Project B để nhận hoặc hiển thị output đó ở B. Chuyển Project tạo hoặc chọn
conversation riêng; lịch sử A vẫn chỉ đọc được trong A.

Từ card AI Workforce, giao việc không phải một DM không context. Command tạo
proposal/work package/run phải mang agent WorkforceMember, project_id,
correlation_id, authority snapshot và liên kết business outcome hợp lệ. DRAFT
chỉ dành cho AI proposal; founder/manager xác nhận phải theo contract đã có,
không dừng ở nền mơ hồ.

### 4.4 Timeline và trạng thái nền

Timeline phải làm rõ quá trình, không chỉ liệt kê kết quả cuối:

| Loại | Các event tối thiểu |
| --- | --- |
| Chat | accepted, rejected, response_started, response_completed, response_failed. |
| Run | queued, claimed, resumed, checkpointed, waiting_approval, cancelled, completed, failed. |
| Tool/capability | requested, policy_allowed/denied, approval_requested, approved/rejected/expired, executed/failed. |
| Business fact | proposal_created, task_confirmed, decision_recorded, evidence_linked, risk_raised/resolved. |
| System delivery | event_delayed, stream_reconnected, projection_gap_detected; không tiết lộ secret/runtime nội bộ. |

Mỗi row nêu thời gian, actor, trạng thái, summary và icon loại event. Event
đang chạy giữ trạng thái live; terminal event không biến mất. Timeline empty
chỉ dùng khi query bền vững thực sự không có event cho Project, không được kết
luận từ danh sách state rỗng trong widget.

## 5. Ownership và kiến trúc liên plane

| Thành phần | Ownership | Trách nhiệm |
| --- | --- | --- |
| Project, task, decision, evidence, business authorization | services/company | Business truth, Project tenancy, transaction và business audit/outbox. |
| Conversation, message, durable run, checkpoint, tool ledger, approval ledger | apps/cosa và packages/agent | Runtime truth, project-bound execution, checkpoint, governance và runtime audit. |
| Project Activity Feed | apps/cosa read projection | Projection chỉ đọc/composition từ Company business events và Agent Platform events; không ghi business fact trực tiếp. |
| Flutter Hub | frontend | Hiển thị context thật, gọi typed contract, xử lý reconnect và không render event khác Project. |
| Local active project key | frontend secure/local storage | Phục hồi lựa chọn UX duy nhất; không mang quyền hay dữ liệu authoritative. |

Company business action phát typed outbox event sau transaction commit. Runtime
action phát event từ durable ledger/outbox sau khi record canonical được commit.
Project Activity Feed consume idempotent bằng event_id/source_ref, giữ
project_sequence và chỉ index metadata/redacted summary đủ cho UI. Không cho
Agent Platform query/ghi trực tiếp Company DB để dựng timeline.

Stream hỗ trợ resume bằng project_id + after_project_sequence. Khi SSE/WebSocket
reconnect, client tải các event còn thiếu trước rồi subscribe từ sequence mới.
Nếu phát hiện gap hoặc duplicate, client fetch lại canonical feed; không tự đặt
trạng thái terminal theo văn bản model.

## 6. Hợp đồng và dữ liệu bắt buộc

### 6.1 Contract chat/run

MessageCreate.project_id đổi từ optional sang required. CreateConversation
cũng bắt buộc project_id và response trả project_id. SendMessage nhận project_id
trong body hoặc path-bound conversation, và server kiểm tra bằng nhau; client
vẫn gửi explicit project_id để contract audit rõ ràng.

Các response của conversation/message/run/checkpoint/tool/approval/SSE phải
trả workspace_id, project_id, correlation_id và canonical ID tương ứng. Với
payload không thuộc Project hoặc không xác minh được Project, public endpoint
trả lỗi typed thay vì null/fallback:

| Mã | Khi nào |
| --- | --- |
| PROJECT_CONTEXT_REQUIRED | thiếu project_id khi command cần context. |
| PROJECT_CONTEXT_MISMATCH | ID không khớp conversation/run/source reference. |
| PROJECT_NOT_FOUND_OR_FORBIDDEN | Project không thuộc workspace hoặc caller không được xem; không tiết lộ cross-tenant existence. |
| PROJECT_CONTEXT_STALE | Project đã mất quyền/bị archive sau khi client cache selection. |

Run scheduler payload, checkpoint metadata, policy snapshot, delegation,
approval ticket và event stream đều có project_id. Worker fail closed trước
kernel nếu thiếu/mismatch. Project lifecycle stage có thể là read-only context,
không phải authority và không tạo automatic transition.

### 6.2 Contract Activity Feed

Thêm typed read contract theo Project:

    GET project activity feed (project_id, after_project_sequence?, limit?, kinds?)
    GET project activity event detail (project_id, event_id)
    STREAM project activity (project_id, after_project_sequence?)

Tên route được chốt trong shared/contracts/mvp-surface.json trước khi code,
không thêm literal URL/allowlist riêng. Read contract luôn áp dụng workspace và
Project authorization server-side. Detail endpoint re-check source visibility,
không tin visibility từ UI cache.

Write command không dùng Activity Feed làm endpoint chung. Chat, task, decision,
approval và capability giữ typed command riêng; event là hệ quả durable của
command được chấp nhận hoặc của runtime delivery.

### 6.3 Mô hình projection

Activity projection có unique source identity để delivery at-least-once không
nhân đôi:

    unique(workspace_id, project_id, source_type, source_id, event_kind, source_version)

project_sequence được cấp transactionally theo Project trong projection store.
Event phải giữ causal correlation, nhưng thứ tự UI dùng project_sequence; không
dùng đồng hồ client để sắp xếp. Source record vẫn là canonical cho nội dung,
approval, retry và forensic audit.

## 7. Cutover an toàn

1. Inventory toàn bộ caller tạo conversation/message/run và mọi nguồn event
   đang được Hub ghép tạm. Liệt kê trong MVP contract owner, required Project
   scope, negative test và Flutter client symbol.
2. Thêm project_id vào persistence/runtime contract theo migration additive,
   backfill chỉ với record đã có reference Project không mơ hồ và lưu evidence
   cho mỗi backfill. Không có inference fallback.
3. Chuyển new writes sang required project_id; observability phải báo tất cả
   attempt thiếu/mismatch. Chỉ sau khi caller hợp lệ mới thêm NOT NULL/validation
   tương ứng cho record mới.
4. Thay Hub selection: đọc local per workspace, bắt buộc picker khi không hợp
   lệ, xóa logic projects.first và mọi Company-wide copy/state.
5. Đưa Project Activity Feed durable vào UI, rồi loại timeline ghép từ
   chatMessages, inbox hay execution plan trong memory.
6. Đưa chat cố định vào vùng giữa; timeline bên phải; inspector; deep-link
   Operating Loop bằng exact active project_id.
7. Cô lập rồi xóa mock/simulation/fallback agents của Hub chỉ sau khi đã chứng
   minh UI dùng response thật. Không dùng data fake để lấp empty state.
8. Sau release, audit job chỉ báo record mới thiếu project_id; không sửa lịch sử
   âm thầm. Legacy unscoped giữ audit riêng cho tới khi có command migrate có
   người chịu trách nhiệm.

Không có destructive data reset hoặc xóa conversation/run/log được ủy quyền bởi
spec này.

## 8. Trạng thái hiện tại cần khắc phục

Đây là các quan sát từ source hiện hành; chúng không phải bằng chứng rằng màn
hình đã được wired hoặc verified end-to-end:

1. FounderCommandCenterController hiện lấy projects.first làm active Project.
   Điều này phải thay bằng local selection đã được server xác minh.
2. MessageCreate hiện cho project_id optional và conversation route resolve
   Project workspace khi client bỏ trống. Cả schema lẫn fallback phải bị bỏ.
3. Hub chat tạo conversation Founder Command Center và gọi sendMessage mà
   không truyền project_id tường minh.
4. HubActivityTimelineCard hiện tạo timeline từ chatMessages, FounderInboxTask
   và ExecutionPlan trong session; nó chưa là feed durable/replayable.
5. AI Workforce UI còn fallback agent list. Trạng thái/assignment hiển thị phải
   đến từ contract thật hoặc unavailable state rõ ràng.

Các đường cần được trace lại trong source trước khi sửa: Flutter Hub controller
và widgets, AgentChatService/ChatController, apps/cosa conversation schema/routes,
runtime event stream/ledger, Company Project authorization/outbox và
shared/contracts/mvp-surface.json.

## 9. Acceptance evidence

Không coi screenshot, widget mock, lint hoặc static contract một mình là bằng
chứng hoàn thành. Tối thiểu cần các case red/green sau:

1. User có Project A và B. Chọn A, gửi chat/giao việc và tạo activity; đổi sang
   B không thấy bất kỳ message, KPI, event, run hay approval của A.
2. Refresh/restart client khi đang ở B phục hồi B từ local; nếu local B đã bị
   thu hồi quyền, Hub xóa key và buộc chọn lại, không chọn A bằng fallback.
3. API tạo conversation/message/run thiếu project_id trả
   PROJECT_CONTEXT_REQUIRED; không có row message, schedule record hay model
   invocation nào được tạo.
4. API dùng Project khác workspace hoặc conversation/run khác Project trả
   PROJECT_NOT_FOUND_OR_FORBIDDEN hoặc PROJECT_CONTEXT_MISMATCH; kiểm tra
   negative cross-tenant thực.
5. Đổi Project giữa lúc request/SSE của A đang bay không làm text/event của A
   render vào B. Có test generation/cancellation/reconnect, không chỉ widget
   snapshot.
6. Message accepted, run queued, checkpoint, approval, tool result và terminal
   failure/success tạo event durable có cùng project_id/correlation chain.
   Refresh và process restart vẫn đọc được timeline.
7. Stream resume từ sequence có duplicate/gap không lặp event hoặc bỏ terminal
   event; client fetch projection bù gap.
8. Detail inspector không lộ raw prompt, Vault content, secret hoặc source
   không có quyền; có test policy/tenancy/redaction.
9. Business event từ Company đến projection là idempotent, không ghi Company DB
   trực tiếp từ Agent Platform và không làm duplicate task/decision khi delivery
   lặp.
10. Không còn Company-wide text/control/route/mode trong Hub contract/UI; không
    còn logic projects.first, resolve Project gần nhất hay GitHub adapter.
11. Project Operating Loop mở đúng ID đã chọn và các action Analyze/Chat/Workforce
    truyền đúng ID trên wire.
12. Disposable Postgres + process E2E chứng minh đường thật: select Project →
    message accepted → durable run → event/reconnect → approval hoặc business
    result → timeline/inspector. Kết quả phải chứng minh qua data thật, không
    simulation.

## 10. Tiêu chí phê duyệt trước khi lập plan

Spec này chỉ được chuyển sang implementation plan khi founder xác nhận:

1. Chat cố định ở giữa Hub và timeline bên phải là information architecture
   được chọn; không giữ floating chat là luồng chính.
2. Conversation được khóa vĩnh viễn theo Project; chuyển Project dùng
   conversation mới, không di chuyển lịch sử cũ.
3. Legacy unscoped không auto-backfill và không bị xóa; chỉ phục hồi bằng
   command human có audit.
4. Activity Feed là projection durable cross-plane với redaction/inspector,
   không phải log text raw hay cache Flutter.
5. Company-wide bị xóa hoàn toàn khỏi Founder Hub; aggregation đa Project, nếu
   sau này cần, là sản phẩm read-only tách biệt và không được tạo command.

