# MarkItDown cho tri thức doanh nghiệp COSA — Design Specification

**Trạng thái:** đề xuất triển khai theo phase

**Ngày:** 2026-08-27

**Phạm vi:** `apps/cosa`, `services/cosa`, `packages/agent_core/knowledge`, hạ tầng object storage và review vận hành
**Nguồn:** [Microsoft MarkItDown README](https://github.com/microsoft/markitdown/blob/main/README.md), [package manifest](https://github.com/microsoft/markitdown/blob/main/packages/markitdown/pyproject.toml), [converter implementation](https://github.com/microsoft/markitdown/blob/main/packages/markitdown/src/markitdown/_markitdown.py), [MCP implementation](https://github.com/microsoft/markitdown/blob/main/packages/markitdown-mcp/src/markitdown_mcp/__main__.py), [COSA Knowledge](../../features/knowledge.md).

## 1. Quyết định

Tích hợp **MarkItDown như thư viện chuyển đổi nằm bên trong một ingestion pipeline có kiểm soát của COSA**, không nhúng dự án, không chạy `markitdown-mcp`, không để agent hoặc browser gọi converter trực tiếp.

MarkItDown phù hợp để chuẩn hoá PDF, Word, Excel, PowerPoint, HTML, CSV và text thành Markdown hướng tới phân tích LLM. Nó không thay thế kho tri thức, phân quyền, versioning, semantic retrieval, kiểm duyệt policy hay workflow engine. COSA đã có `knowledge_sources` → `source_versions` → `knowledge_chunks`, durable scheduler và Workspace tenancy; MarkItDown chỉ lấp phần thiếu là **document-to-markdown extraction**.

```text
Browser / connector
        │ server-authorized upload ticket; never a client URI
        ▼
Private quarantine object store ──► malware + type/archive preflight
        │                                  │ reject / retain evidence
        ▼                                  ▼
Isolated conversion runner ── MarkItDown.convert_stream(..., enable_plugins=False)
        │
        ▼
Normalized Markdown + extraction manifest + immutable source checksum
        │
        ▼
Agent Core Knowledge: source → version → section-aware chunks
        │
        ▼
Review queue ──► published source / pinned KnowledgeSnapshot ──► governed retrieval (Phase B)
                                  │
                                  └──► process proposal / human activation (Phase C)
```

Một document được upload là dữ liệu **không tin cậy**. Nó không được đưa nguyên văn vào prompt, không tự trở thành `POLICY`, không tự kích hoạt workflow và không thể thay thế dữ liệu live trong `services/company`.

## 2. Hiện trạng COSA và khoảng trống cần lấp

| Năng lực hiện có | Bằng chứng trong codebase | Khoảng trống cần bổ sung |
| --- | --- | --- |
| Kho knowledge versioned | `packages/agent_core/knowledge`, migrations 003/010, `PostgresKnowledgeStore` | Chưa có document ingestion boundary hay manifest chuyển đổi. |
| Chunk provenance cơ bản | `KnowledgeChunk.page_or_section`, `CitationProvenance` | Converter không trả source location chuẩn; cần anchor/section manifest riêng. |
| Authority class | `REFERENCE`, `POLICY`, `BUSINESS_SNAPSHOT`, `USER_CONTENT`, `EXTERNAL` | `search_chunks()` hiện chỉ ILIKE theo Workspace, chưa filter authority/status/sensitivity. Không được nối vào agent trước Phase B. |
| Durable worker | `apps/cosa/worker/main.py`, scheduler có claim/fencing/retry | Dispatcher hiện mặc định task phải có `run_id`/lease. Ingestion cần lifecycle độc lập, không giả là agent run. |
| Attachment metadata | `MessageAttachmentRecord` giữ `object_ref`, checksum, trạng thái ingest | API hiện nhận `object_ref` từ client. Giá trị này không thể là quyền đọc object hay nguồn tri thức đáng tin. |
| Object storage dev | MinIO có trong `docker-compose.yml` | Chưa có broker/upload ticket/scanning/private object policy. |

Điều này cũng có nghĩa: việc gọi `KnowledgeIngestionService.ingest_raw_text()` hiện tại trực tiếp từ attachment là không đủ an toàn. Hàm đó hữu ích sau khi text đã được chuẩn hoá và có provenance, nhưng không phải ingress public.

## 3. Đánh giá MarkItDown

### 3.1 Điểm có ích

- Thư viện Python, MIT, yêu cầu Python 3.10+, có optional extras theo từng định dạng thay vì bắt buộc toàn bộ ecosystem.
- Chuyển PDF, DOCX, XLSX, PPTX, HTML, CSV và text sang Markdown phù hợp với pipeline chunk/retrieval của COSA.
- Có thể gọi `convert_stream(stream, stream_info=...)`, cho phép COSA tự kiểm soát bytes trước khi converter nhìn thấy chúng.
- Kết quả có `markdown` và `title`, phù hợp làm input cho normalizer; knowledge store hiện đã hỗ trợ source version và chunk metadata.

### 3.2 Rủi ro và quyết định giảm thiểu

| Quan sát | Rủi ro nếu dùng thẳng | Quyết định COSA |
| --- | --- | --- |
| `convert_uri()` nhận `http`, `https`, `file`, `data` URI và tải nội dung bằng HTTP client | SSRF, đọc file cục bộ, vượt object policy | Cấm `convert_uri()`/CLI/MCP ở production. Chỉ gọi `convert_stream()` với bytes do broker đã xác thực. |
| Plugin entry point có thể được load khi bật plugins | Code tùy ý chạy trong worker | Luôn `enable_plugins=False`; không cài plugin bên thứ ba. |
| Generic ZIP converter đọc archive và member trong bộ nhớ | Zip bomb, recursive archive, DoS | Cấm generic ZIP; DOCX/XLSX/PPTX phải qua ZIP preflight trước converter. |
| Stream không seekable có thể bị đọc toàn bộ vào memory | Memory exhaustion | Broker stream có limit; size input/output/time/memory được enforce bởi runner. |
| Converter result chỉ có Markdown/title | Citation sai nguồn hoặc không audit được extract | COSA tạo extraction manifest, chunk anchor, checksum và parser profile riêng. |
| `markitdown-mcp` nhận URI, hỗ trợ `file:`/`data:`, không phải gateway có auth | Remote file exposure/capability bypass | Không expose MCP server này cho agent, browser, connector hay mạng nội bộ. |
| Azure Document Intelligence/Content Understanding là optional cloud integration | dữ liệu, region, chi phí, vendor lock-in | Không thuộc Phase A; chỉ cân nhắc sau DPA, allowlist region, budget và evaluator riêng. |

## 4. Mục tiêu và phi mục tiêu

### Mục tiêu Phase A

1. Người dùng có quyền trong đúng Workspace upload tài liệu doanh nghiệp vào private quarantine storage qua server-issued ticket.
2. Một worker bền vững xác minh, scan, convert và chuẩn hoá file cho phép thành `KnowledgeDocument` versioned với source checksum, converter version và section provenance.
3. Output chỉ là **knowledge candidate chờ review**, mặc định `USER_CONTENT`; không có tool/agent nào retrieve candidate ở Phase A.
4. Reviewer có thể xem metadata/Markdown redacted, reject hoặc publish thành `REFERENCE`. Nâng lên `POLICY` hoặc `BUSINESS_SNAPSHOT` cần workflow/owner riêng ở Phase C.
5. Mọi retry idempotent theo ingestion ID + source SHA-256, audit không ghi raw document/secret vào log hay queue.

### Phi mục tiêu Phase A

- Không URL/web crawl, `file://`, `data:`, YouTube, email MSG, audio, image OCR hoặc generic ZIP.
- Không dùng `[all]`, plugins, LLM extraction, Azure dịch vụ, MarkItDown MCP hoặc external URI.
- Không semantic search, embeddings, answer-time RAG hay injection document vào conversation prompt.
- Không biến SOP/tài liệu thành Company task, workflow, policy hoặc capability tự động.
- Không ghi đè `services/company` business truth bằng bản sao từ file.

## 5. Contract và state machine

### 5.1 `DocumentIngestionRecord`

Control Plane sở hữu trạng thái vận hành; Agent Core chỉ sở hữu knowledge normalized. Bản ghi có dữ liệu tối thiểu:

```ts
type DocumentIngestionState =
  | "UPLOADING" | "QUARANTINED" | "QUEUED" | "VALIDATING"
  | "CONVERTING" | "REVIEW_PENDING" | "PUBLISHED"
  | "REJECTED" | "FAILED" | "EXPIRED";

interface DocumentIngestionRecord {
  id: string;                         // ing_<random>; opaque
  workspaceId: string;                // server-authoritative
  createdBy: string;                  // platform principal
  originalObjectKey: string;          // private `quarantine/...`, never browser supplied
  originalFilename: string;           // display only; never used to infer type
  declaredMediaType: string | null;
  detectedMediaType: string | null;
  sizeBytes: number | null;
  sourceSha256: string | null;
  state: DocumentIngestionState;
  idempotencyKey: string;
  knowledgeSourceId: string | null;
  converterProfile: string | null;    // `markitdown-safe-v1`
  converterVersion: string | null;    // installed package version
  extractionManifest: Record<string, unknown> | null;
  failureCode: string | null;         // allowlisted; no raw parser error
  createdAt: string;
  updatedAt: string;
}
```

`originalObjectKey`, any signed upload target, scan response, parser stderr and raw Markdown are never returned by public list endpoints. Public response only includes ID, file name, detected type, state, allowed failure code, timestamps and optional knowledge source ID after review.

### 5.2 Chuyển trạng thái

```text
UPLOADING --complete+verify--> QUARANTINED --schedule--> QUEUED
QUEUED --> VALIDATING --> CONVERTING --> REVIEW_PENDING --> PUBLISHED
                    └──> REJECTED                      └──> REJECTED
                    └──> FAILED --bounded retry--> QUEUED
Any non-terminal state --retention TTL--> EXPIRED
```

- Chỉ worker service được chuyển `QUEUED` → `VALIDATING` → `CONVERTING`.
- `PUBLISHED` hoặc `REJECTED` là terminal đối với bản source hiện tại. File mới tạo ingestion/source version mới, không ghi đè chứng cứ cũ.
- Retry chỉ áp dụng lỗi hạ tầng allowlisted; malware, MIME mismatch, archive limit, unsupported type, converter policy violation và checksum mismatch là `REJECTED`.
- Claim token của scheduled task phải được kiểm tra khi complete. Không có retry nào được phép tạo version/chunk thứ hai cho cùng ingestion/source SHA-256.

### 5.3 Knowledge candidate

Khi convert thành công, worker tạo `KnowledgeDocument` với:

| Field | Giá trị Phase A |
| --- | --- |
| `id` | ID source do server tạo, lưu ngược vào ingestion record |
| `workspace_id` | workspace từ record, không từ body/task/model |
| `source_uri` | `object://knowledge-ingestions/<ingestion-id>` opaque, không dereference ở client |
| `media_type` | detected MIME đã allowlist |
| `checksum` | SHA-256 file gốc; Markdown checksum lưu trong metadata/version hash |
| `authority_class` | `USER_CONTENT` |
| `ingest_status`/source status | `review_pending`; không được consumer retrieval xem là published |
| `metadata` | ingestion ID, source hash, manifest version, converter package/version/profile, scan verdict, source version provenance |

Mỗi `KnowledgeChunk` có `chunker_name="document-section-v1"`, `chunker_version="1"`, `content_hash`, `page_or_section` là heading/worksheet/slide anchor đã kiểm chứng và metadata chứa `anchor_id`. Không tự tạo page number nếu converter không bảo đảm page mapping.

### 5.4 Extraction manifest

Manifest là dữ liệu canonical để reviewer/auditor biết tri thức đã đi từ đâu, không phải source document thay thế. Dạng v1:

```json
{
  "schema_version": "cosa.document-extraction-manifest/v1",
  "ingestion_id": "ing_...",
  "source_sha256": "...",
  "detected_media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "converter": {"name": "markitdown", "version": "0.1.7", "profile": "markitdown-safe-v1"},
  "markdown_sha256": "...",
  "anchors": [
    {"id": "sec-001", "kind": "heading", "label": "3. Quy trình phê duyệt", "ordinal": 1}
  ],
  "warnings": ["table_structure_degraded"],
  "generated_at": "2026-08-27T00:00:00Z"
}
```

Warning phải là enum allowlist. Nó cho phép reviewer biết khi table/layout/OCR không đáng tin thay vì model âm thầm coi bản convert là chính xác.

## 6. Boundary bảo mật và vận hành

### 6.1 Định dạng và quota an toàn ban đầu

| Nhóm | Phase A allowlist | Ràng buộc bắt buộc |
| --- | --- | --- |
| Text | `text/plain`, `text/csv`, `text/html` | SHA-256, UTF-8 normalize/reject invalid encoding theo policy, tối đa 10 MiB. |
| PDF | `application/pdf` | magic type match, tối đa 25 MiB, 90 giây conversion. |
| Office | DOCX, XLSX, PPTX MIME chuẩn | magic type + ZIP preflight: tối đa 25 MiB compressed, 1,000 members, 100 MiB uncompressed, 20:1 compression ratio, 50 MiB/member. |

Toàn bộ output Markdown bị chặn tại 10 MiB và 20,000 chunks/source. Mặc định vượt limit là `REJECTED` với code rõ ràng. Các giá trị nằm trong policy config versioned và phải có metric để điều chỉnh; không dùng filename/extension làm bằng chứng MIME.

### 6.2 Upload và object storage

1. API xác thực identity, chứng minh Workspace membership và tạo ingestion record `UPLOADING` trước.
2. Nó tạo object key ngẫu nhiên dưới private prefix `quarantine/<workspace-id>/<ingestion-id>/original`; browser chỉ nhận signed PUT/POST có expiry ngắn, content-length range và key cố định.
3. Sau upload, browser chỉ gọi “complete upload” bằng ingestion ID. Broker HEAD object, tính SHA-256 từ object bytes và MIME sniff server-side; client checksum/size chỉ dùng chẩn đoán, không phải truth.
4. Quarantine bucket không public, không list bởi browser, không dùng object key như URL; read chỉ từ worker identity có prefix/workspace validation.
5. Original giữ theo retention policy; candidate Markdown/manifest nằm ở private normalized prefix. Delete/expiry phải tombstone knowledge source theo policy, không âm thầm xoá audit history.

Không tái dùng `MessageAttachmentCreate.object_ref` như URI quyền lực. Nếu cần liên kết chat, attachment chỉ giữ `ingestion_id` opaque và status do server trả về.

### 6.3 Scanner và sandbox

- Malware scanner là mandatory production dependency. Interface có thể test bằng fake scanner, nhưng deployment validator phải từ chối production khi scanner là fake/unconfigured hoặc verdict timeout.
- Conversion runner chạy non-root, filesystem tạm riêng theo job, read-only dependency root, không secret business/LLM/connector, CPU/memory/pid/time limit và egress deny. Chỉ broker bên ngoài sandbox có quyền object storage/control-plane.
- Converter subprocess/container nhận bytes đã scan qua stream/mount read-only và chỉ trả Markdown + allowlisted diagnostics. Nó không có network, không được đọc host path hay environment secrets.
- No `convert_uri`, `convert_local`, CLI mode accepting path/URI, plugin entry points, `[all]`, or arbitrary `requests.Session` in worker code.
- Logs, metric labels, queue payload và error response chỉ chứa ingestion ID, workspace hash/ID theo policy, type, byte counts, version và failure code. Không log content, filename nhạy cảm, object key, signed URL, scan body hoặc parser traceback.

## 7. Review, knowledge và quy trình doanh nghiệp

### 7.1 Review gate

`REVIEW_PENDING` là ranh giới bắt buộc trước khi document có thể được chọn vào KnowledgeSnapshot. Reviewer xác nhận:

1. đúng Workspace và quyền sở hữu;
2. loại/nguồn/tính mới của tài liệu;
3. Markdown không bị mất ngữ cảnh nghiêm trọng (heading, table, encoding, warning);
4. authority phù hợp: mặc định publish thành `REFERENCE`;
5. sensitivity/redaction policy trước khi retrieval được bật.

Reviewer action tạo audit record có principal, timestamp, old/new state, selected authority, source/version checksum và reason. Không có bulk “approve all”.

### 7.2 Tài liệu quy trình không tự là workflow

Sau publish, một phase sau có thể tạo `ProcessKnowledgeProposal` từ source/version đã pin:

```json
{
  "source_ref": {"source_id": "doc_...", "version": 3, "content_hash": "..."},
  "proposed_steps": [],
  "roles": [],
  "approval_points": [],
  "systems_of_record": [],
  "open_questions": [],
  "requires_human_activation": true
}
```

Đây là proposal có citation, không phải lệnh thực thi. Chỉ owner tại `services/company` có thể map proposal đã được duyệt vào business workflow/capability. Policy doanh nghiệp cần một lifecycle riêng; `POLICY` không được gán chỉ vì file có chữ “quy định”.

### 7.3 Retrieval và snapshot (Phase B)

Phase A **không gọi** `KnowledgeIngestionService.retrieve_citations()` từ agent, vì implementation hiện tại không filter `authority_class`, source `status`, role hoặc sensitivity. Để release retrieval phải bổ sung:

- `KnowledgeAccessContext` server-authoritative gồm Workspace, principal/role, allowed authority class, sensitivity ceiling và snapshot pin;
- repository query filter trước ranking theo `workspace_id`, `status='published'`, authority/sensitivity và source version;
- hybrid retrieval/evaluation cụ thể trước pgvector/BM25; citation phải trả source/version/anchor, không chỉ snippet;
- KnowledgeSnapshot chỉ chứa source versions đã review/publish, có retrieval evaluator và definition hash.

`BUSINESS_SNAPSHOT` vẫn là derived evidence, không thay `services/company` live query. `POLICY` chỉ là context cho model sau khi policy owner publish version đúng lifecycle.

## 8. Phased roadmap và release gates

| Phase | Deliverable | Gate mở phase | Không bao gồm |
| --- | --- | --- | --- |
| 0 | Upload broker, record lifecycle, scan + type/archive guard, isolated MarkItDown conversion, candidate/review UI/API | workspace tenancy tests, storage/scanner/sandbox config, red-team files pass | retrieval/agent context |
| B | Access-aware retrieval + KnowledgeSnapshot + citation UI/evals | 100% cross-workspace/status/authority tests; review audit verified | process activation |
| C | Process proposal, policy promotion workflow, Company-owner activation | human review and business owner approval, eval against source anchors | autonomous workflow changes |
| D | Approved connectors/cloud extraction/OCR | DPA/region/cost cap/egress policy and per-connector tests | generic external URL ingest |

**Phase A Definition of Done**

- Browser cannot choose a storage key/URI, read another Workspace’s upload or cause server-side URL/file fetch.
- Unsupported/oversized/archive-bomb/mime-mismatch/malware files are terminally rejected with no Markdown/chunk persisted.
- Plugins and network are demonstrably disabled in converter runtime; production config rejects an unsandboxed or unscanned path.
- Same completed upload/retry creates at most one source/version for the same ingestion ID and source SHA-256.
- Candidate source is never returned by current retrieval path or injected into agent prompt.
- Reviewer can publish/reject with immutable audit evidence; published reference preserves source/markdown/converter/chunker provenance.
- Unit, integration, cross-Workspace, malicious-input, crash/retry and release smoke tests pass.

## 9. Dependencies, versions và supply chain

Phase A pins `markitdown[pdf,docx,pptx,xlsx]==0.1.7`; it does not install `markitdown[all]`. Build must record package hashes/lock resolution and expose a software bill of materials in the container build artifact. A package upgrade is a change to `converter_profile` and requires fixture regression (PDF/DOCX/XLSX/PPTX/HTML/CSV), performance/memory checks, malware/archive cases and review of newly pulled optional dependencies.

The Python conversion image is separate from normal model agent worker. The normal agent worker must not acquire document parser extras merely because an ingestion feature exists. Dev fake object store/scanner/sandbox implementations are explicit and cannot be selected under production environment settings.

## 10. Observable signals and runbook

Metrics per workspace only where privacy policy permits: intake count, state transitions, bytes, conversion duration, output-to-input ratio, warning enums, rejection/failure codes, retry count, scan latency, queue age and review age. Alert on queue age/retry burst, scanner unavailable, conversion timeout/memory failure and conversion ratio anomalies.

Runbook actions:

1. **Scanner unavailable:** stop moving records past `QUARANTINED`; do not fail-open.
2. **Converter regression:** disable `markitdown-safe-v1` feature flag, retain quarantined originals, inspect only redacted diagnostics/fixture reproduction.
3. **Suspicious source:** set record/source `REJECTED`, revoke candidate from pending queue, preserve audit/forensic metadata per retention policy.
4. **Published bad source:** unpublish the exact source/version and remove it from the next snapshot; do not mutate historical version content.
5. **Storage breach suspicion:** rotate object-store credentials, invalidate signed upload URLs, scope investigation by object prefix and ingestion IDs.

## 11. Open decisions deliberately deferred

- Production malware provider and egress enforcement mechanism must be selected with infrastructure/security owner before production enablement. The contract is fixed; vendor is not assumed here.
- OCR quality, scanned PDFs, image/audio/video conversion and Azure services are deferred until cost/privacy/eval data exists.
- Semantic model, vector index and retrieval ranking remain a benchmarked Phase B decision; no unmeasured pgvector query is prescribed.
- Actual activation of a documented process remains owned by the relevant Company bounded context; no generic “document-to-workflow” automation is approved.

The detailed implementation order, test-first steps and precise file map are in [MarkItDown Knowledge Ingestion Phase A plan](../plans/2026-08-27-markitdown-knowledge-ingestion-phase-a.md).
