# Knowledge

## 1. Mục đích

RAG substrate: source → source_version → chunks → embeddings, có provenance và authority class (REFERENCE/POLICY/BUSINESS_SNAPSHOT/USER_CONTENT/EXTERNAL).

## 2. Khi nào sử dụng

Khi agent cần tra cứu tài liệu nội bộ (policy, handbook, spec) qua tìm kiếm chunk.

## 3. Không dùng cho việc gì

`BUSINESS_SNAPSHOT` KHÔNG thay thế live business query — Company Service vẫn là nguồn sự thật cho state hiện tại.

## 4. Kiến trúc và luồng dữ liệu

**Phát hiện quan trọng (Wave 8, 2026-08-24):** schema `knowledge.knowledge_sources`/`knowledge_chunks` đã tồn tại từ migration 003 (Wave 0) nhưng **chưa từng có `PostgresKnowledgeStore`** — chỉ có `InMemoryKnowledgeStore`. Toàn bộ subsystem chạy in-memory dù schema durable sẵn sàng từ đầu.

`PostgresKnowledgeStore.save_document()` tự tạo `source_version` MỚI khi nội dung đổi (content_hash tổng hợp từ toàn bộ chunk theo `chunk_index`), giữ lịch sử version thay vì ghi đè:

```
save_document(doc)
  → compute content_hash (sha256 của các chunk nối theo chunk_index)
  → INSERT/UPDATE knowledge_sources
  → nếu content_hash != version gần nhất → INSERT source_versions (version+1)
  → INSERT/UPDATE knowledge_chunks (link source_version_id) + chunk_embeddings (nếu có)
```

## 5. Public contracts/API

`agent_core.knowledge.store.KnowledgeStore` (Protocol), `get_knowledge_store()` (factory). `agent_core.knowledge.models.KnowledgeDocument/KnowledgeChunk/CitationProvenance`.

## 6. Database/schema liên quan

Schema `knowledge` (migration 003, 010): `knowledge_sources` (+ `authority_class`/`status`/scope), `source_versions` (mới), `knowledge_chunks` (+ `source_version_id`/`chunker_name`), `chunk_embeddings` (mới — nhiều embedding/chunk, khác model không mất embedding cũ).

## 7. Cấu hình

`AGENT_CORE_DATABASE_URL`.

## 8. Ví dụ sử dụng

```python
store = get_knowledge_store()
await store.save_document(doc)
results = await store.search_chunks(workspace_id="ws1", query="chính sách nghỉ phép")
```

## 9. Cách bổ sung implementation mới

Implement `KnowledgeStore` Protocol 3 method.

## 10. Security/governance

`authority_class` phân loại độ tin cậy nguồn — chưa có enforcement tự động (đọc để hiển thị/lọc, chưa gate truy cập).

## 11. Error handling

Không có exception riêng ngoài `ConfigurationError` (thiếu session factory).

## 12. Observability

Không có event riêng.

## 13. Testing

`tests/agent_core/knowledge/providers/test_postgres_knowledge_store.py` (logic không cần DB test được trực tiếp; I/O roundtrip cần `AGENT_CORE_TEST_DATABASE_URL`, hiện skip).

## 14. Migration/backward compatibility

Migration 010 additive — cột embedding inline cũ trên `knowledge_chunks` (migration 003) giữ nguyên cho code cũ, không xoá.

## 15. Troubleshooting

`search_chunks()` hiện là ILIKE keyword search, KHÔNG phải semantic/vector search thật — cần benchmark index/model cụ thể trước khi xây (để lại có chủ đích, xem §3 code comment).

## 16. Definition of Done

- [x] Source versioning, chunk_embeddings, PostgresKnowledgeStore hoàn toàn mới, test content-hash logic
- [ ] Vector/semantic search thật (hiện chỉ keyword)
- [ ] Chạy trên Postgres thật

---

## 17. Governed document ingestion — Phase A (MarkItDown)

Người dùng tải tài liệu (PDF, DOCX, XLSX, PPTX, HTML, CSV, plain text) → chuyển thành
Markdown chuẩn hoá → tạo **candidate** để người duyệt xét, KHÔNG tự động vào retrieval.

### 17.1 Luồng

```
browser
  → POST /agent/knowledge/uploads            (member) → upload ticket (server-owned object key)
  → PUT signed_url                            (bytes vào quarantine object store)
  → POST /agent/knowledge/uploads/{id}/complete (broker, worker token)
       → services/cosa: UPLOADING → QUARANTINED → QUEUED + scheduler task
  worker (image Dockerfile.ingestion-worker, KHÔNG có parser trong image API/worker thường):
    claim (QUEUED→VALIDATING) → load bytes → preflight (MIME magic, size, ZIP-bomb)
    → malware scan (chỉ 'clean' đi tiếp) → sandbox convert (chỉ convert_stream, plugins off)
    → normalize (anchor sec-NNN, chunk document-section-v1) → persist candidate
    → record_candidate (VALIDATING→REVIEW_PENDING, gắn knowledge_source_id + manifest)
  → POST /agent/knowledge/ingestions/{id}/review  (member) publish_reference | reject
       → services/cosa audit + flip KnowledgeDocument.ingest_status
```

### 17.2 Trạng thái & quy tắc

- Candidate: `authority_class="USER_CONTENT"`, `ingest_status="review_pending"` (thêm cùng
  `published`/`rejected`; 4 trạng thái cũ `pending/processing/completed/failed` giữ nguyên).
- **Không retrieval trong Phase A**: `retrieve_citations()`/`search_chunks()` KHÔNG được
  gọi hay sửa cho candidate. Retrieval-aware access, authority/status/sensitivity gating,
  KnowledgeSnapshot đã publish, citation anchors, evals → thuộc **Phase B** (plan riêng,
  chỉ bắt đầu sau khi Phase A xanh).
- Provenance: `knowledge.source_versions.{ingestion_run_id, parser_name, parser_version}`
  được điền từ metadata candidate (`ingestion_id`, `converter_name`, `converter_version`);
  extraction manifest (`schema_version="cosa.document-extraction-manifest/v1"`) chứa
  converter profile, source/markdown SHA-256, anchors, warnings.
- Chỉ mã trong allowlist (`FailureCode`/`warning_code`) xuất hiện ở API/queue/log/metric —
  không nội dung, object key, signed URL, parser traceback, scanner body.
- Metric schema cố định: `{ingestion_id, workspace_id, state, detected_media_type,
  size_bytes, duration_ms, failure_code?, warning_codes?}` (`IngestionMetricEvent`).

### 17.3 Release controls

- Feature flag fail-closed `KNOWLEDGE_INGESTION_ENABLED` — kiểm ở ticket issuance (API) và
  worker start (handler) qua `knowledge_ingestion_enabled()`.
- `assert_production_ingestion_ready(environment)` — cổng ENTRYPOINT của image ingestion.
  Khi `ENVIRONMENT=production` đòi: flag bật, storage prefix policy hợp lệ,
  `KNOWLEDGE_INGESTION_SCANNER_BACKEND` không fake/none,
  `KNOWLEDGE_INGESTION_SANDBOX_BACKEND` không inprocess/none,
  `KNOWLEDGE_INGESTION_EGRESS_DENY_ATTESTED` + `KNOWLEDGE_INGESTION_RESOURCE_LIMITS_ATTESTED`
  = true, `KNOWLEDGE_INGESTION_CONVERTER_SPEC` == `markitdown[pdf,docx,pptx,xlsx]==0.1.7`.
  Container KHÔNG boot nếu thiếu — không phải warning log.
- `assert_production_conversion_ready(sandbox, scanner, environment)` — cổng tại thời điểm
  xử lý job (kiểm instance thật, không phải InProcess/Fake).
- Docker Compose `cosa-ingestion-worker` là tiện lợi dev; **network Compose một mình KHÔNG
  cấp egress isolation production** — cần orchestrator (K8s NetworkPolicy deny-all, gVisor…).
- `make knowledge-ingestion-test` chạy bộ test tập trung (in-memory, không cần DB); đã đưa
  vào `make verify-local`.

### 17.4 Runbook

- **Unpublish / gỡ candidate đã publish**: gọi lại review endpoint với `decision="reject"`
  cho ingestion tương ứng (REVIEW_PENDING mới cho review; với candidate đã PUBLISHED cần
  thao tác thủ công: `KnowledgeIngestionService.update_document_ingest_status(source_id,
  "rejected")` + audit ở services/cosa). Retention: candidate `rejected`/`failed` và object
  quarantine hết hạn → EXPIRED; dọn object store theo TTL bucket `quarantine/`.
- **Migration**: `services/cosa/migrations/15_document_ingestions.up.sql`. Lưu ý dev:
  `services/cosa/storage/client.ts` mặc định DSN `...@127.0.0.1:5434/cosa` khi
  `COSA_DATABASE_URL` chưa set — KHÁC DB trong `.env` gốc (`5432/cosa_control_plane`).
  Chạy `cd services/cosa && COSA_DATABASE_URL=<dsn 5434> node scripts/migrate.mjs` để test
  vitest local thấy bảng.
- **Phase B prerequisites**: bằng chứng Phase A xanh (unit + hostile-file + vertical +
  tenancy + boundary); chưa mở rộng branch này sang retrieval/business automation. Trích
  xuất process chỉ được tạo `ProcessKnowledgeProposal` có citation — activation thuộc chủ
  sở hữu `services/company` với Capability Gateway/approval/audit riêng.
