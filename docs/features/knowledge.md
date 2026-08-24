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
