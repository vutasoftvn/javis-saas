# Thiết kế Local-first Enterprise Knowledge cho COSA

## Mục tiêu

Triển khai Vault Document API và Knowledge ingestion để mỗi Workspace Runtime
Node sở hữu tài liệu gốc, dữ liệu chuyển đổi, chunk, embedding và chỉ mục
retrieval của chính workspace đó. Founder được đọc toàn bộ tri thức của
workspace; member chỉ nhận tài liệu và chunk được policy cấp quyền. Agent không
đọc filesystem, object store hoặc business database trực tiếp.

## Quyết định

1. **Local-first là bắt buộc.** Không dùng S3 làm storage authority hay
   dependency của lõi. Local workspace ghi vào persistent volume của node qua
   `WorkspaceDocumentStore`; cloud workspace có thể cài adapter storage riêng
   sau này. Không copy raw file, filename, raw chunk hoặc embedding lên VPS.
2. **Vault là canonical asset registry.** Một Vault document có version bất
   biến; Knowledge source/version/chunk chỉ là dẫn xuất có provenance tới đúng
   Vault version. Ingestion job là lịch sử vận hành, không phải nguồn quyền đọc.
3. **Một permission resolver.** Mọi list, detail, download, retrieval, citation
   và injection vào chat gọi cùng resolver. Lọc quyền xảy ra trong truy vấn,
   trước semantic/lexical ranking. Founder có `knowledge.read.all` trong đúng
   workspace; member phải thỏa đồng thời role grant và document grant.
4. **GraphQL là lớp đọc local cho AI và UI.** Agent không gửi raw GraphQL
   tùy ý. Capability `workspace.context.read` chỉ chạy persisted query/view
   đã allowlist trên Workspace Runtime Node; từng resolver nhận principal,
   workspace và policy snapshot, rồi tự áp authorization. GraphQL không có
   mutation trong milestone này.
5. **Write là command có audit.** Upload, complete, review, publish, archive,
   purge và grant/revoke quyền là REST command có actor, workspace, idempotency
   và audit. Không cho model gọi mutation storage hay database trực tiếp.
6. **Control Plane chỉ nhận telemetry đã sanitize.** State/job scheduler, raw
   object reference và audit chi tiết chạy tại execution plane local. Platform
   chỉ có event aggregate không chứa nội dung, filename, object key hay chunk.

## Phân lớp dữ liệu

| Lớp | Local node giữ | Không được gửi Platform |
|---|---|---|
| Vault version | file gốc, checksum, local object ref, retention/legal hold | file, filename, đường dẫn, object ref |
| Ingestion | upload ticket hash, scanner/converter result, trạng thái retry | raw error, object key, nội dung |
| Knowledge | markdown chuẩn hóa, chunks, embeddings, provenance | text/chunk/embedding |
| Retrieval audit | principal, document/version/chunk IDs, decision, run ID | chỉ metric aggregate đã redact |

## Vòng đời

`DRAFT → UPLOADING → QUARANTINED → VALIDATING → CONVERTING → REVIEW_PENDING
→ PUBLISHED → ARCHIVED → PURGED`.

`REJECTED`, `FAILED`, `EXPIRED` là trạng thái terminal/operational của một
version ingestion. Một version mới của document đã `PUBLISHED` tạo bản
`REVIEW_PENDING`; version cũ vẫn là nguồn active cho đến khi bản mới được
publish. `PURGED` lập tức loại document/version khỏi retrieval, sau đó xóa file
và derived chunks theo retention nếu không có legal hold.

## Quyền mặc định

- `founder`, `co-founder`, `admin`: `discover/read/download/manage/review/publish`
  với mọi document thuộc workspace.
- `knowledge_reviewer`: `discover/read/review/publish` với document được giao;
  không tự động có `manage` hay đọc `RESTRICTED` ngoài grant.
- `member`: chỉ `discover/read/download` khi có role policy phù hợp
  classification và grant theo workspace/role/team/user; upload mặc định tạo
  tài liệu private của chính người upload.
- Credential, token và secret không trở thành Vault document/Knowledge source.
  Dữ liệu có classification `RESTRICTED` cần grant rõ ràng; không đưa nguyên
  văn vào log, telemetry hoặc prompt.

## Chính sách model local-first và founder-managed

Mỗi agent luôn có system default đã pin để workspace chạy được ngay. Founder,
co-founder hoặc admin có thể tạo `WorkspaceModelPolicy` bằng UI để chọn default
và fallback cho từng agent profile hoặc toàn workspace. Thứ tự resolve là:

1. model policy đã pin của run/workflow, nếu policy đó được workspace cho phép;
2. override theo agent profile của workspace;
3. default model của workspace;
4. system default đã publish/pin.

Không có fallback ngầm sang provider khác. Khi provider hết quota, offline hoặc
bị data-policy từ chối, worker chỉ thử fallback theo thứ tự founder đã lưu và
audit từng attempt; nếu hết danh sách, run trả `model_provider_unavailable`.

| Type | Cách chạy | Credential/điều kiện |
|---|---|---|
| `local_openai_compatible` | endpoint local của Ollama/vLLM/llama.cpp hay gateway tương thích | không cần key hoặc key local do founder cấu hình |
| `anthropic_api` | Claude qua API | API key mã hóa tại local node |
| `openai_api` | OpenAI API | API key mã hóa tại local node; không suy diễn entitlement từ gói ChatGPT |
| `openrouter_api` | OpenRouter API | API key mã hóa tại local node |
| `deepseek_api` | DeepSeek API | API key mã hóa tại local node; đây là system default hiện tại nhưng có thể bị workspace override |
| `claude_cli` / `codex_cli` / `gemini_cli` | local model bridge gọi executable allowlist trên node | CLI cài và đăng nhập cục bộ, explicit enable; không sao chép browser/session token vào COSA |

CLI adapter là integration `EXPERIMENTAL`: bridge chỉ nhận request typed,
executable path allowlist, timeout/concurrency/budget cứng và không cấp shell
tool cho model. Nếu CLI/provider không hỗ trợ automation ổn định hoặc account
không cấp quyền, status là unavailable thay vì giả fallback.

Secrets chỉ tồn tại trong local credential store được mã hóa bằng key của node;
frontend không lưu key và Platform Control Plane không nhận key, prompt hay
usage chi tiết. Founder có thể test connection, xoay/revoke credential, đặt
budget/concurrency/model allowlist và xem audit đã redact. Founder không được
override compliance: provider/model/purpose/retention bị policy dữ liệu cấm thì
run fail-closed trước khi gửi prompt ra ngoài node.

## Contract public dự kiến

- `POST /agent/vault/documents`: tạo document + version `UPLOADING`, trả local
  upload target một lần; workspace lấy từ identity, không từ request body.
- `PUT /agent/vault/uploads/{upload_id}/content`: local runtime nhận stream có
  ticket, ghi atomically vào quarantine; không tin MIME/checksum từ client.
- `POST /agent/vault/uploads/{upload_id}/complete`: finalize authoritative,
  enqueue ingestion local với idempotency/fencing.
- `GET /agent/vault/documents`, `GET /agent/vault/documents/{id}`: trả metadata
  đã permission-filtered; unauthorized ID trả `404` để không enumerate.
- `POST /agent/vault/documents/{id}/review`, `/publish`, `/archive`, `/purge`:
  command tách bạch, audit đầy đủ.
- `POST /agent/knowledge/retrieve`: query có identity; kết quả là citation gồm
  document/version/chunk/section/score, chỉ từ nguồn `PUBLISHED` được phép đọc.

Chat dùng capability `knowledge.enterprise.read` gọi cùng retrieval service.
`POST /agent/graphql` chạy trên local runtime, chỉ nhận `operationId` và
variables đã validate; không nhận `query` text từ agent. Hai operation đầu là
`workspaceContext` (tóm tắt business/knowledge theo quyền) và
`enterpriseKnowledgeSearch` (citation đã lọc). GraphQL không thay đổi contract
authorization, không truy cập storage trực tiếp và không có mutation.

## Không nằm trong scope phát hành đầu

- Đồng bộ Google Drive/Dropbox/SharePoint.
- OCR cho ảnh và document handwriting.
- Knowledge graph/backlink được AI suy luận.
- Cloud object storage hoặc replication cross-node.

## Điều kiện phát hành

Không bật feature flag hay Vault UI cho tới khi có: local persistent storage,
malware scanner thật, sandbox converter cô lập/no-egress, migration RLS
fail-closed, permission-filtered retrieval, audit, process-restart test và
Postgres/local-volume integration test.

Model routing chỉ phát hành khi có test precedence default/override/fallback,
cross-workspace credential isolation, redaction, provider deny, quota exhaustion
và local CLI bridge timeout/cancellation. ChatGPT/API entitlement được xác minh
ở bước thiết lập credential; không suy diễn từ loại subscription của người dùng.
