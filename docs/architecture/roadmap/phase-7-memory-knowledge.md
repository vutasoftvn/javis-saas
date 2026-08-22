# Phase 7 — Memory & Knowledge

> Chi tiết thực thi cho Phase 7 của `docs/architecture/COSA_IMPLEMENTATION_ROADMAP_2026-08-22.md`. Dựa trên spike đã xác nhận trực tiếp bằng code (không suy đoán): **Memory và Knowledge lệch trình độ hoàn thiện đáng kể** — Knowledge đã có pipeline chunk→embed→retrieve chạy thật và unit-test full path; Memory mới ở mức prototype, có bug silent-data-loss cần fix ngay. Chia 4 workstream độc lập, không gộp chung.

## Bối cảnh CURRENT đã verify (không suy đoán)

**Memory** (`agentos/memory/{consolidation,models,pgvector_store,retrieval,retriever,store}.py`):
- `MemoryStore` protocol + `InMemoryMemoryStore` đã implement, có test.
- `MemoryRetriever` ranking chỉ `0.7×relevance + 0.3×importance`; `score_relevance()` tokenize bằng regex `[a-z0-9]+` — không xử lý tiếng Việt có dấu, không có recency factor dù docstring nhắc tới.
- `PgVectorMemoryStore` **tên gây hiểu nhầm**: bảng `agent_memories` không có cột `embedding`, search chỉ `WHERE workspace_id=... ORDER BY created_at DESC` — là Postgres persistence adapter thường, không phải vector/semantic memory.
- **Bug nghiêm trọng:** không truyền `db_session_factory` → `put()` return im lặng, `search()` trả `[]`, `delete()` no-op im lặng — silent data loss khi cấu hình sai.
- `agentos/memory/providers/` (target §14.1) **không tồn tại**.
- Composition root (`build_cosa_agent_plane()`, Phase 0b) chưa wire `MemoryRetriever` vào production dù hook đã có ở `ContextBuilder`.

**Knowledge** (`agentos/knowledge/`):
- Pipeline `chunk → embed → store → semantic retrieval` là implementation thật, unit-test full path (`KnowledgeIngestPipeline`, `OpenAICompatibleEmbeddingProvider` gọi thật `POST /embeddings` qua httpx, `InMemoryKnowledgeStore` cosine search).
- Chunking MVP theo character count (`DEFAULT_CHUNK_SIZE=800`, `overlap=100`) — không heading/token-aware, đủ dùng cho MVP.
- `PgVectorKnowledgeStore` có SQL semantic vector thật (`embedding <=> :query_embedding`) nhưng **chỉ test bằng fake session**, chưa có migration cho `knowledge_sources`/`knowledge_chunks`, DB ownership cố tình chưa quyết.
- Parser hoàn toàn chưa có — pipeline nhận thẳng `raw_text: str`.
- `ContextBuilder` chưa có `knowledge_snippets`/citations — Knowledge tồn tại độc lập nhưng AgentRuntime chưa consume.

## 7A — Storage ownership (làm trước tiên, chặn 7C/7D)

**Task:**
1. Chốt dùng chung 1 PostgreSQL cluster hiện có (không dựng Postgres thứ 2). Tách schema ownership: `services/*` sở hữu business schema, `agentos/memory` sở hữu schema `agent_memory`, `agentos/knowledge` sở hữu schema `knowledge`.
2. Viết migration cho `knowledge_sources`, `knowledge_chunks` (dùng đúng field đã ngụ ý trong `KnowledgeChunk`/`KnowledgeSource` model hiện có ở `agentos/knowledge/models.py` hoặc tương đương — đọc code hiện tại trước khi viết SQL, không tự bịa field mới).
3. Bổ sung cột còn thiếu cho `agent_memories` nếu cần (ví dụ metadata versioning — xem 7B).
4. Ghi rõ trong `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`: schema `agent_memory` → owner `agentos/memory`; schema `knowledge` → owner `agentos/knowledge`.

**Acceptance:**
- [ ] Migration cho `knowledge_sources`/`knowledge_chunks` tồn tại và chạy được trên Postgres thật có extension `pgvector`.
- [ ] `CREATE EXTENSION IF NOT EXISTS vector;` có trong migration (không giả định extension đã bật sẵn).
- [ ] Ownership map cập nhật đúng 2 schema mới.

## 7B — Memory provider architecture

**Task:**
1. Fix bug silent no-op trước tiên (ưu tiên cao nhất, độc lập không cần chờ 7A): nếu thiếu `db_session_factory` khi khởi tạo `PostgresMemoryStore` (đổi tên, xem bước 3), raise lỗi cấu hình ngay khi khởi động (`ConfigurationError` hoặc `UnavailableMemoryBackend`), không cho phép service chạy ở trạng thái "giả vờ hoạt động".
2. Tạo `agentos/memory/providers/` với `in_memory.py` (di chuyển `InMemoryMemoryStore` hiện có vào đây), `postgres.py`, `tencent_agent_memory.py` (stub, implement khi có nhu cầu thật — không cần code đầy đủ ở Phase 7 nếu chưa dùng).
3. Đổi tên `PgVectorMemoryStore` → `PostgresMemoryStore` (đúng bản chất hiện tại: persistence adapter, không phải vector store) — trừ khi quyết định thêm vector semantics thật ngay trong Phase 7 (xem bước 5, optional).
4. Nâng contract lên semantic hơn: `MemoryService` với `remember()/recall()/forget()/consolidate()` xây trên nền `MemoryStore` low-level hiện có (không xoá `MemoryStore`, chỉ thêm lớp trên).
5. **Optional, chỉ làm nếu có nhu cầu thật ngay:** thêm cột `embedding` vào `agent_memories`, wire `EmbeddingProvider` (đã có sẵn ở `agentos/knowledge/`, tái dùng chứ không viết lại) để `PostgresMemoryStore` có thể tìm theo semantic similarity thật — nếu không làm ngay, ghi rõ TODO trong code, không giả vờ đã có.
6. Cải thiện `score_relevance()`: tối thiểu chuẩn hoá Unicode tiếng Việt trước khi tokenize (NFC normalize + xử lý dấu) thay vì chỉ regex ASCII; thêm recency factor vào công thức ranking nếu docstring tiếp tục claim có recency (hoặc sửa docstring nếu quyết định không làm recency ở Phase 7).
7. Test `agentos/memory/providers/postgres.py` với Postgres thật (testcontainer hoặc DB test có sẵn trong CI) — không chỉ mock.

**Acceptance:**
- [ ] Thiếu `db_session_factory` → raise lỗi khi khởi động, có test xác nhận (không phải `put()` trả về im lặng).
- [ ] `agentos/memory/providers/` tồn tại đúng cấu trúc, `InMemoryMemoryStore` không còn nằm ngoài `providers/`.
- [ ] Test `test_postgres_memory_store.py` chạy với DB thật, không chỉ fake session.
- [ ] `score_relevance()` xử lý đúng câu tiếng Việt có dấu trong ít nhất 1 test case cụ thể (ví dụ "khách hàng chưa thanh toán").
- [ ] Docstring `MemoryRetriever` phản ánh đúng thực tế đã implement (không claim tính năng chưa có).

## 7C — Knowledge productionization

**Task:**
1. Viết migration thật cho `knowledge_sources`/`knowledge_chunks` (đã làm ở 7A) — bước này là chạy integration test thật với Postgres + pgvector extension, không chỉ fake session.
2. Thêm validate `len(embeddings) == len(texts)` trong `KnowledgeIngestPipeline` trước khi lưu — hiện dùng `zip()` sẽ silently truncate nếu provider trả thiếu, phải raise lỗi rõ ràng thay vì âm thầm mất dữ liệu.
3. Thêm parser tối thiểu: plain text + markdown trước (dùng thư viện parser markdown nếu cần lấy heading, hoặc parse thô nếu MVP chấp nhận). PDF/DOCX để sau, không bắt buộc trong Phase 7 — nhưng phải có interface parser rõ ràng (`Parser.parse(file) -> str`) để cắm thêm định dạng sau mà không đổi kiến trúc.
4. Bổ sung metadata vào `KnowledgeChunk`: `embedding_model`, `embedding_dimensions`, `embedding_version`, `content_hash` — cần thiết để re-index an toàn khi đổi embedding model sau này.
5. Test workspace isolation ở tầng DB thật (không chỉ ở tầng application code) — 2 workspace khác nhau, query similarity không được trả kết quả chéo.

**Acceptance:**
- [ ] Ít nhất 1 integration test `PgVectorKnowledgeStore` chạy với Postgres/pgvector thật (không fake session), bao gồm insert + query + xác nhận similarity score hợp lý.
- [ ] `KnowledgeIngestPipeline` raise lỗi rõ ràng khi `len(embeddings) != len(texts)`, có test.
- [ ] Ingest 1 file markdown thật → chunk → embed → lưu → search lại ra đúng nội dung, chạy end-to-end không cần caller tự parse trước.
- [ ] `KnowledgeChunk` có đủ metadata versioning, test xác nhận field được lưu đúng.
- [ ] Test workspace isolation ở tầng SQL (2 workspace, query không lẫn kết quả).

## 7D — Agent integration

**Task:**
1. Wire `MemoryRetriever` (đã fix ở 7B) vào `build_cosa_agent_plane()` (Phase 0b) — hiện tham số đã có trong signature nhưng production composition chưa thực sự truyền provider thật vào.
2. Mở rộng `ContextBuilder` thêm `knowledge_snippets: list[KnowledgeCitation]` — gọi `KnowledgeRetriever` (đã có ở `agentos/knowledge/`) song song với memory retrieval khi build context cho 1 turn chat.
3. `KnowledgeCitation` tối thiểu: `chunk_text, source_ref, page/section (nullable), similarity_score`.
4. Nối vào Phase 4c (Text Chat context) — khi `ContextBuilder` có `knowledge_snippets`, Agent API (Phase 4a) phát event `citation` qua SSE khi response tham chiếu tới 1 knowledge chunk cụ thể.
5. Nếu Knowledge chưa có source nào cho 1 workspace (chưa ingest gì), `knowledge_snippets` trả `[]` một cách tường minh, không lỗi.

**Acceptance:**
- [ ] `ContextBuilder.build()` trả về `knowledge_snippets` có nội dung thật khi workspace đã ingest ít nhất 1 document liên quan tới câu hỏi.
- [ ] Test: workspace chưa ingest gì → `knowledge_snippets == []`, không exception.
- [ ] Test end-to-end: gửi message qua `/agent/conversations/{id}/messages` (Phase 4a) với câu hỏi có liên quan tới 1 document đã ingest → response kèm event `citation` trỏ đúng document/chunk.
- [ ] `build_cosa_agent_plane()` không còn tham số memory/knowledge nào bị bỏ `None` một cách âm thầm trong production path.

## Dependency

7A chặn 7C (cần migration trước khi test integration thật) và 7D (cần schema tồn tại để lưu). 7B độc lập với 7A/7C, có thể làm song song — chỉ cần fix bug silent no-op ngay lập tức không chờ gì cả. 7D phụ thuộc 7B (MemoryRetriever đã fix) và 7C (Knowledge có dữ liệu thật để retrieve) và Phase 4c (ContextBuilder đã có sườn wiring từ Text Chat).
