# COSA One-Person Enterprise — Thiết kế tích hợp và điều chỉnh

**Trạng thái:** Thiết kế đề xuất, chưa triển khai mã nguồn  
**Ngày:** 28/08/2026  
**Quyết định sản phẩm đã chốt:** COSA cung cấp `Venture Workspace` miễn phí cho một cá nhân từ Level 0; dữ liệu, lịch sử và bằng chứng đi cùng người sáng lập khi họ chuyển thành pháp nhân.

## 1. Mục tiêu

Biến COSA từ một Founder/Company OS thành **AI Operating System for One-Person Enterprise**: một nền tảng để cá nhân bắt đầu từ vấn đề chưa định hình, được AI hỗ trợ phân tích và triển khai, rồi phát triển thành hoạt động kinh doanh, pháp nhân và doanh nghiệp có vận hành–kế toán–tuân thủ rõ ràng.

Mục tiêu không phải là để AI “làm doanh nghiệp thay” người dùng. COSA phải giúp người sáng lập:

1. Hiểu vấn đề, khách hàng và giả định của mình.
2. Biến phân tích thành bằng chứng, quyết định và công việc nhỏ có thể thực hiện.
3. Có một workspace miễn phí ngay cả khi chưa có doanh nghiệp đăng ký.
4. Nhận biết đúng thời điểm cần đăng ký, cần kế toán hoặc cần chuyên gia pháp lý.
5. Tự động hóa dữ liệu tài chính một cách đọc-trước, kiểm chứng được và luôn có quyền phê duyệt của con người.

## 2. Phạm vi và các giới hạn bắt buộc

### 2.1 Trong phạm vi

- Onboarding Level 0 và `Venture Workspace` miễn phí.
- Vòng đời S0–S5 có bằng chứng, gate và chuyển stage thực sự.
- Tách trạng thái phát triển kinh doanh khỏi trạng thái pháp lý.
- Khung tuân thủ, kế toán TT58/2026/TT-BTC và tài chính quản trị.
- Kết nối Cas.so theo cơ chế consent, chỉ đọc giao dịch/số dư ở giai đoạn đầu.
- AI trợ lý: phân tích, đề xuất, tạo nháp, tạo công việc và chờ phê duyệt trước mọi hành động có hệ quả.
- Sửa các hợp đồng API giữa Flutter, Company Service, Control Plane và AgentOS trước khi mở rộng tính năng.

### 2.2 Ngoài phạm vi của đợt đầu

- Tự nộp hồ sơ đăng ký doanh nghiệp, khai thuế, ký số hoặc nộp báo cáo cho cơ quan nhà nước.
- Tư vấn pháp lý/kế toán có giá trị kết luận thay cho người hành nghề có thẩm quyền.
- Chuyển tiền, payout, thanh toán hóa đơn hoặc bất kỳ lệnh chi nào qua Cas.so.
- Xây dựng sổ cái kép tổng quát khi mode TT58 đang áp dụng không yêu cầu điều đó.
- Tự động kết luận rằng người dùng đủ điều kiện hưởng một chính sách thí điểm.

## 3. Cơ sở pháp lý và cách COSA phải diễn đạt

Nghị quyết 86/NQ-CP ban hành Chiến lược quốc gia về khởi nghiệp sáng tạo đặt ra việc **đề xuất chính sách thí điểm** cho mô hình “doanh nghiệp một người”, bao gồm một số cơ chế có thể được nghiên cứu. Đây không phải là một loại hình doanh nghiệp mới đã có hiệu lực áp dụng chung. Phụ lục chiến lược giao việc xây dựng đề xuất mô hình cho giai đoạn đến năm 2027.

Vì vậy, mọi nội dung trong COSA phải phân biệt ba lớp:

| Lớp thông tin | Ý nghĩa trong sản phẩm | Cách AI được phép nói |
|---|---|---|
| `CURRENT_LAW` | Nghĩa vụ/quyền theo văn bản đang có hiệu lực và điều kiện đã biết | Nêu nguồn, ngày hiệu lực, dữ kiện người dùng còn thiếu và mức tin cậy |
| `POLICY_WATCH` | Đề xuất, chính sách đang nghiên cứu hoặc chương trình thí điểm | Nêu rõ “đang theo dõi”, không hứa quyền lợi hoặc miễn trừ |
| `PROFESSIONAL_REVIEW` | Việc đòi hỏi hồ sơ, cơ quan có thẩm quyền hoặc ý kiến chuyên gia | Lập checklist và đề xuất gặp chuyên gia; không đưa kết luận pháp lý cuối cùng |

Thông tư 58/2026/TT-BTC có hiệu lực từ 01/07/2026, thay thế Thông tư 132/2018/TT-BTC đối với doanh nghiệp siêu nhỏ. COSA phải quản lý chế độ kế toán theo **phiên bản văn bản, thời điểm bắt đầu năm tài chính và điều kiện áp dụng**, không gắn nhãn TT58 chỉ bằng một lựa chọn trong giao diện.

Nguồn cần được lưu trong Legal/Regulation Catalog:

- Nghị quyết 86/NQ-CP ngày 05/04/2026: https://vanban.chinhphu.vn/?classid=509&docid=217558&pageid=27160
- Thông tư 58/2026/TT-BTC: https://congbao.chinhphu.vn/van-ban-dang-cong-bao/bo-tai-chinh-c10/trang-4.htm
- Tóm tắt chính sách TT58 của Bộ Tài chính: https://www.mof.gov.vn/tin-tuc-tai-chinh/tin-chinh-sach-tai-chinh/quy-dinh-moi-ve-che-do-ke-toan-cho-doanh-nghiep-sieu-nho
- Cas.so API: https://cas.so/en/general/api/
- Cas.so webhook: https://cas.so/en/general/api/webhook/

## 4. Kết quả audit ảnh hưởng đến thiết kế

### 4.1 Nền tảng có thể tái sử dụng

- `services/company` đã có workspace, membership, workforce, task, OKR, strategy, evidence, stage policy, approval cho giao dịch rủi ro và transactional outbox.
- `apps/cosa` và `packages/agent_core` đã có capability gateway, policy, approval theo tool call, idempotency và audit trail bền vững.
- `services/cosa` đã có plan, license, entitlement và khung connector có installation, authorization, session grant, scope và revoke.
- Flutter đã có các module onboarding, strategy, task, finance, legal, approvals và hub có thể được thay bằng luồng thống nhất thay vì xây lại ứng dụng.

### 4.2 Các điểm phải sửa trước khi mở rộng

| Hiện trạng | Rủi ro | Quyết định thiết kế |
|---|---|---|
| Đăng ký bắt buộc tạo `company` trên Control Plane | Level 0 bị gán là công ty dù chưa kinh doanh/đăng ký | Tạo platform workspace/venture độc lập với legal company |
| `identity_workspaces.company_stage` có `S0_GENESIS` | Endpoint stage transition chỉ ghi log, không đổi stage thực | Một service chuyển stage duy nhất phải cập nhật state + journal + outbox trong cùng transaction |
| Plan `free` đã seed | Tạo company không tạo license/entitlement | Provision free entitlement ngay khi tạo Venture Workspace |
| Finance schema mặc định TT58 | Thiếu chứng từ, sổ, source, reconciliation và report lifecycle | Xây financial ingestion và accounting document lifecycle trước UI TT58 |
| Finance UI gọi endpoint thiếu hoặc trả giá trị giả | Người dùng tưởng dữ liệu tài chính thật | Bỏ giả lập, tắt feature chưa có server, thêm contract test |
| Finance agent gọi `/finance-legal/payouts` không tồn tại | Luồng chi tiền có vẻ được bảo vệ nhưng không triển khai thật | Loại payout khỏi bản đầu; chỉ giữ read/propose/record-draft có service identity |
| Agent ghi transaction gửi `accountId`/`type` nhưng backend cần `transactionDate`/`direction` | Capability hiện không thể ghi giao dịch hợp lệ | Dùng một finance command contract duy nhất, do backend kiểm tra |
| Connector Control Plane chỉ allow `sandbox-read` mặc định | Chưa có Cas provider, consent exchange hoặc webhook processing | Thêm connector `cas` với quyền read-only, secret reference và re-check grant |
| Legal checklist/obligation chỉ là title thủ công | Không thể giải thích nguồn, hiệu lực hoặc điều kiện áp dụng | Tạo catalog văn bản, applicability rule và obligation instance có provenance |

## 5. Kiến trúc đích

### 5.1 Nguyên tắc tenant

`Venture Workspace` là tenant sản phẩm, không đồng nghĩa với pháp nhân. Một cá nhân có thể có nhiều Venture Workspace; mỗi workspace có đúng một founder owner ban đầu và có thể mời người khác sau này.

Không dùng bảng `companies` hiện có như một từ đồng nghĩa với workspace. Việc đó sẽ làm sai ngữ nghĩa Level 0, entitlement và compliance ngay từ gốc.

```text
Platform user
  └── Platform Workspace / Venture Workspace (identity, billing, entitlement)
        └── Local identity workspace (tenant nghiệp vụ)
              ├── Venture profile (stage và bối cảnh khởi nghiệp)
              ├── Legal entity profile 0..n (chỉ có sau khi khai báo/đăng ký)
              ├── Strategy, evidence, tasks, commercial
              ├── Finance / TT58 / Cas connections
              └── AI conversations, approvals, audit events
```

### 5.2 Thay đổi Control Plane

Tạo các khái niệm tách biệt trong `services/cosa`:

| Bảng/khái niệm | Trách nhiệm | Ghi chú |
|---|---|---|
| `platform_workspaces` | Tenant cấp platform, tên workspace, owner, trạng thái | UI gọi là Venture Workspace cho S0–S3 |
| `platform_workspace_memberships` | Quyền founder/member cho tenant platform | Không dùng `company_memberships` cho venture mới |
| `workspace_entitlements` và `workspace_licenses` | Plan/limit/feature theo workspace | Thay thế phụ thuộc vào `company_id` cho luồng mới |
| `companies` và `company_memberships` | Tổ chức hợp tác/pháp nhân cũ hoặc đã xác lập | Giữ tương thích dữ liệu hiện hữu |

Khi một Venture Workspace có pháp nhân, `legal_entity_profiles.platform_company_id` có thể liên kết sang `companies`; quan hệ này là tùy chọn. Không di chuyển tenant hay mất lịch sử khi liên kết.

Luồng provision mới:

1. User đăng ký hoặc đăng nhập platform.
2. User nhập tên venture/workspace, không phải “tên công ty”.
3. Control Plane tạo `platform_workspace`, membership founder, license `free`, entitlement snapshot trong một transaction.
4. Local Company Service đồng bộ thành `identity_workspaces` có `platform_workspace_id` và membership founder.
5. App chọn workspace rồi vào onboarding S0.

Nếu một transaction provision lỗi, không trả token thành công với workspace nửa vời. Retry dùng idempotency key theo `user_id + client_workspace_creation_id`.

### 5.3 Thay đổi local workspace và vòng đời

Giữ `identity_workspaces` là tenant nghiệp vụ để tránh di chuyển toàn bộ foreign key. Bổ sung:

- `platform_workspace_id`: unique, nullable khi local-only;
- giữ `platform_company_id` cho liên kết legacy/pháp nhân;
- đổi tên API/domain từ `companyStage` sang `ventureStage`, nhưng giữ cột `company_stage` trong giai đoạn tương thích;
- `venture_profiles`: 1:1 với workspace, lưu founder intent, industry, geography, currency, timezone, stage entered at;
- `legal_entity_profiles`: 0..n theo workspace, status và bằng chứng xác minh, không lưu kết luận pháp lý từ AI.

Stage kinh doanh tiếp tục dùng code hiện có để giảm đứt gãy:

| Stage | Ý nghĩa UX | Điều COSA ưu tiên |
|---|---|---|
| `S0_GENESIS` | Tôi có vấn đề/ý tưởng nhưng chưa có mô hình kinh doanh | Problem framing, customer hypothesis, founder goal |
| `S1_PROBLEM_VALIDATION` | Tôi cần chứng minh vấn đề đáng giải | Interview, evidence, assumption, decision log |
| `S2_SOLUTION_VALIDATION` | Tôi đang kiểm tra giải pháp/offer | Prototype, experiment, ICP, pricing hypothesis |
| `S3_MVP_BUILD` | Tôi đã có MVP hoặc hoạt động thử | Weekly execution, early revenue, operating controls |
| `S4_PRODUCT_MARKET_FIT` | Tôi có tín hiệu thị trường và cần chuẩn hóa vận hành | Registration readiness, compliance, accounting profile |
| `S5_SCALE` | Tôi mở rộng doanh thu/đội ngũ/hệ thống | Portfolio, delegation, reporting, control cadence |

Trạng thái pháp lý là trục riêng, không suy ra từ stage:

`NOT_DECLARED` → `UNREGISTERED` → `REGISTRATION_READINESS` → `REGISTERED_PENDING_VERIFICATION` → `REGISTERED_VERIFIED`.

Một stage transition hợp lệ phải:

1. Đọc stage hiện tại từ workspace, không tin `fromStage` do client gửi.
2. Kiểm tra stage policy và evidence/gate tương ứng.
3. Trả về proposal nếu gate chưa đạt; chỉ human founder có thể xác nhận override có lý do.
4. Cập nhật `company_stage`, ghi `stage_transitions`, `decision_records` và outbox event `venture.stage.changed.v1` trong cùng transaction.
5. Hỗ trợ chuyển lùi/reopen bằng lý do bắt buộc; không xóa journal cũ.

## 6. Trải nghiệm Level 0

### 6.1 Onboarding không dùng ngôn ngữ “đăng ký công ty”

Sau đăng nhập, onboarding gồm năm bước ngắn:

1. **Bạn đang muốn giải quyết điều gì?** Người dùng nhập tự do bằng tiếng Việt.
2. **Ai đang gặp vấn đề đó?** AI tách problem, customer, bối cảnh và điều chưa rõ.
3. **Bạn muốn đạt điều gì trong 12 tuần?** Chọn thử nghiệm, thu nhập phụ, dịch vụ, sản phẩm hoặc học tập.
4. **AI đề xuất bản đồ khởi đầu.** Gồm giả định, câu hỏi phỏng vấn, rủi ro và ba việc đầu tiên.
5. **Tạo Venture Workspace Free.** Founder xác nhận; COSA tạo workspace, evidence seed, backlog và weekly plan nhẹ.

AI không được tự khẳng định “ý tưởng khả thi”, “phải đăng ký doanh nghiệp”, “đủ điều kiện TT58” hay “được miễn nghĩa vụ”. Mọi câu trả lời tư vấn phải bao gồm:

- điều đã biết và nguồn;
- giả định chưa kiểm chứng;
- hành động kế tiếp;
- nhãn `insight`, `proposal`, hoặc `requires_professional_review`.

### 6.2 Entitlement free tối thiểu

Free workspace cần là quyền thật ở backend, không chỉ là pricing copy:

- một founder workspace đang hoạt động;
- giới hạn project/task/AI run được thể hiện chính xác từ entitlement snapshot;
- discovery, strategy, evidence, basic task và read-only finance insight bật;
- Cas connection, automated accounting, filing pack và multi-member automation chỉ được hiển thị khi entitlement cho phép;
- kiểm tra entitlement ở API/backend trước capability execution, không chỉ ở Flutter.

## 7. AI Operating System: quyền hạn và giao thức

### 7.1 Mô hình quyền hạn

| Cấp | AI được làm | Ví dụ |
|---|---|---|
| L0 Observe | Đọc dữ liệu đã được cấp quyền, phân tích và giải thích | Tóm tắt interview, giải thích runway |
| L1 Propose | Sinh draft, plan, transaction classification, checklist | Đề xuất ba việc tuần này, nháp chứng từ |
| L2 Execute with approval | Tạo task, lưu evidence, tạo draft document sau founder approval phù hợp | Tạo backlog đã xem trước |
| Không dùng cho v1 | Tự gửi hồ sơ, chi tiền, thay đổi nghĩa vụ pháp lý | Bị deny ở policy lẫn capability registry |

### 7.2 Capability cần có

Thêm capability theo ranh giới nghiệp vụ, không để model ghi trực tiếp database:

- `venture.profile.read`, `venture.profile.propose_update`;
- `venture.stage.assess`, `venture.stage.transition.propose`;
- `strategy.discovery.read`, `strategy.evidence.create_draft`, `operations.task.create_draft`;
- `finance.connection.read`, `finance.transaction.read`, `finance.transaction.classify.propose`;
- `finance.accounting_document.create_draft`, `finance.accounting_document.confirm`;
- `legal.applicability.assess`, `legal.obligation.create_draft`.

`finance.payout.execute` không được đăng ký trong agent plane hoặc workflow của release TT58/Cas đầu tiên. Endpoint `/finance-legal/payouts` không tồn tại và không được thêm chỉ để làm capability này hoạt động.

Mỗi capability write phải nhận identity của principal/service, workspace id, action idempotency key, payload hash và approval context. Company Service phải xác thực service identity riêng; AgentOS không dùng anonymous `CompanyServiceClient` để vượt qua `requireWorkspaceAccess`.

### 7.3 Decision record chuẩn

Mọi insight có tác động đến stage, tài chính hay pháp lý tạo một `decision_record` gồm:

- `decision_type`, `workspace_id`, chủ thể tạo;
- evidence refs và regulation refs;
- confidence, assumptions, alternatives;
- founder decision: accepted/rejected/deferred;
- immutable audit timestamp và version của policy/AI prompt.

## 8. Kế toán TT58 và Cas.so

### 8.1 Kiến trúc TT58

`accounting_profiles` và `accounting_fiscal_profiles` hiện có chỉ là điểm bắt đầu. Bổ sung các lớp sau:

| Lớp | Dữ liệu cần quản lý | Quy tắc |
|---|---|---|
| Regulation catalog | Văn bản, issuer, số hiệu, effective period, URL, content hash, version | Không hard-code form/báo cáo trong Flutter |
| Applicability assessment | Entity status, fiscal year start, user declarations, unresolved facts, reviewer confirmation | AI chỉ đề xuất; founder/chuyên gia xác nhận |
| Bank connection | Provider, consent state, secret reference, scopes, account links, expiry | Không lưu access token thô trong database nghiệp vụ |
| Ingestion event | Provider event id, received time, raw payload encrypted/ref, checksum, status | Idempotent trước khi tạo transaction |
| Bank transaction | Provider/account/external id, posted date/time, amount decimal, currency, description, counterparty, provenance | Unique theo provider + account + external transaction id |
| Accounting document | Draft, reviewed, confirmed, voided, correction relation, evidence link | Confirm/void có audit, không sửa lịch sử im lặng |
| Reporting snapshot | Kỳ, regulation version, source document version, generated at, reviewer | Không tự đánh dấu “ready to file” |

Mode TT58 phải được cài đặt qua `AccountingRegimePolicy`, không rải `if (TT58)` trong Flutter. Với mode không yêu cầu chart of accounts, COSA dùng transaction/document register thích hợp; không ép người dùng vào sổ cái kép chung. Danh mục sổ và báo cáo chỉ được xuất khi Regulation Catalog đã xác nhận đúng văn bản áp dụng.

### 8.2 Luồng Cas.so read-only

```text
Founder consents
  → Control Plane creates Cas connector authorization (secret reference only)
  → Cas linking/exchange happens server-to-server
  → Cas sends transaction/balance webhook
  → Finance ingestion verifies, stores inbox record, deduplicates
  → Mapper creates bank transaction with provenance
  → Reconciliation/classification proposes accounting document
  → Founder reviews and confirms document
  → Company outbox emits finance events for insights and tasks
```

Yêu cầu bắt buộc cho Cas connector:

1. `connectorKey = cas` phải nằm trong allow-list theo environment; production không dùng mặc định `sandbox-read`.
2. Authorization lưu `secret://cosa-connectors/...`; token, client secret và refresh secret nằm ở secret manager, không ở Flutter, conversation hoặc agent memory.
3. Scope bản đầu chỉ là `balance:read` và `transactions:read` theo phạm vi Cas thực tế cấp; không xin transfer/payout scope.
4. Webhook chỉ được xử lý sau khi xác minh theo cơ chế xác thực được Cas công bố cho account đó. Lưu event trước, xử lý sau từ inbox idempotent.
5. Replayed/out-of-order webhook không được tạo giao dịch kép; external transaction id và payload checksum là khóa chống trùng.
6. Mọi số liệu UI phải hiển thị `last_synced_at`, connection state và nguồn Cas; khi sync lỗi phải hiển thị lỗi, không trả về số 0 hoặc dữ liệu giả.
7. Cas transaction không tự trở thành chứng từ/kế toán chính thức. Nó chỉ tạo candidate để phân loại và xác nhận.

## 9. Legal and compliance workspace

Tạo `regulation_sources`, `regulation_versions`, `applicability_rules`, `legal_obligation_templates` và `legal_obligation_instances`.

Mỗi obligation instance phải có: nguồn/vị trí áp dụng, legal entity profile, ngày hiệu lực, due date, predicate đã thỏa/chưa thỏa, evidence artifact, review status và owner. `legal_checklist_items` cũ có thể được migrate thành manual instance với `source = USER_CREATED`, không biến thành nghĩa vụ pháp luật tự động.

Giao diện Legal không được hard-code “Thông tư 58/2024/TT-BTC”. `getLegalSources()` phải đọc catalog có version. Contract analysis AI trả về issue/risk/question/source nhưng luôn kèm nhãn `not_legal_advice` và đường dẫn escalation.

## 10. Hợp đồng API và giao diện

### 10.1 Quy tắc hợp đồng

- Backend là nguồn chuẩn cho request/response schema.
- Flutter dùng typed DTO và endpoint contract được kiểm thử, không suy đoán key như `regime` thay cho `mode`.
- Không dùng workspace id dự phòng `'1'`; không xác định workspace là lỗi hiển thị được.
- Không nuốt exception và trả `[]`/`null` như thể không có dữ liệu.
- Không hiển thị feature “đã hoạt động” khi backend không có endpoint.

### 10.2 Các sửa chữa phải thực hiện sớm

| File/khối hiện có | Điều chỉnh |
|---|---|
| `frontend/lib/modules/finance/services/finance_service.dart` | Bỏ fallback workspace `'1'`, bỏ `activateProfile`/`previewRegimeTransition` giả, đổi payload `regime` thành `mode`, chỉ gọi endpoint đã tồn tại |
| `frontend/lib/modules/finance/services/finance_tt58_service.dart` | Tắt/xóa route TT58 cũ chưa có server; thay bằng typed API sau khi finance backend hoàn thành |
| `frontend/lib/modules/legal/services/legal_service.dart` | Thay hard-coded source bằng Regulation Catalog; dùng đúng route checklist/obligation hoặc xây list route thật |
| `apps/cosa/capabilities/finance_write.py` | Xóa payout execution và thay finance transaction write bằng command contract có auth/provenance/approval |
| `services/company/finance-legal` | Thêm list endpoints, document lifecycle, finance ingestion và outbox events thay vì để UI tự suy đoán |
| `services/company/operations/strategy/handlers/stage-transition.handler.ts` | Gọi lifecycle service transactionally thay vì insert journal trực tiếp |

Contract tests phải chạy với Company Service thật hoặc test server theo schema đã generated. Test chỉ mock URL không được coi là bằng chứng màn hình đã tích hợp.

## 11. Data migration và tương thích ngược

1. Tạo bảng mới bằng forward migration, không xóa `companies`, `identity_workspaces`, `company_stage`, `accounting_profiles` hoặc dữ liệu lịch sử.
2. Backfill mỗi company legacy thành một `platform_workspace` có `legal_status = NOT_DECLARED` trừ khi có dữ liệu pháp nhân đã xác minh. Không suy đoán `REGISTERED_VERIFIED`.
3. Link local workspace cũ qua `platform_workspace_id`; giữ `platform_company_id` nguyên vẹn.
4. Cấp entitlement free/starter/pro tương ứng theo license hiện hữu; mọi backfill có idempotency key và báo cáo số record.
5. Gán legal checklist/obligation cũ `source = USER_CREATED`; không gán source luật giả.
6. Bổ sung audit event cho backfill, nhưng không phát trigger AI cho dữ liệu backfill.
7. Giữ alias endpoint đăng ký company cho khách hàng cũ; onboarding mới dùng endpoint workspace/venture.

Rollback là feature-flag theo workspace: tắt onboarding mới, Cas connector và automation finance, nhưng không rollback migration hay xóa transaction/event.

## 12. Lộ trình triển khai theo lát cắt có thể nghiệm thu

### Release A — Venture foundation và API truthfulness

**Mục tiêu:** Người dùng mới tạo được workspace free trước khi có công ty và không gặp UI finance/legal giả.

- Platform workspace + membership + free entitlement transactionally.
- Đồng bộ platform workspace sang local workspace.
- Venture onboarding S0 và profile tối thiểu.
- Lifecycle service cập nhật stage thực, journal và outbox.
- Ẩn/tắt các màn hình/API fake; sửa typecheck event task hiện đang lỗi.

**Nghiệm thu:** Một người dùng mới có thể tạo workspace S0, đăng nhập lại thấy cùng workspace/entitlement, đổi S0→S1 khi gate hợp lệ và không có API finance/legal nào trả dữ liệu mô phỏng.

### Release B — Evidence, legal catalog và registration readiness

**Mục tiêu:** COSA biến tư vấn AI thành các đề xuất có nguồn và biết lúc nào phải chuyển sang chuyên gia.

- Regulation Catalog + TT58/2026 source/version.
- Legal status và legal entity profile.
- Applicability assessment, obligation templates/instances.
- AI decision record, citation/assumption/uncertainty UI.
- Registration readiness checklist ở S3/S4.

**Nghiệm thu:** COSA có thể giải thích vì sao một checklist xuất hiện, nguồn nào đang hiệu lực và yếu tố nào còn thiếu; không kết luận điều kiện pháp lý khi còn thiếu dữ kiện.

### Release C — Finance ingestion và TT58 foundation

**Mục tiêu:** Có dữ liệu tài chính đáng tin và chứng từ nháp/đã xác nhận, chưa tự động khai/nộp.

- Accounting regime policy và applicability confirmation.
- Bank transaction/event/document data model.
- Reconciliation and classification proposal.
- Accounting document approve/void/correction lifecycle.
- Finance outbox events và founder financial overview có provenance.

**Nghiệm thu:** Một giao dịch nhập tay có thể tạo candidate, được founder xác nhận, chỉnh sai bằng correction; mọi số liệu màn hình dẫn được về document/transaction nguồn.

### Release D — Cas.so read-only connector

**Mục tiêu:** Founder kết nối Cas và nhận giao dịch/số dư đã đồng ý chia sẻ, không có lệnh chi.

- Cas installation, consent/link/exchange, secret handling.
- Webhook inbox, verification, deduplication, retry/DLQ.
- Mapping account/transaction, sync health UI.
- Đề xuất reconciliation/document từ transaction Cas.

**Nghiệm thu:** Cùng webhook gửi lại nhiều lần chỉ tạo một bank transaction; mất consent hoặc token hết hạn chặn sync và báo rõ; agent không nhìn thấy secret và không có capability transfer/payout.

### Release E — AI operating loops và scale

**Mục tiêu:** AI thực sự điều hành bằng proposal → approval → execution trên dữ liệu đã tin cậy.

- Next-best-action sử dụng evidence, stage, cash/runway, finance exception và legal due date.
- Founder weekly review có decision record và action plan.
- Feature upgrade/multi-member controls cho workspace trưởng thành.

**Nghiệm thu:** AI có thể tạo một weekly plan có citation đến evidence/tài chính/nghĩa vụ; các action write chỉ xảy ra sau policy và approval đúng scope.

## 13. Test, quan sát và tiêu chí phát hành

Mỗi release cần có cả unit, integration và end-to-end test. Các case bắt buộc:

- Tenant A không đọc/ghi được venture, Cas connection, transaction, entitlement của Tenant B.
- Provision workspace retry không tạo license/membership trùng.
- Stage transition không đổi stage khi gate fail; override founder có audit reason.
- Flutter không gọi endpoint chưa đăng ký; contract mismatch làm CI fail.
- Financial event duplicate, out-of-order và retry không tạo duplicate document/transaction.
- Approval đã hết hạn hoặc connector grant bị revoke không thể resume execution.
- AI không thể gọi payout/transfer capability dù prompt yêu cầu.
- Legal source cũ/hết hiệu lực không được dùng để sinh obligation mới.

Metrics tối thiểu: workspace provision success/failure, stage conversion, evidence completion, contract mismatch, Cas webhook dedupe/retry/DLQ, reconciliation confidence, approval latency, legal obligation overdue và agent action denied-by-policy.

Không phát hành finance/Cas nếu TypeScript typecheck còn lỗi, nếu contract test chưa chạy trong CI, hoặc nếu UI có fallback dữ liệu giả cho tình trạng mất kết nối.

## 14. Thứ tự ưu tiên được khuyến nghị

1. Release A trước: tenant đúng, entitlement thật, stage thật, UI không nói dối.
2. Release B: tạo lớp pháp lý có nguồn trước khi đưa lời khuyên đăng ký/TT58.
3. Release C: chuẩn hóa document/data provenance trước khi kết nối ngân hàng.
4. Release D: Cas read-only, inbox và đối chiếu.
5. Release E: mở rộng AI execute dựa trên dữ liệu đã kiểm chứng.

Thứ tự này tránh rủi ro lớn nhất: kết nối AI trực tiếp vào tiền hoặc nghĩa vụ pháp lý khi tenant model, data provenance và contract giữa các service còn chưa ổn định.

## 15. Quyết định cần được giữ xuyên suốt

- Một người chưa thành lập doanh nghiệp vẫn là khách hàng đầy đủ của COSA.
- `Venture Workspace` là sản phẩm; pháp nhân là một trạng thái/liên kết sau đó.
- AI giải thích và đề xuất trước, không tự quyết định pháp lý/tài chính.
- Cas khởi đầu read-only; payout/transfer bị cấm ở capability registry và policy.
- TT58 là policy versioned + applicability + evidence, không phải một dashboard tĩnh.
- Mọi dữ liệu quan trọng phải nói rõ nguồn, thời điểm cập nhật và mức độ được xác nhận.
