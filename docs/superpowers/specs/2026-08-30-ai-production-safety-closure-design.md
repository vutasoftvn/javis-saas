# AI Production Safety Closure — Design

**Ngày:** 2026-08-30  
**Trạng thái:** Chờ duyệt spec  
**Phạm vi đợt 1:** đóng hai điều kiện P0 ngăn AI chạy production và khôi phục các quality gate đang đỏ. Không mở rộng sang API `/company-runtime`, landing intake hay refactor lớn.

## 1. Mục tiêu và tiêu chí thành công

Một tin nhắn trực tiếp từ người dùng chỉ được gửi vào model khi toàn bộ chuỗi sau hoàn tất:

1. Runtime có cùng `COSA_COMPANY_DELEGATION_SECRET` ở bên mint (COSA) và bên verify (Company).
2. Company trả một compliance snapshot đang được phê duyệt, có provider, model, purpose và retention policy xác định.
3. Người dùng gắn nhãn dữ liệu cho tin nhắn; backend tạo `DataAccessClaim` bất biến từ nhãn đó, message thật và snapshot.
4. Company cho phép data use với đúng workspace, capability, provider/model và authorization còn hiệu lực.

Thiếu bất cứ dữ liệu nào thì run bị từ chối trước khi gọi model. Event/audit chỉ chứa mã từ chối, source reference và hash; không chứa prompt hay raw delegation token.

## 2. Quyết định kiến trúc

### 2.1 Distribution cho delegation secret

`COSA_COMPANY_DELEGATION_SECRET` là shared secret một mục đích: `cosa-api` và `cosa-worker` dùng để mint JWT COSA → Company; `services-company` dùng để verify. Production compose phải yêu cầu biến này ở cả ba service bằng `${COSA_COMPANY_DELEGATION_SECRET:?…}`. Coolify là nơi inject giá trị vào compose; nếu Company chạy trong managed Encore ngoài compose thì cùng giá trị phải được khai báo tại Encore secret manager.

Không tái sử dụng `PLATFORM_JWT_SECRET`, `JWT_SECRET`, hay service token. Rotation dùng expand → deploy đồng thời ba consumer → staging verification → revoke giá trị cũ; không log giá trị secret.

### 2.2 Nguồn sự thật của Data Egress Context

Đợt này chỉ mở **direct user text** từ endpoint gửi message vào conversation. Knowledge retrieval, attachment content, autopilot và copilot chưa có nguồn metadata thật nên vẫn bị chặn bởi gate hiện có; chúng là các subproject sau, không được lách bằng claim chung.

Mỗi `MessageCreate` có nội dung đưa vào run phải mang `data_access`:

```text
data_access.categories: non-empty set<string>
data_access.subject_reference: string | null
```

Flutter hiển thị bước phân loại trước khi gửi: không có lựa chọn category thì nút gửi bị vô hiệu. Khi category chứa `PERSONAL` hoặc `SENSITIVE_PERSONAL`, `subject_reference` là bắt buộc. Category do người dùng xác nhận, không do LLM/gate đoán; Company vẫn là authority cuối cùng kiểm tra category có thuộc provider/data processing profile và authorization còn hiệu lực hay không.

Backend, không phải client, tạo:

```text
source_ref  = conversation_message:<message_id>
source_hash = sha256(UTF-8 message content)
```

Client không được gửi `source_ref`, hash, provider, model, deployment, purpose hay retention policy. Các giá trị đó lần lượt lấy từ identity, message đã lưu và snapshot đã được Company resolve.

### 2.3 Snapshot đủ provenance cho claim

Runtime snapshot phải trả thêm `providerKey`, `modelKey`, `purposeId` và `retentionPolicyId`, lấy từ `ai_provider_profiles`/`ai_data_processing_profiles` đã được chọn trong `resolveApprovedComplianceSnapshot`. `ComplianceSnapshot` Python và `AiComplianceClient` coi bốn trường là required contract, thiếu một trường là `CONTRACT_VIOLATION`.

`ComplianceResolver.resolve_for_run` nhận data-access context do worker truyền trong `RunRequest.metadata`, resolve snapshot trước, sau đó tạo `DataAccessClaim`. Claim được bind với:

- workspace/deployment/provider/model/purpose/retention từ snapshot;
- `capability_id` từ capability thực tế sử dụng cho initial user input, ban đầu là `model.input.direct-user-message` và phải có trong AgentSpec/approved binding;
- source reference/hash và category/subject reference từ message context.

`CosaDataModelGate` tiếp tục gọi `resolve_data_use` trước model call. Nó không có nhánh fallback khi runtime được compliance-gated.

### 2.4 Luồng dữ liệu

```text
Flutter classification
  → POST conversation message (category + subject reference)
  → API lưu message, tạo source ref/hash, dispatch durable payload
  → worker tạo RunRequest metadata
  → ComplianceResolver mint delegation + resolve approved snapshot
  → resolver tạo DataAccessClaim
  → CosaDataModelGate / Company resolve-data-use
  → allow + minimize → model, hoặc deny trước model
```

Nếu message không có data-access context, worker trả run failed với `DATA_ACCESS_CLAIM_MISSING`; nếu category cá nhân thiếu subject reference, trả `PROCESSING_AUTHORIZATION_MISSING`; nếu Company từ chối profile hoặc authorization bị thu hồi, model không được gọi.

### 2.5 Contract và UX

`MessageCreate.data_access` là field optional ở schema HTTP để client cũ nhận phản hồi validation có kiểm soát thay vì lỗi parse; nhưng endpoint không schedule AI run khi field thiếu. Response trả lỗi người dùng có thể hành động, không ghi prompt vào event payload.

Flutter thêm một value object immutable cho data access và truyền đúng JSON qua `AgentChatService`. UI chỉ hỗ trợ direct text trong đợt này; attachment gửi cùng message hiển thị rằng chưa được phép dùng làm model input và không được thêm vào claim giả.

Không để Flutter chọn provider/model/purpose. UI chỉ thể hiện lỗi từ backend bằng mã thân thiện và yêu cầu người dùng phân loại lại hoặc bổ sung subject reference.

## 3. Khôi phục quality gates

Các sửa chất lượng trong cùng đợt nhưng không đổi kiến trúc:

- Sửa Ruff/mypy: import/type annotation ở `company_client.py`, `agent_plane.py`, `worker/handlers.py`; thu hẹp giá trị `Any | list | None` trước `list()` trong capability gateway.
- Đồng bộ fixture Company dùng enum project status `ACTIVE` thay vì `active`.
- Xóa năm unused imports của landing để `npm run lint` và `npm run build` chạy trong CI.
- Sửa test async mock chưa được await để test API thực sự xác nhận hành vi.

Không làm bulk dependency upgrade trong đợt này.

## 4. Thay đổi dự kiến theo boundary

| Boundary | Thay đổi |
|---|---|
| Company finance-legal | Mở rộng private runtime snapshot response và test contract để trả field provenance cần thiết. Không tạo bảng/migration mới vì provider/data profile đã là nguồn dữ liệu. |
| COSA API/worker | Validate, persist và chuyển tiếp direct-message data access context; tính hash server-side; tạo claim sau khi resolve snapshot. |
| Agent platform | Chỉ nhận claim qua `RunRequest.metadata`; không import Company code và không tự quyết định category/authorization. |
| Flutter | Thu thập explicit user classification cho chat text và hiển thị lỗi có thể xử lý. |
| Deploy/docs | Inject secret bắt buộc tại ba consumer, cập nhật env examples, secrets runbook và preflight assertion. |
| CI/tests | Bổ sung unit, contract và real HTTP E2E; sửa các gate đang fail. |

## 5. Kiểm thử bắt buộc

1. Compose config thiếu delegation secret fail; đủ secret thì config render ở cả ba service.
2. Company snapshot contract trả provenance từ profile approved; thiếu field ở Python client fail closed.
3. API/worker hash đúng raw message, không tin hash/ref do client gửi.
4. Direct business-confidential message có category hợp lệ đi tới fake model đúng một lần qua Company HTTP thật.
5. Thiếu classification, personal không có subject reference, model/profile mismatch, cross-workspace delegation và authorization withdrawn đều dẫn đến zero model call.
6. Flutter unit/widget tests chứng minh không gửi tin nhắn chưa phân loại và serializes đúng field.
7. Các quality gates đã fail trong audit đều green; chạy lại test Python agent/COSA, Company, Flutter và landing lint/build.

## 6. Không nằm trong phạm vi

- Metadata và claims cho knowledge retrieval, file attachment, connector output, copilot hoặc autopilot.
- API `/company-runtime` và các UI runtime chưa có backend.
- Durable landing registration, public endpoint rate limiting tổng quát và refactor module lớn.
- Cho phép một run production dùng category/provider/purpose mặc định.

## 7. Rủi ro và rollout

Direct chat sẽ chỉ usable khi workspace có deployment/profile/binding đúng capability mới. Đây là thay đổi cố ý: các workspace chưa được govern sẽ tiếp tục fail closed, không được âm thầm dùng model. Trước production rollout, seed một workspace staging có provider profile, data processing profile, approved deployment, capability binding và authorization test; chạy đủ allow/deny E2E rồi mới bật UI classification cho staging. Production rollout theo workspace sau khi staging evidence đạt tiêu chí §5.
