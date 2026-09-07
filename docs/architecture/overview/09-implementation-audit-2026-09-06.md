# Kiểm tra implementation sau Antigravity — overview 07 + 08

Ngày kiểm tra: 2026-09-06. Baseline trước triển khai: `e4829b75`. Mốc code chốt cho báo cáo: `527aced4580ad70ede7a59e761dd029ab3e84cfa` trên main. Trong lúc kiểm tra, HEAD đi từ `4efac4bd` qua `d8f8e9db` tới `527aced4`; phần Cas F2/F3 đã được đọc lại ở mốc cuối. Các plan/overview đang là file untracked trong workspace, vẫn được dùng làm yêu cầu. Không sửa application code, không commit hoặc gọi ngân hàng thật.

**Kết luận: chưa triển khai đúng và đủ để nghiệm thu plan tổng.** Có nhiều cấu phần mới hữu ích, nhưng còn đường public bỏ qua quyền, helper không có caller production, UI vẫn dùng stub và test không chứng minh luồng thật. F4/F5/F6 và H1 chưa có các đầu ra chính. Không thể dùng tên commit hoặc số test pass để đánh dấu các task đã xong.

Nguồn yêu cầu: [plan tổng](/docs/superpowers/plans/2026-09-05-business-agents-master.md), [permissions](/docs/superpowers/plans/2026-09-05-business-agents-permissions.md), [strategy/operating](/docs/superpowers/plans/2026-09-05-business-agents-strategy-operating.md), [runtime](/docs/superpowers/plans/2026-09-05-business-agents-runtime.md), [legal](/docs/superpowers/plans/2026-09-05-business-agents-legal.md), [finance](/docs/superpowers/plans/2026-09-05-business-agents-finance.md).

## 1. Ma trận 24 task

“Một phần” nghĩa là có implementation, không đồng nghĩa đã wired/verified. “Chưa có” dựa trên tìm cả tên file dự kiến lẫn capability/route/caller tương đương, không chỉ kiểm tên file.

| Task | Trạng thái nghiệm thu | Có gì / còn thiếu |
|---|---|---|
| H0 | Có runner; DB thực chưa kiểm chứng được | 5 unit tests pass. Runner disposable không kết nối được admin Postgres local với cấu hình hiện có |
| A1 | Chưa đạt | Có guard và tenant checks mới; setter capability policy vẫn chỉ kiểm membership qua handler |
| A2 | Một phần | Catalog/role/assignment/evaluator có; chưa áp trên toàn bộ command, bootstrap và quản lý quyền còn thiếu điều kiện |
| A3 | Chưa đạt | Có policy reference và evaluation client; chưa được gateway sử dụng để quyết định side effect |
| A4 | Một phần | Có UI/controller/API permissions; UI không bảo đảm quyền thay đổi thực sự điều khiển mọi hành động |
| S1 | Chưa đạt | Có evidence helper và sửa project/PMF một phần; W-stage vẫn dùng toàn bộ evidence và bỏ allowed của edge |
| S2 | Một phần | Có calendar, revision và changed kickoff; còn đường kickoff/cycle/weekly chưa theo một nguồn lịch |
| S3 | Chưa đạt | Có observation/completion services; chưa nối đầy đủ tới API/worker; score/criteria còn có đường bỏ qua evidence |
| S4 | Một phần | Có context thật; decision–execution–review và kiểm scope/version chưa khép đầy đủ |
| S5 | Chưa đạt | Có DTO và API client mới; màn hình cũ vẫn đi qua getDashboard/createTactic stub |
| R1 | Chưa đạt | Có envelope/scheduler changes; event metadata chưa đủ cho handler run thực, pin/authority chưa được dùng nhất quán |
| R2 | Chưa đạt | Có trạng thái và context tốt hơn; Copilot gọi sai ArtifactRepository.get; WGA completion endpoint chưa tồn tại |
| R3 | Chưa đạt | Có knowledge/readiness helper; composition không inject knowledge repo; readiness chưa có consumer production |
| R4 | Chưa đạt | Có eval/restart tests; nhiều test dựng kết quả hoặc truyền checkpoint qua Queue, không chạy persistence/gateway thật |
| L1 | Chưa đạt | Có typed predicates/evaluation records; chưa correction literal cũ, chưa enforce legal review và fiscal profile theo entity |
| L2 | Chưa đạt | Có authority mới ở create/approve; resume còn fallback authority cũ, chưa kiểm thu hồi quyền đầy đủ |
| L3 | Một phần | Có lifecycle/journal/UI mới; cần nối màn hình/legal review thật và bỏ đường fulfill thiếu evidence |
| F1 | Một phần | Có row locking/conditional reconciliation/currency filter; thiếu entity isolation đầy đủ, money/coverage còn sai |
| F2 | Chưa đạt | Create grantToken có HTTP thật; exchange vẫn mock, callback state không hoàn thiện, reauthorize tin input caller |
| F3 | Chưa đạt | Có cron/inbox/normalizer/sync thật; sai contract Cas, crash PROCESSING kẹt, correction bị dedup mất |
| F4 | Chưa có đầu ra chính | Không có payment request/QR/settlement allocation theo plan; payout workflow cũ vẫn còn |
| F5 | Chưa có đầu ra chính | Không có bộ book/report mapping TT58 đã kiểm chứng và fixtures nguồn/reviewer |
| F6 | Chưa có đầu ra chính | Không có payment Flutter flow/budget summary hoàn chỉnh; FinanceTT58Service vẫn throw |
| H1 | Chưa có | Chưa có business_operating_loop E2E/Flutter integration và release evidence theo plan |

## 2. Phát hiện cần sửa trước khi tăng mức tự động hóa

### IA01 — P1: Auditor vẫn sửa được capability policy; F02 chưa được đóng

[setCapabilityPolicyService](/services/company/operations/services/execution-plan.service.ts:690) không gọi requireFounderCommand/requireCommandAuthority; lấy workspaceId từ tham số và ghi rule trực tiếp. [Handler](/services/company/operations/handlers/execution-plan.handler.ts:202) chỉ xác thực membership.

Tình huống: auditor gọi POST `/operations/capability-policy` với decision ALLOW hoặc null vẫn tới insert/delete. Việc đã tạo command-authority helper không bảo vệ đường này. Direct service còn không so workspace tham số với ctx; public route thường lấy cùng workspace từ handler nên không gộp hai vấn đề thành kết luận public cross-tenant chưa được chứng minh.

Cần đưa authorization vào chính service, lấy workspace từ ctx và test public handler + setter + row/outbox. Không chỉ test helper từ chối auditor.

### IA02 — P1: Permissions mới chưa điều khiển runtime và nhiều command nghiệp vụ

[requireFounderCommand](/services/company/identity/services/command-authority.service.ts:12) vẫn chỉ kiểm tên role; evaluator đầy đủ là helper khác. Python [company_policy_client.py](/apps/cosa/policies/company_policy_client.py) có evaluate_business_action nhưng chưa có caller production. `businessPolicyRef` được thêm vào snapshot nhưng chưa tạo quyết định Company bắt buộc ở gateway; bản client còn dùng base URL mặc định của control plane cho route evaluate thuộc Company.

Tình huống: founder đặt DENY trong bảng permissions mới nhưng đường đang gọi guard role cũ hoặc policy cũ không đọc quyết định này; giao diện và quyền thực thi không đồng nhất. Không kết luận các hard floor/connector guard sẵn có đều bị vượt: vấn đề là lớp business policy mới chưa được nối.

Cần một writer/source cho quyền nghiệp vụ, client đúng plane/token, evaluation trong gateway trước side effect/resume và recheck service. Negative test phải thay DB policy rồi chạy command/tool thật.

### IA03 — P1: W-stage vẫn dùng evidence chưa duyệt và bỏ cờ chặn edge; F03 còn nguyên

[stage-lifecycle.service.ts:121](/services/company/operations/strategy/services/stage-lifecycle.service.ts:121) vẫn chọn tất cả evidence workspace, không lọc status/deletedAt/freshUntil. [Edge lookup](/services/company/operations/strategy/services/stage-lifecycle.service.ts:247) chỉ đọc policyVersion.

Tình huống: candidate/expired evidence đủ điểm vẫn có thể góp vào assessment; edge allowed=false không được dùng ở luồng workspace transition. Evidence helper mới ở file khác không sửa được caller này. Cần test transition thật, gồm gate pass nhưng edge deny và candidate-only.

### IA04 — P1: Project transition chưa bắt buộc decision/gate hợp lệ; PMF chưa hiểu đơn vị đo đầy đủ

[Project transition](/services/company/operations/strategy/services/project-stage-lifecycle.service.ts:142) chỉ kiểm decision khi caller có truyền `decisionId`. Có thể bỏ tham số và đi đường trước đây. Khi có decision, chưa resolve đầy đủ evaluation/policy/evidence freshness theo S1. PMF có sửa missing approved evidence nhưng vẫn chuẩn hóa giá trị metric bằng clamp [0,1] thay vì metric contract/cohort/direction.

Cần bắt buộc decision/evaluation phù hợp khi chuyển tới stage yêu cầu gate; không biến field optional thành biện pháp kiểm soát. Test tỷ lệ giảm, số đếm và stale contract bằng production evaluator.

### IA05 — P1: 12WY UI vẫn báo tạo công việc mà không lưu; F11 chưa sửa

[getDashboard](/frontend/lib/modules/strategy/services/twelve_wy_service.dart:35) vẫn bỏ projectId, chọn cycles.first, trả tacticsByWeek/weeklyScores rỗng. createTactic vẫn sinh ID timestamp tại client; updateTactic/generateWeeklyReview trả null. Method getExecutionCycleView mới chưa thay thế luồng UI đang dùng các method cũ.

Tình huống: tạo tactic rồi reload mất dữ liệu; đổi project có thể vẫn xem cycle đầu tiên. Test DTO/new endpoint riêng pass không chứng minh màn hình đã chuyển sang API thật. Cần thay caller/controller/mixin, kiểm request/persist/reload và stale response khi đổi project.

### IA06 — P1: Copilot gọi sai chữ ký repository, làm output hợp lệ bị báo thất bại

[copilot_run.py:323](/apps/cosa/worker/copilot_run.py:323) gọi `get(artifact_ref)`; [ArtifactRepository protocol](/packages/agent/artifacts/repository.py:19) yêu cầu `get(workspace_id, artifact_id)`. Repository thật/InMemory sinh TypeError; exception bị bắt và artifact_persisted=false.

Đã tái hiện offline bằng repository thật: `InMemoryArtifactRepository.get() missing 1 required positional argument: 'artifact_id'`. Mock AsyncMock nhận mọi argument che lỗi này. Ngoài ra branch không có artifact_repository lại đặt artifact_persisted=true, trái yêu cầu fail khi không có nơi lưu. Cần test protocol có spec/autospec và artifact content thực, không chỉ metadata/object_ref.

### IA07 — P1: Knowledge/readiness có code nhưng chưa được nối vào agent plane

[register_cosa_capabilities](/apps/cosa/composition/capability_registration.py:132) nhận knowledge_snapshot_repo tùy chọn; [build agent plane](/apps/cosa/composition/agent_plane.py:236) không truyền repository. Runtime mặc định không có nguồn knowledge mới. [capability_readiness.py](/apps/cosa/agents/capability_readiness.py) chưa có caller production thực thi readiness khi activation/run.

Trả UNAVAILABLE trung thực hơn stub cũ, nhưng không đạt R3 “knowledge thật”. Cần inject storage repo, test boot composition và run tool thật; thiếu required tool phải chặn activation thay vì chỉ hiển thị helper output.

### IA08 — P1: Cas Link chưa thể hoàn tất grant thật; có đường tự cấp lại consent

[Create link](/services/company/finance-legal/services/cas-link.service.ts:124) không đưa state vào link/callback hay trả state cho client, trong khi exchange bắt đúng stateHash đã lưu. Test có thể đọc hash từ DB, người dùng browser không có nguồn lấy hash đó.

[Exchange](/services/company/finance-legal/services/cas-link.service.ts:193) không sử dụng publicToken để gọi Cas: tạo `grant_mock_*`, `acc_mock_*`, secretRef giả rồi ghi GRANTED. [Reauthorize handler](/services/company/finance-legal/handlers/cas-link.handler.ts:102) truyền sameAccountVerified do caller nhập; [service](/services/company/finance-legal/services/cas-link.service.ts:299) dùng boolean đó để đưa connection về GRANTED mà không có provider proof.

Tình huống: cấp publicToken bất kỳ với session/hash hợp lệ vẫn tạo “đã kết nối”; member có membership gửi sameAccountVerified=true có thể tự đổi consent state của connection workspace. Đây là lỗi nghiệp vụ, không phải đơn thuần thiếu credential. Cần exchange thật, state roundtrip đúng, vault storage và server-side identity verification; revoke/reauthorize phải kiểm command permission.

### IA09 — P1: Contract Cas trong code không khớp tài liệu được chọn

[cas-client.ts](/services/company/finance-legal/services/cas-client.ts:122) dùng `/tokens/exchange` và public_token, trong khi Cas công bố `/grant/exchange` với publicToken và developer headers. GET client thiếu developer/version headers; client đọc data/cursor trong khi cas-contract.ts của chính repo khai records/page. [Nguồn Cas Transactions](https://cas.so/product/transactions/).

[Webhook handler](/services/company/finance-legal/handlers/cas-webhook.handler.ts:5) vẫn yêu cầu field rawPayload:string thay vì nhận body raw JSON. [Parser](/services/company/finance-legal/services/cas-webhook.service.ts:75) chờ error=0/data; mẫu Cas QR Pay dùng webhookType/grantId/transaction, nên nếu gửi nguyên mẫu đó qua adapter hiện tại sẽ thành IGNORED hoặc bị boundary từ chối. Cơ chế signature trong contract/handler cũng khác nhau và chưa có evidence nhà cung cấp xác nhận. [Mẫu Cas QR Pay](https://cas.so/product/qr-pay/).

Không gọi API ngân hàng thật trong audit; kết luận là mismatch tĩnh với contract công khai và nội bộ, không suy diễn đã test live. Cần lưu fixture/provider version đã kiểm chứng rồi contract-test raw HTTP request thật.

### IA10 — P1: Inbox không khôi phục bản ghi đã claim khi worker chết

[claimDueCasInboxEvents](/services/company/finance-legal/services/ingestion.service.ts:200) chỉ chọn RECEIVED/FAILED; ngay sau claim đổi PROCESSING. Nếu process chết trước complete/fail, lease hết hạn nhưng status vẫn PROCESSING và không bao giờ được query này chọn lại. Không tìm thấy sweeper khác chuyển PROCESSING hết lease về trạng thái có thể claim.

Test mang tên crash-then-resume hiện kiểm crash sau enqueue, trước claim; không chạm lỗi sau claim. Cần test worker thật chết sau PROCESSING rồi process khác reclaim với fencing token mới. Đây là gap F3 durability có thể làm giao dịch đã ACK bị kẹt vĩnh viễn.

### IA11 — P1: Correction cùng transaction ID bị dedup trước khi tới kiểm tra conflict

[enqueueCasInboxEvent](/services/company/finance-legal/services/ingestion.service.ts:158) onConflictDoNothing theo event identity; identity ghép connection/transaction/kind/contract version, không provider revision. Payload cùng ID đổi amount/status bị trả lại inbox cũ, payload mới không được lưu hoặc xử lý.

Worker có kiểm content hash khác ở [cas-inbox-worker.service.ts](/services/company/finance-legal/services/cas-inbox-worker.service.ts:135), nhưng duplicate nói trên không tới worker. Cần tách delivery/event revision identity và transaction identity; luôn lưu correction evidence, không overwrite tiền đã đối soát.

### IA12 — P1: Finance snapshot gắn nhãn pháp nhân nhưng cộng toàn workspace

[calculateAndSaveSnapshotService](/services/company/finance-legal/services/financial-snapshot.service.ts:181) chỉ lọc bank transactions theo workspace/currency, không join connection/entity, sau đó gắn legalEntityId vào snapshot. Migration [35](/services/company/finance-legal/migrations/35_financial_integrity.up.sql:18) unique(workspace,date,currency) không gồm entity. Hai entity cùng ngày/currency không lưu riêng được; query không có entity còn có thể lấy snapshot một entity rồi đổi thành workspace aggregate.

computeSnapshot vẫn parseFloat, missing opening balance mặc định 0; bank rows thực tế không mang classification được helper dùng để loại transfer/capital. Vì vậy test truyền category vào hàm thuần không chứng minh burn từ DB đã đúng. Đã tái hiện offline: không truyền opening balance, chỉ giao dịch IN=100 vẫn trả currentCash=100, không thể hiện coverage/unknown.

Cần entity-scoped query/unique key, source balance/coverage và classification provenance. Helper Money mới không đủ nếu calculation path vẫn dùng Number.

### IA13 — P1: Amount string bị đổi qua Number trước khi vào Money, mất chính xác

[cas-normalizer.ts](/services/company/finance-legal/services/cas-normalizer.ts:148) đổi string sang Number rồi Math.abs trước parseDecimalToMoney. Probe chạy chính hàm production với dependency DB/provider không hoạt động: input `9007199254740993` VND → output amountMinor `9007199254740992`.

Cần parse dấu và decimal bằng string/NUMERIC, không đi qua float; kiểm currency decimals và reject fraction không hợp lệ thay vì cắt âm thầm. Đây là sai số tái hiện được, dù ví dụ lớn hơn giao dịch thường gặp.

### IA14 — P1: Chưa có luồng chi QR, sổ TT58 và budget/UI theo plan

Tìm toàn code không thấy payment-request/payment-allocation/payment-qr/book-report mapping/budget summary tương đương F4–F6. [FinanceTT58Service](/frontend/lib/modules/finance/services/finance_tt58_service.dart:1) vẫn throw UnimplementedError; [workflow payout](/apps/cosa/workflows/specs.py:28) vẫn tham chiếu finance.payout.execute.

Không thể nghiệm thu yêu cầu founder duyệt/quét QR/đối soát hoặc TT58 theo pháp nhân/kỳ. Cần thực hiện F4–F6 sau khi F1–F3 được sửa; không triển khai executor tự chuyển tiền thay cho yêu cầu đã thống nhất.

### IA15 — P1: Roles chưa được cấp phát; lưu permissions có thể xóa hạn mức

[Migration permissions](/services/company/identity/migrations/8_business_permissions.up.sql) tạo bảng và seed permission definitions, nhưng không seed/backfill roles/assignments. Không tìm thấy production writer tạo coreWorkspaceRoles; tests tự insert. PUT chỉ chấp nhận role đã có tại [permissions.service.ts:284](/services/company/identity/services/permissions.service.ts:284). Workspace sạch mở Settings sẽ không có role để chỉnh/assign.

[Flutter controller:84](/frontend/lib/modules/settings/controllers/permissions_controller.dart:84) gửi effect mà không giữ conditions; [backend:310](/services/company/identity/services/permissions.service.ts:310) thay conditions thiếu bằng `{}`. Đổi effect rồi Save có thể làm mất maxAmountMinor/currency đang áp dụng. Cần bootstrap/backfill có kiểm chứng và semantics patch bảo toàn fields không được chỉnh; thêm UI assignment/scope/expiry/limit.

### IA16 — P1: Rule có hạn mức vẫn ALLOW khi thiếu amount facts

[permission-evaluator.ts:55](/services/company/identity/services/permission-evaluator.ts:55) chỉ kiểm conditions trong `if (bestRule.conditions && facts?.amount)`. [Business policy service:49](/services/company/identity/services/business-policy.service.ts:49) forward facts, không resolve resourceRef thành amount/currency/version chuẩn từ DB; resourceVersion được echo lại.

Tình huống: role ALLOW maxAmountMinor=100, gọi evaluate cho resource giá trị 1000 nhưng không truyền facts vẫn ALLOW. Cần fail closed khi thiếu facts bắt buộc, resolve facts server-side và bind decision vào resource/policy version thật. Không được tin amount/version do agent tự khai.

### IA17 — P1: Resume deployment dùng quyền người duyệt cũ, bỏ qua revocation

[Resume handler](/services/company/finance-legal/handlers/ai-compliance-governance.handler.ts) không truyền ctx vào service. [Fallback:453](/services/company/finance-legal/services/ai-compliance-governance.service.ts:453) chỉ so resumedByMemberId với founderMemberId/approvedByMemberId.

Người từng approve, sau đó bị thu hồi ai.deployment.approve nhưng vẫn là member, còn có thể resume deployment nếu không có CRITICAL incident. Review/suspend cũng chưa kiểm action permission. Cần bắt buộc ctx ở service và kiểm quyền hiện tại/proof/assessment version khi approve/resume; test revocation qua handler thật. approvedVersion hiện chỉ là counter, snapshot chưa bind business policy/authority version.

### IA18 — P1: Nghĩa vụ có thể được đóng bằng evidence rỗng hoặc miễn trừ không căn cứ

[transitionObligationStatus:289](/services/company/finance-legal/services/legal-obligation.service.ts:289) không authorize legal.obligation.manage. Check FULFILLED chỉ cần evidenceRefs có phần tử; `[""]` cũng qua. EXEMPT không bắt rationale/căn cứ. Handler chỉ requireWorkspaceAccess.

Auditor có membership có thể đóng nghĩa vụ bằng các payload trên; không query artifact để kiểm tenant, review status, freshness hoặc quan hệ với nghĩa vụ. Cần authority ở service, kiểm evidence thật và căn cứ miễn trừ. Không dùng widget test mock transition thành công làm bằng chứng enforcement.

### IA19 — P1: Legal predicate cũ chưa sửa; kết quả NEEDS_REVIEW bị giấu

[Migration 32](/services/company/finance-legal/migrations/32_legal_predicate_versions.up.sql) chưa tạo corrected predicate version/supersedes/source cho literal entity_status=APPROVED. [Evaluator:67](/services/company/finance-legal/services/legal-predicate.ts:67) so literal trực tiếp nên entity VERIFIED vẫn không match rule cũ. Test tự seed VERIFIED không kiểm backfill này.

[Applicability:124](/services/company/finance-legal/services/legal-applicability.service.ts:124) đọc legalReviewConfirmed nhưng không dùng để chặn; version chưa review vẫn có thể APPLIES. [Dòng 189](/services/company/finance-legal/services/legal-applicability.service.ts:189) bỏ qua NEEDS_REVIEW khi trả API, khiến UI không phân biệt thiếu facts với không có nghĩa vụ.

Fiscal profile mặc định còn chọn bản ghi đầu workspace tại dòng 83, không bind entity/năm hiện hành; factsVersion hardcode 1.0 và evaluation conflict ghi đè provenance. Cần correction version có nguồn, reviewed-only rule activation, trả trạng thái cần review và fiscal facts có lịch sử theo entity.

### IA20 — P1: Accept proposal chưa kiểm cycle tenant/project và chưa chống accept đồng thời

[project-action-context.service.ts:526](/services/company/operations/strategy/services/project-action-context.service.ts:526) dùng cycleId input để insert weekly plan mà không resolve twelveWeekCycles.workspaceId/projectId hoặc kiểm week range. Biết cycle ID workspace B có thể tạo weekly plan workspace A tham chiếu B nếu FK hiện tại cho phép; project A cũng gắn cycle project B. weekNo=999 không bị chặn ở đường này.

[UPDATE:512](/services/company/operations/strategy/services/project-action-context.service.ts:512) không có revision/source status predicate và SELECT không lock. Hai request cùng đọc PROPOSED có thể cùng tạo decision/commitment/outbox. Đường execution plan accept tương tự: [execution-plan.service.ts:471](/services/company/operations/services/execution-plan.service.ts:471) đọc draft rồi UPDATE chỉ theo id. Đây là trace SQL tĩnh, chưa chạy race DB trong audit.

Cần resolve cycle cùng tenant/project, kiểm tuần/lịch/owner/purpose và transaction CAS/unique idempotency. Test concurrent phải đi public service mới, không legacy acceptActionProposalService có handler khác.

### IA21 — P1: Weekly API chưa hỗ trợ N tuần đầy đủ; vẫn fallback ghi tuần 1

[weekly-goal.handler.ts:7](/services/company/operations/strategy/handlers/weekly-goal.handler.ts:7) thiếu cycleId/weekNo/expectedVersion mới; setup handler cũng không forward cycleDurationWeeks. [weekly-goal.service.ts:78](/services/company/operations/strategy/services/weekly-goal.service.ts:78) mặc định tuần 1 khi không resolve được tuần hiện tại. Cycle kết thúc hoặc NEEDS_SETUP có thể tiếp tục upsert tuần 1.

Cần đưa contract chọn cycle/tuần/version qua handler thực; ngoài cycle phải trả trạng thái rõ, không tự chọn tuần 1. N tuần là độ dài cycle do founder quyết định; 12 chỉ là mặc định/phương pháp. Phải test 2/6/12/16 tuần từ setup đến weekly/review thay vì chỉ helper date.

### IA22 — P1: Outcome thật vẫn current/target; execution score giả định DONE đủ evidence

[okr.service.ts:200](/services/company/operations/services/okr.service.ts:200) vẫn ghi currentValue trực tiếp, dòng 250 dùng current/target. Baseline churn=10, target=5, current=8 có thể score 1 thay vì progress 0.4. Helper progress mới và recordKrObservation chỉ có test callers; KR links mới cũng chưa có flow production hoàn chỉnh.

[execution-cycle-view.service.ts:283](/services/company/operations/services/execution-cycle-view.service.ts:283) truyền hasEligibleEvidence=true cho mọi commitment, không đọc evidence. Denominator là danh sách hiện tại, không frozen committed scope đầu tuần. DONE thiếu chứng cứ vẫn đóng góp điểm hoàn thành; xóa việc chưa xong có thể đổi score lịch sử.

Cần nối measured observation vào OKR, tách outcome và execution, khóa denominator của tuần, tính eligibility từ evidence thật. Không cộng/trộn điểm làm việc với mức đạt kết quả.

### IA23 — P1/P2: Completion validator chưa kiểm evidence, còn endpoint WGA gọi chưa có

[execution-outcome.service.ts:169](/services/company/operations/services/execution-outcome.service.ts:169) set task DONE không query evidence/criteria; dòng 184 set parent commitment DONE mà không kiểm các task anh em, không revision CAS. Service này chưa có production caller, nên đây là lỗi cần sửa trước khi nối, không khẳng định đang là đường completion production.

[wga_run.py:117](/apps/cosa/worker/wga_run.py:117) gọi `/operations/tasks/:id/validate-completion`, nhưng chưa có handler endpoint tương ứng. Run hoàn tất đi exception và giữ completion_pending. Điểm đúng: initial/resume dùng chung finalizer và đã ngừng tự đánh DONE. Cần hoàn thành cả validator lẫn HTTP integration để luồng kết thúc được.

### IA24 — P1: Event mới vẫn không đủ input cho worker run thật

[event_run_contract.py:132](/apps/cosa/events/event_run_contract.py:132) thêm run/profile/principal/conversation nhưng không resolve aggregate thành user_prompt/delegation. [handlers.py:151](/apps/cosa/worker/handlers.py:151) đọc ngay payload["user_prompt"]. Payload event Operations/Finance/Marketing mới tới đây sẽ KeyError trước nghiệp vụ.

Test contract mock execute_run_task, nên không chạm lỗi. Envelope pin/hash cũng chưa dùng để chọn spec ở [handlers.py:233](/apps/cosa/worker/handlers.py:233). Legacy thiếu run ID còn mint lại mỗi adapter invocation. Cần producer→scheduler→worker thật, resolve aggregate/principal có quyền, dùng shared preparation và pin spec/hash.

### IA25 — P1: Copilot gọi capability trực tiếp, chưa qua shared auth/compliance pipeline

[copilot_run.py:158](/apps/cosa/worker/copilot_run.py:158) tự mint delegation, fallback actor "0"; các dòng 196/210/226 gọi capability handler trực tiếp dù comment nói via gateway. Kernel call tại dòng 255 không qua run_core chuẩn hóa compliance context. [Company dispatch:78](/services/company/commercial/services/customer-engagement/copilot.service.ts:78) không truyền actor/delegation.

Thêm Authorization read không chứng minh principal đúng hoặc policy/audit gateway được thực thi. Callback HTTP lỗi chỉ log, chưa có retry durable; Company callback overwrite status thiếu completion version/CAS và không lưu đầy đủ reasonCode/evidenceRefs. Cần shared preparation/gateway và callback outbox/idempotency, test từ dispatch thực tới artifact và terminal state.

### IA26 — P2: Resize/kickoff và project projection chưa giữ lịch sử nhất quán

| Đường code | Sai lệch còn lại | Điều kiện nghiệm thu |
|---|---|---|
| [Cycle update:283](/services/company/operations/services/twelve-week-year.service.ts:283) | Đổi local dates/duration không reconcile legacy dates/weekly plans; rút 6→2 vẫn còn tuần 3–6 | Revision/change request, giữ tuần đã chốt, xử lý phần lịch tương lai rõ ràng |
| [Weekly dates:357](/services/company/operations/services/twelve-week-year.service.ts:357) | Client truyền đủ dates thì server không derive/validate chúng trong cycle; weekNo chưa kiểm integer | Server là nguồn lịch; validate integer/timezone/date bounds |
| [Kickoff:95](/services/company/operations/strategy/services/project-kickoff-materialize.service.ts:95) | Caller không bind cycleId; fallback latest cycle; upsert lại tuần 1; removal còn cancel in_progress | Bind cycle/revision từ đầu; thay đổi việc đã chạy qua change request |
| [Projection:102](/services/company/operations/services/execution-cycle-view.service.ts:102) | Explicit cycle không kiểm project, fallback newest không lọc ACTIVE/READY | Chọn đúng project/cycle, xử lý multiple ACTIVE và NEEDS_SETUP |
| [Review handler:26](/services/company/operations/strategy/handlers/weekly-review.handler.ts:26) | Không nhận weeklyPlanIds/decisionIds nên link luôn rỗng | Contract/API/UI lưu và reload các link đã kiểm tenant |

### IA27 — P2: Measurement/context freshness chưa đủ để agent quyết định

[kr-observation.service.ts:49](/services/company/operations/services/kr-observation.service.ts:49) parseFloat nhận "12junk" thành 12 và mất exact decimals; latest projection đọc trước insert không lock KR nên observation cũ có thể overwrite bản mới khi concurrent. Chưa validate evidence/window/contract version; idempotency chưa phân source và chưa xử lý concurrent duplicate thành replay.

[Action context:181](/services/company/operations/strategy/services/project-action-context.service.ts:181) trả metrics READY `[]` mà không đọc metrics, nhiều sourceVersion là "1", outside cycle fallback tuần 1. [GET next-best-actions:74](/services/company/operations/strategy/handlers/next-best-action.handler.ts:74) gọi proposeNextActions có INSERT không dedupe, refresh có thể tạo lặp proposals. Cần provenance/version/freshness thật, readiness trung thực và tách read khỏi tạo proposal.

### IA28 — P2: Obligation history và active context còn thiếu

[Transition map:280](/services/company/finance-legal/services/legal-obligation.service.ts:280) cho EXEMPT/CANCELLED→OPEN cùng instance, không tạo revision mới. CAS chỉ status, không expectedVersion cho thay đổi owner/evidence. [Project context:264](/services/company/operations/strategy/services/project-action-context.service.ts:264) chỉ lấy OPEN nên chuyển IN_PROGRESS làm nghĩa vụ biến mất khỏi active context. Chưa có scheduler/reminder/outbox dedup như L3.

Cần giữ terminal history, đưa OPEN/IN_PROGRESS vào active context phù hợp, reminder theo due date/timezone và quyền owner. Weekly review đếm tổng chưa thay được obligation details/action/evidence.

## 3. Các khoảng trống kiểm chứng và tích hợp cần xử lý tiếp

- **R4 chưa chứng minh durable runtime:** [test_event_approval_restart.py](/tests/e2e/test_event_approval_restart.py:65) tăng delivered_count trực tiếp và chuyển checkpoint dict qua multiprocessing.Queue. Có hai PID nhưng không có production run repository/checkpoint/lease/gateway. Giữ test như simulation nếu muốn, nhưng không dùng làm bằng chứng restart.
- **H1 thiếu:** không thấy test_business_operating_loop.py, business_operating_loop.dart hoặc release evidence tương đương. Existing cross-plane smoke có phạm vi riêng, không thay được business loop mới.
- **Company typecheck đang fail:** 9 lỗi ở deployment-authority/legal-applicability-integrity/legal-obligation-lifecycle tests. Có fixture legalName không tồn tại trong schema và TenantContext thiếu permissions/correlationId. Không thể ghi “full checks passed”.
- **F1 mới khóa kỳ một phần:** close kỳ vẫn chỉ requireWorkspaceAccess, không finance.period.close; closedBy chưa được ghi. Guard có legalEntityId tùy chọn trong khi document confirm/void không truyền entity; open kỳ chưa chặn overlap bằng constraint/validation. Row SHARE/UPDATE là cải tiến thật nhưng chưa hoàn thành scope/authority/invariants.
- **F3 grant lifecycle chưa hoàn chỉnh:** sync tick không kiểm grantExpiresAt; worker inbox không recheck consent trước normalize/write. Cron resolver đọc CAS_ACCESS_TOKEN_<connectionId> thay vì secretRef/vault; chính code thừa nhận exchange chưa có token thật. Event revoke/expired trong parser đang IGNORED, không cập nhật consent. Cần quyết định rõ chính sách xử lý dữ liệu đã nhận trước revoke và chặn fetch mới sau expiry/revoke.
- **Contract gates có giới hạn:** các gate boundary/route/suppression pass không chứng minh routes được màn hình thật gọi hoặc authorization đúng. Migration compatibility checker pass cũng không chứng minh migrations đã chạy, backfill đúng hay app N-1 hoạt động.

## 4. Bằng chứng kiểm tra thực hiện

| Kiểm tra | Kết quả | Phạm vi |
|---|---|---|
| Company `npm run typecheck` tại mốc 527aced4 | FAIL, exit 2, 9 lỗi | Các lỗi được liệt kê phía dưới; không sửa code để làm pass |
| COSA `npm run typecheck` | PASS, exit 0 | Chỉ type correctness |
| Company boundary + Encore handler boundary | PASS | Có 7 tests boundary; handler không query DB trực tiếp |
| TS suppression gate | PASS | 5 tests; không phải gate cấm mọi any/cast |
| Frontend API contract gate | PASS | 11 tests; có allowlist, không xác nhận caller wiring |
| Migration compatibility gate | PASS | Chạy lại tại 527aced4: 159 migrations, 0 violations; đây là static gate, chưa khẳng định migrations đã chạy DB |
| H0 runner unit với PYTHONPATH=. | 5 PASS | Mock cluster/subprocess, không phải migrate thực |
| Python runtime/readiness/knowledge/event/evals chọn lọc | 29 PASS | Chạy helper/contract suites; không chứng minh production wiring, policy-bound execution hoặc durability |
| Flutter permissions/cycle/legal flow tests mới | 4 PASS | Fake services, không kiểm HTTP/DB persistence toàn luồng |
| Disposable DB integration F1/F3 | Chưa chạy được test | Admin PostgreSQL local trả password authentication failed; không tìm thấy credential admin đã cấu hình để tiếp tục |
| Probe repository thật | Tái hiện TypeError | Sai chữ ký get của Copilot |
| Probe production Cas normalizer | Tái hiện sai amountMinor | 9007199254740993 → 9007199254740992 |
| Probe production snapshot | Tái hiện thiếu coverage | Unknown opening balance vẫn thành số dư chắc chắn |

Lệnh Flutter đã chạy: `flutter test test/modules/settings/permissions_panel_test.dart test/modules/strategy/execution_cycle_flow_test.dart test/modules/legal/obligation_flow_test.dart` tại frontend. Probe TypeScript transpile chính source vào VM, mock import DB/API boundary để chỉ gọi hàm thuần; không kết nối DB/provider.

Lệnh Python runtime đã chạy bởi reviewer trong cùng workspace:

```sh
env AGENT_DATABASE_URL= COSA_DATABASE_URL= DATABASE_URL= PYTHONPATH=. \
.venv/bin/python -m pytest -q \
tests/apps/cosa/worker/test_run_outcome.py \
tests/apps/cosa/agents/test_business_agent_readiness.py \
tests/apps/cosa/test_knowledge_profile_evidence.py \
tests/apps/cosa/events/test_event_worker_contract.py \
tests/apps/cosa/evals/test_business_agent_evals.py
```

Kết quả 29 passed in 1.62s. Revocation test riêng dựng DummyBusinessPolicyClient và tự quyết định side effect bằng if; restart test dựng checkpoint dict; các test đó không được tính là bằng chứng agent/gateway/PostgreSQL thật. Flutter cycle test inject lists rồi assert text, không Save/reload; legal flow mock transition, chưa kiểm evidence hoặc quyền thật. `frontend/test/modules/legal/deployment_authority_test.dart` chưa tồn tại.

Các lỗi typecheck: deployment-authority.test.ts:169,257,280; legal-applicability-integrity.test.ts:34,44,90,99,182; legal-obligation-lifecycle.test.ts:98. Lần chạy H0 với PYTHONPATH thêm packages/agent gây shadow namespace scripts; sửa cách chạy về PYTHONPATH=. thì 5 test pass. Lỗi đường chạy này không được tính thành lỗi implementation H0, nhưng cần sửa lệnh hướng dẫn trong plan khi thực thi.

## 5. Thứ tự khắc phục đề xuất

Các phần nên giữ lại: runner disposable với preflight rõ; weekly review completion có CAS/outbox và replay không phát lại event; lọc candidate ở project gate/PMF; calendar N tuần và revision schema; permission catalog/evaluator nền; WGA dùng chung finalizer; finance period row locking và inbox durable schema. Đây là tiến bộ thực trong source. Phần còn thiếu chủ yếu là enforcement ở caller thật, bảo toàn dữ liệu/version và kiểm chứng integration; không cần viết lại tất cả từ đầu.

1. Chặn IA01/IA02 và authority resume trước; viết test từ public command/tool thật, không chỉ helper. Sửa typecheck để test fixtures phản ánh schema thật.
2. Sửa W-stage/project gate và nối S2–S5 vào controller/API hiện dùng. Hoàn tất endpoint observation/completion, giữ history/version và evidence thật.
3. Sửa run envelope→handler/context/pin, Copilot artifact protocol, inject knowledge repo và readiness. Thay các eval tự dựng kết quả bằng production path + process/persistence thật.
4. Hoàn thiện Cas exchange/state/vault/contract, webhook raw payload và inbox crash/correction/grant handling; sửa snapshot entity/currency/coverage. Kiểm sandbox bằng fixtures đã xác nhận, không đặt SANDBOX_READY chỉ vì có credentials.
5. Thực hiện F4/F5/F6 và H1 còn thiếu; chạy DB concurrency, migration/backfill, frontend reload và business E2E trước đánh dấu hoàn tất.

**Giới hạn:** chưa kiểm runtime đang deploy hoặc migration state của môi trường thật; chưa gọi API ngân hàng, chưa kiểm biểu mẫu TT58 đầy đủ. Đây là audit source/caller/tests ở commit đã nêu; các lỗi concurrent SQL/permission được trace tĩnh trừ những probe đã ghi rõ. Các thay đổi sau 527aced4 cần audit bổ sung, không tự được bao phủ bởi báo cáo này.
