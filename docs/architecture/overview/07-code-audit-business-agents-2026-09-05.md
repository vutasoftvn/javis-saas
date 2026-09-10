# Rà soát logic nghiệp vụ và agent — 2026-09-05

Phạm vi: code tại commit `e4829b75`, nhánh `main`, gồm Company strategy/operations/finance/legal, COSA worker/composition/capabilities và các màn hình liên quan. Code, schema, migration, handler, caller và test là nguồn kết luận; tài liệu kiến trúc chỉ để tham khảo. Đây là đánh giá implementation, không xác nhận tính đúng pháp lý của các văn bản được seed.

**Bổ sung theo yêu cầu founder:** [Phân tích chu kỳ N tuần, Cas.so và permissions](/docs/architecture/overview/08-phan-tich-cycle-cas-permissions-2026-09-05.md) làm rõ 12WY là mẫu phương pháp, độ dài thực tế tùy chọn; khoản chi do founder quét QR và chuyển qua app ngân hàng. Vì vậy khuyến nghị payout dưới đây được điều chỉnh thành workflow đề nghị chi–QR–đối soát, không ưu tiên xây executor tự chuyển tiền. Tài liệu bổ sung cũng đối chiếu contract Cas.so và nguồn chính thức về TT58/2026.

**Kết luận chính:** nền tảng đã có nhiều cấu phần thật, nhưng vòng từ quyết định → thực thi → kết quả → đánh giá lại chưa nhất quán. Cần ưu tiên quyền truy cập, trạng thái nghiệp vụ và kết nối giữa các lớp trước khi mở thêm agent profile.

**Luồng thực tế và phần nên giữ**

| Vùng | Đã có trong code | Điểm cần nối hoặc củng cố |
|---|---|---|
| Strategy | Workspace W0–W5 tách project P0–P6; assumption, experiment, evidence review, gate, decision, pilot, metric contract và PMF | Chất lượng evidence giữa các evaluator khác nhau; gate dự án chưa ràng buộc quyết định chuyển stage; next action có đầu vào mẫu |
| Operating | Kickoff materialize cycle → weekly plan → commitment → task; weekly goal phát outbox cho agent phân rã; execution plan và task sweep | Tuần hiện tại, giao diện 12WY, đồng bộ sửa kickoff, tiêu chuẩn hoàn thành và rollup kết quả |
| Finance | Giao dịch thu/chi, approval vượt ngưỡng, bank ingestion, chứng từ, proposal đối soát, snapshot cash/burn/runway | Khóa kỳ, currency, cạnh tranh khi đối soát, thống nhất ý nghĩa các nguồn snapshot |
| Legal | Pháp nhân và verification; catalog/version/rule/obligation; AI deployment/assessment/snapshot/data governance/incident | Enum sau migration, applicability theo từng pháp nhân, quyền người duyệt và nghĩa vụ chưa hoàn tất trong action context |
| Agent | Registry pin, capability gateway, governance/approval, compliance resolver, durable task claim/lease, worker và outbox | Event→worker contract, Copilot context/output, skill→capability readiness, knowledge thật và bằng chứng hoàn thành |

Nên giữ CAS/version và transactional outbox của stage transition; approval evidence ở project gate; metric contract có version; kiểm tra workspace khi accept reconciliation; founder check khi duyệt giao dịch vượt ngưỡng; compliance resolver và model data guard trong kernel chính. Không cần thay toàn bộ kiến trúc để sửa các lỗi dưới đây.

**Các lỗi ưu tiên P1 — sửa trước khi tăng mức tự động hóa**

**F01. Hai lệnh strategy thiếu ràng buộc workspace ở bản ghi đích.**

`completeWeeklyReviewService` và `acceptActionProposalService` nhận ID nhưng không nhận workspace. Handler xác thực membership workspace A, service SELECT/UPDATE theo ID đơn lẻ, rồi trả nội dung và phát event thuộc bản ghi B. Thành viên A biết ID của B có thể tác động chéo workspace và nhận summary/context của B.

Nguồn: [weekly review service](/services/company/operations/strategy/services/weekly-review.service.ts:95), [proposal handler](/services/company/operations/strategy/handlers/next-best-action.handler.ts:103), [proposal service](/services/company/operations/strategy/services/next-best-action.service.ts:285).

Điều chỉnh: truyền `TenantContext`; mọi SELECT/UPDATE phải có workspace và trạng thái nguồn hợp lệ; replay không tạo event mới. Test hai workspace cho từng command.

**F02. Membership đang được dùng thay cho quyền sửa chính sách agent.**

Auditor có `permissions=['read']`, nhưng endpoint sửa `workspaceCapabilityPolicy` chỉ gọi `requireWorkspaceAccess`; service vẫn cho xóa rule hoặc đặt `ALLOW`. Như vậy vai trò đọc được sửa một lớp kiểm soát thực thi. Điều này không đồng nghĩa bỏ qua được mọi statutory floor hoặc approval khác.

Nguồn: [role permissions](/services/company/identity/services/tenant-context.service.ts:21), [policy handler](/services/company/operations/handlers/execution-plan.handler.ts:189), [policy mutation](/services/company/operations/services/execution-plan.service.ts:689).

Điều chỉnh: quyền command riêng như `agent.policy.manage`, `execution.plan.approve`, `agent.sweep.manage`; kiểm tra tại service boundary. Áp dụng cùng nguyên tắc cho các command bật sweep và duyệt execution plan, không chỉ ẩn nút trên UI.

**F03. Workspace stage dùng evidence chưa đủ điều kiện và bỏ qua cờ chặn edge.**

`assessVentureStage` lấy toàn bộ evidence workspace, không lọc `approved`, `deletedAt`, `freshUntil`. Evidence candidate/rejected/expired có thể tác động kết quả gate. Khi transition thật, cấu hình edge chỉ được đọc `policyVersion`; `allowed=false` không được thực thi. Hai lỗi trực tiếp ảnh hưởng W-stage, không tự động nâng P-stage.

Nguồn: [evidence selection](/services/company/operations/strategy/services/stage-lifecycle.service.ts:121), [transition check](/services/company/operations/strategy/services/stage-lifecycle.service.ts:211), [edge lookup](/services/company/operations/strategy/services/stage-lifecycle.service.ts:247).

Điều chỉnh: một bộ chọn evidence hợp lệ dùng chung; resolve và enforce edge đang hiệu lực cùng policy liên kết. Journal cần evidence ID/version và policy snapshot, không chỉ số lượng. Test candidate đủ điểm vẫn không qua; gate passed nhưng edge denied vẫn bị chặn.

**F04. Agent nhận sự kiện không đi qua được worker contract.**

`schedule_reference_task` tạo payload có `kind='event_trigger'` nhưng không có `run_id` và `task_type`. Scheduler lưu nguyên payload; worker yêu cầu `run_id` và chỉ dispatch các `task_type` đã biết. Tái hiện offline bằng chính producer và consumer cho kết quả `success=False`, `missing run_id in payload` trước khi chạy agent.

Nguồn: [event producer](/apps/cosa/events/execution_plane_client.py:22), [scheduler storage](/services/cosa/services/control-plane-scheduler.service.ts:88), [worker rejection](/apps/cosa/worker/main.py:305).

Điều chỉnh: contract task có kiểu và version chung; hoặc worker có nhánh `event_trigger`, hoặc producer tạo đầy đủ run task. Run ID phải ổn định khi retry; resolve đúng spec pin trong event. Bổ sung test producer → scheduler record → worker, thay vì test từng bên với payload tự viết.

**F05. Customer Support Copilot đọc context thiếu authorization.**

Copilot gọi capability handler trực tiếp trước kernel, với context chỉ chứa workspace/run. Handler gửi `X-Workspace-Id`; token ambient chỉ được kernel thiết lập trong tool call. Company endpoint yêu cầu authorization. Với composition mặc định, đọc thread thật sẽ bị từ chối trước khi tới model. Kiểm chứng offline với `CompanyServiceClient` thật và HTTP transport giả xác nhận request không có `Authorization`.

Nguồn: [prefetch](/apps/cosa/worker/copilot_run.py:159), [read handler](/apps/cosa/capabilities/engagement_read.py:46), [HTTP header composition](/apps/cosa/capabilities/client.py:166), [Company guard](/services/company/commercial/handlers/customer-engagement/copilot.handler.ts:105).

Điều chỉnh: resolve run/compliance/delegation trước fetch và thực hiện read qua gateway với invocation context chuẩn. Kernel chính có fallback resolve compliance, nên vấn đề ở đây là prefetch nằm trước kernel, không phải kernel thiếu compliance hoàn toàn.

**F06. Copilot báo hoàn tất kể cả kernel thất bại.**

Sau `kernel.run`, worker không kiểm tra `RunStatus`; nếu không có output thì dùng câu trả lời mẫu, tạo artifact ref rồi callback `completed`. Lỗi lưu artifact cũng chỉ được log. Tái hiện offline: kernel trả `FAILED` nhưng callback là `completed` và có một lần tạo artifact.

Nguồn: [output handling](/apps/cosa/worker/copilot_run.py:233), [artifact handling](/apps/cosa/worker/copilot_run.py:280), [success callback](/apps/cosa/worker/copilot_run.py:320).

Điều chỉnh: map đầy đủ completed/failed/waiting/cancelled; validate output có schema; chỉ báo hoàn tất khi artifact nội dung đã lưu và có thể đọc lại. Đối chiếu thêm contract input: worker đặt dữ liệu ở `input.context`, nhưng [kernel](/packages/agent_integrations/openai_agents_sdk/kernel.py:449) ưu tiên chỉ lấy `input.prompt`, nên context đã fetch không tự được đưa vào prompt. Cần một context envelope được kiểm soát thay vì trông chờ hai phía hiểu ngầm.

**F07. Đóng kỳ kế toán chưa khóa đường ghi sổ.**

Close period chỉ đổi `status='CLOSED'`. Đường ghi financial transaction và confirm accounting document không tra kỳ chứa ngày giao dịch/chứng từ. Vì vậy vẫn có thể ghi hoặc xác nhận ngày thuộc kỳ đã đóng. Các migration đã tìm không cung cấp trigger khóa bù cho service.

Nguồn: [close period](/services/company/finance-legal/services/accounting-period.service.ts:79), [transaction insert](/services/company/finance-legal/services/financial-transaction.service.ts:84), [document confirm](/services/company/finance-legal/services/accounting-document.service.ts:115).

Điều chỉnh: xác định rõ kỳ khóa cho loại sổ nào, enforce trong transaction khi posting/confirm/void; ngày hợp lệ và kỳ không chồng lấn; lưu người đóng, snapshot khi đóng; sửa kỳ cũ qua adjustment hoặc reopen có thẩm quyền.

**F08. Hai proposal khác nhau có thể cùng đối soát một bank transaction.**

Service kiểm tra bank transaction `UNRECONCILED` bằng SELECT không khóa. CAS chỉ đặt trên proposal riêng; UPDATE bank transaction không kiểm lại trạng thái. Hai transaction đồng thời có thể chấp nhận hai proposal, trong khi bank row cuối cùng chỉ trỏ tới chứng từ của lần ghi sau.

Nguồn: [read bank transaction](/services/company/finance-legal/services/reconciliation-proposal.service.ts:104), [proposal CAS và bank update](/services/company/finance-legal/services/reconciliation-proposal.service.ts:141).

Điều chỉnh: khóa bank row hoặc conditional update `status=UNRECONCILED` với kiểm tra affected row; ràng buộc uniqueness nếu nghiệp vụ là một đối một. Với thanh toán một phần/nhiều chứng từ, cần bảng allocation và tổng số tiền đối soát. Đây là kết luận từ interleaving SQL, chưa chạy concurrency test với Postgres.

**F09. Snapshot cộng tiền khác currency như cùng đơn vị.**

Bank ingestion nhận currency, nhưng `computeSnapshot` chỉ dùng amount/direction/date; query lấy toàn workspace. Nếu có VND và USD, cash/burn/runway không còn đúng đơn vị. Phép tính còn dùng `parseFloat`/JavaScript number cho money.

Nguồn: [bank currency](/services/company/finance-legal/services/bank-transaction.service.ts:120), [snapshot calculation](/services/company/finance-legal/services/financial-snapshot.service.ts:85), [workspace-wide input](/services/company/finance-legal/services/financial-snapshot.service.ts:136).

Điều chỉnh: trước mắt chặn hoặc tách snapshot theo currency; sau đó reporting currency, tỷ giá và ngày tỷ giá, Decimal/minor units. Tách luồng chuyển nội bộ khỏi thu/chi hoạt động nếu dùng snapshot để ra quyết định burn. Lỗi cộng currency chỉ phát sinh khi dữ liệu có nhiều đồng tiền.

**Các điều chỉnh P2 — làm logic và trải nghiệm nhất quán**

**F10. Mục tiêu tuần luôn ghi vào tuần 1.** Service chọn cycle mới nhất không xét trạng thái/tuần hiện tại, rồi upsert `weekNo:1`. Đổi mục tiêu ở tuần 2 trở đi ghi đè lịch sử tuần đầu. Cần week identity rõ: cycle + weekNo + date range/timezone, không suy ra bằng cycle mới nhất. [Code](/services/company/operations/strategy/services/weekly-goal.service.ts:59).

**F11. Tab 12WY có thao tác chỉ tồn tại ở client.** `getDashboard(projectId)` bỏ projectId, lấy `cycles.first` và trả tactics/scores rỗng; `createTactic` chỉ dựng object với timestamp ID, `createOrGetCycle` chỉ đọc, update/review trả null. Cần nối API persistence và project scope; nếu chức năng chưa hỗ trợ thì trả trạng thái có cấu trúc, không thể hiện như đã tạo thành công. [Code](/frontend/lib/modules/strategy/services/twelve_wy_service.dart:35).

**F12. PMF có thể PROMISING khi không có evidence approved.** Cờ `NO_REVIEWED_EVIDENCE` được tính trước khi lọc approved. Có một candidate/rejected, metric 0.8 và đủ contract có thể làm missing flag rỗng, valid evidence rỗng nhưng kết quả vẫn PROMISING. Mọi metric còn bị clamp về [0,1], không xét đơn vị hoặc chiều tốt/xấu. Cần kiểm tra đầu vào sau lọc; scoring theo contract, cohort, metric direction và quality. [Code](/services/company/operations/strategy/services/pmf-scoreboard.service.ts:115).

**F13. Next best actions của project dùng assumption mẫu.** Handler luôn đưa assumption `id=1`, “Customer problem validation”, importance/uncertainty 8; không đọc project context thật. Cần lấy dữ liệu workspace/project đã kiểm quyền, trả insufficient data nếu thiếu; giữ Snowflake ID dạng string thay vì `Number`. [Code](/services/company/operations/strategy/handlers/next-best-action.handler.ts:49).

**F14. Sửa kickoff giữ nguyên action ID không cập nhật task.** Materializer chỉ xử lý added/removed. Đổi “phỏng vấn 3 khách” thành “10 khách” có thể để task/commitment giữ yêu cầu cũ. Cần diff changed, cập nhật nội dung và giữ tiến độ, hoặc version/change order sau activation. [Code](/services/company/operations/strategy/services/project-kickoff-materialize.service.ts:98).

**F15. Legal có hai lệch enum làm mất nghĩa vụ khỏi đánh giá.** Migration 25 đổi `REGISTERED_VERIFIED` sang `VERIFIED`, nhưng rule seed migration 14 còn status cũ; evaluator so sánh literal. Bên cạnh đó create obligation ghi `OPEN`, trong khi action context chỉ lấy `PENDING`. Cần migration đồng bộ predicate, enum chung, test toàn chuỗi create obligation → action context. Applicability hiện lấy `profiles[0]` và chỉ xét `entity_status`, chưa evaluate đầy đủ điều kiện accounting regime trong predicate: cần evaluate từng pháp nhân bằng rules có kiểu.

Nguồn: seed `14_legal_seed_tt58_nq86.up.sql:46` và migration `25_legal_entity_status_v2.up.sql:12` (cả hai đã bị squash baseline `81461673` gộp vào `001_founder_trial_mvp_baseline`), [evaluator](/services/company/finance-legal/services/legal-applicability.service.ts:29), [OPEN](/services/company/finance-legal/services/legal-obligation.service.ts:162), [PENDING](/services/company/operations/strategy/services/next-best-action.service.ts:82).

**F16. Founder của AI deployment được gán bằng caller, chưa xác minh role.** Create handler chỉ kiểm membership rồi ghi caller vào `founderMemberId`; approve service kiểm ID người duyệt có bằng trường này. Thành viên tạo deployment có thể trở thành “founder” của deployment theo logic dữ liệu. Cần resolve founder/approver thực từ quyền workforce, phân tách reviewer và approver theo mức rủi ro. Đây là lỗi authority của hồ sơ; không kết luận nó vượt mọi runtime gate: runtime vẫn có kiểm tra applicability/compliance riêng.

Nguồn: [create handler](/services/company/finance-legal/handlers/ai-compliance-governance.handler.ts:60), [approval identity check](/services/company/finance-legal/services/ai-compliance-governance.service.ts:206).

**Agent cần điều chỉnh và bổ sung gì**

| Agent đang seed | Khả năng thực tế từ spec | Đề xuất |
|---|---|---|
| Operations / founder_assistant | list/read/create draft task; pinned skill lifecycle/weekly review/SOP | Bổ sung read project, next actions, weekly plan, metric và evidence theo nhiệm vụ; output phải gắn artifact/evidence và tiêu chuẩn hoàn thành |
| Finance | Chỉ có `finance.transaction.record`; skill runway/budget/unit economics là hướng dẫn | Ưu tiên transaction/snapshot/document read và calculation tool xác định; sau đó đề xuất phân loại/đối soát. Không coi agent này đã là CFO hoặc executor thanh toán |
| Marketing | Marketing context read và web search; nhiều skill nội dung/chiến lược | Nối experiment/evidence/CRM outcome; mọi kết luận có nguồn và dữ liệu dự án. Chỉ mở write theo workflow đã phê duyệt |
| Customer Support Copilot | Read thread/customer/knowledge, draft; có lỗi F05/F06 | Sửa run pipeline, context, schema output và artifact persistence trước |
| Customer Support Autopilot | Read/draft/send/handoff theo spec | Sửa F04; dùng resume chuẩn có approval/checkpoint; test disable rule, takeover, retry và lỗi đọc trạng thái trước khi bật tự động |
| Strategy / Legal | Chưa có profile riêng trong danh sách deployed, dù capability/skill nghiệp vụ đã tồn tại | Trước mắt compose role/skill/workflow vào agent hiện có; tạo profile riêng khi có phạm vi quyết định, owner, bộ quyền và eval riêng |

Nguồn: [deployed AgentSpecs](/apps/cosa/agents/specs.py:52), [capability registration](/apps/cosa/composition/capability_registration.py:124).

Có hai khoảng trống đã kiểm chứng cụ thể:

- Operations pin `lifecycle.context-resolver` và `lifecycle.next-best-action`, nhưng thiếu `strategy.project.get` và `strategy.next_best_action.get` trong capability refs. Kernel chỉ dựng tools từ refs; pin skill chỉ thêm instructions. Cần readiness validator `required tools ⊆ agent capabilities`, không tự mở quyền chỉ vì skill yêu cầu. [Kernel](/packages/agent_integrations/openai_agents_sdk/kernel.py:147).
- `knowledge.profile.read` hiện trả object mẫu, insights rỗng và source attribution `curated_knowledge`, không đọc repository. Tham số `include_untrusted=true` lại làm output `untrusted=false`. Cần nối tri thức đã publish, source/version/freshness và provenance thực; không dùng boolean lọc để đổi độ tin cậy dữ liệu. [Handler](/apps/cosa/capabilities/knowledge_read.py:74).

Workflow payout có tên `finance.payout.execute`, nhưng capability đó không được đăng ký trong composition hiện tại. Nên gắn trạng thái chưa hỗ trợ cho workflow cho tới khi có executor và cơ chế xác nhận kết quả ngân hàng; “record transaction” không tương đương “đã chuyển tiền”. [Workflow](/apps/cosa/workflows/specs.py:7).

**Vòng nghiệp vụ nên hoàn thiện**

`Project context + hypothesis → evidence/metric đủ chuẩn → gate evaluation → decision có thẩm quyền → kế hoạch tuần + budget + legal obligations → task/agent run → artifact + kết quả đo được → weekly review → quyết định/kế hoạch tiếp theo`.

Các bổ sung cụ thể, tách khỏi lỗi hiện hữu:

1. **Decision gắn execution:** lưu evaluation ID, decision ID, policy/evidence version và project stage; tiến/lùi/pivot/hold/kill có lý do. Project transition hiện kiểm edge boolean, nên việc bắt buộc gate evaluation là bổ sung quy tắc nghiệp vụ cần thống nhất.
2. **Definition of done:** task hoàn tất cần outcome/artifact đã kiểm tra. WGA hiện đổi task sang done khi kernel COMPLETED; một phản hồi model hoàn tất chưa chứng minh mục tiêu nghiệp vụ đã đạt. Rollup commitment, weekly score và outcome score cần phân biệt hoàn thành hoạt động với đạt chỉ số. [WGA](/apps/cosa/worker/wga_run.py:338).
3. **Finance gắn initiative/project:** budget envelope, actual/committed/forecast, variance và allocation rõ. Xác định ranh giới bank transactions, manual financial transactions, accounting documents và management snapshots; thêm reconciliation giữa các góc nhìn, không cộng gộp dễ trùng.
4. **Legal obligation có vòng đời:** owner, legal entity, nguồn/version, due date tính theo kỳ, evidence hoàn thành, review, reminder/escalation và exemption có lý do; obligation đang mở cần xuất hiện ở planning/weekly review.
5. **Một run contract chung:** các đường chat, schedule, event, copilot và WGA dùng cùng resolve spec → policy/compliance → context → kernel → validate result → artifact → callback. Các wrapper chỉ khác input và UX.
6. **Eval nghiệp vụ thật:** tình huống input thay đổi phải làm output/decision thay đổi; test mô hình dữ liệu, permissions, side effect và sự kiện cuối cùng. Một số autopilot eval hiện kiểm dict được dựng sẵn, không gọi agent/gateway; pass các case đó chưa chứng minh FAQ/handoff/approval hoạt động. [Eval implementation](/apps/cosa/evals/customer_support_autopilot_cases.py:60).

**Thứ tự triển khai đề xuất**

- Đợt 1: F01/F02, quyền AI deployment, transition gate/edge; bổ sung negative tests tenant/role/state.
- Đợt 2: F04/F05/F06, tuần hiện tại và 12WY persistence; test xuyên producer–consumer và UI–API.
- Đợt 3: khóa kỳ, reconciliation concurrency, currency, legal enum/applicability và PMF scoring.
- Đợt 4: khép vòng decision–execution–review, chuẩn hóa context/capability readiness, rồi mới mở thêm role hoặc tăng autonomy.

**Bằng chứng kiểm tra và giới hạn**

- 37 Python tests hiện có về AgentSpec, worker/Copilot/autopilot và delegation: pass.
- 21 TypeScript tests thuần về deterministic strategy, JSON và snapshot calculation: pass; DB URL giả loopback cổng 1 để không chạm DB đang chạy.
- Kiểm chứng offline dùng hàm production và dependency giả: event payload bị worker từ chối; Copilot prefetch không có Authorization; kernel FAILED vẫn callback completed; knowledge trả dữ liệu mẫu; Operations thiếu hai capability mà pinned skill yêu cầu.
- 19 Flutter tests của service 12WY: pass. Test hiện có bao gồm kỳ vọng stub/null, nên không chứng minh persistence. Tổng ba nhóm test được chọn: 77 pass.
- Không thay đổi application code, không migrate/deploy, không kiểm tra trên dữ liệu production. Các lỗi SQL concurrency/tenant/lifecycle nêu ở trên được trace tĩnh qua caller–service–schema; cần regression test Postgres dùng dữ liệu cô lập khi sửa. Không suy diễn kết quả bộ test hẹp thành toàn hệ thống đã ổn.
