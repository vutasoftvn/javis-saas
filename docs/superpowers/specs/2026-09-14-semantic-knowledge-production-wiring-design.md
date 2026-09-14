# Semantic Knowledge Production Wiring — Design

Status: DRAFT (chờ user review)
Ngày: 2026-09-14
Phạm vi: sub-project #3/6 trong đợt audit "Ba blocker lớn nhất" (2026-09-14) — P1.
Các sub-project khác có spec riêng:
[#1 Schedule Project scope](2026-09-14-schedule-project-scope-design.md),
[#2 Python quality gates](2026-09-14-python-quality-gates-design.md).

## Vấn đề

Audit ban đầu nêu: "semantic search chỉ chạy nếu caller tự cấp query
embedding; chưa có embedding model production. Vault route cũng đang trả
501 cho phần chưa phát hành." Đề xuất: công khai trạng thái lexical-only,
sau đó thêm embedding provider production + version/dimension fingerprint +
reindex + purge/revoke + E2E tenant-isolation trước khi quảng bá semantic
retrieval.

**Xác nhận lại trong code (2026-09-14) — bức tranh chi tiết hơn audit ban
đầu:**

- `agent.knowledge.retrieval.retrieve()` (`packages/agent/knowledge/
  retrieval.py:38`) hiện **không có bất kỳ caller nào** trong toàn bộ
  `packages/agent`/`apps/cosa` — dead code, chưa từng wire vào route/worker
  nào. Không có UI Flutter nào quảng cáo "semantic search"/"AI-powered
  search" (grep xác nhận). `vault_routes.py` `/retrieval/query` trả 501
  một cách trung thực (`_not_released()`, dòng 61-64), cùng
  `/knowledge/graph` và `/knowledge/sources`. Document CRUD/upload đã hoạt
  động thật (không stub). **Kết luận: hiện không có vi phạm "trung thực"
  nào đang xảy ra** — khuyến nghị của audit mang tính phòng ngừa cho tương
  lai, không phải sửa 1 bug đang hiện diện.
- Hạ tầng lưu trữ semantic **đã xây gần xong**:
  - `packages/agent/knowledge/store.py` — `KnowledgeStore` Protocol chỉ khai
    báo `search_chunks`; `search_chunks_semantic` là duck-typed extension
    (kiểm tra bằng `hasattr`).
  - `packages/agent/knowledge/providers/postgres.py:491-528` —
    `PostgresKnowledgeStore.search_chunks_semantic` **đã implement thật**
    (pgvector cosine query `1 - (c.embedding <=> CAST(:qvec AS vector))`,
    set `cosa.workspace_id` cho RLS, filter `embedding IS NOT NULL`).
  - Migration `packages/agent/migrations/002_restore_knowledge_
    artifact_automation.sql`: `CREATE EXTENSION IF NOT EXISTS vector`
    (dòng 20); `knowledge_chunks.embedding public.vector` +
    `embedding_model`/`embedding_dimensions`/`embedding_version` (dòng
    106-115); bảng versioned riêng `knowledge.chunk_embeddings` (dòng
    128-138, khóa theo `chunk_id, embedding_model, embedding_version`, RLS
    dòng 172-174).
  - `PostgresKnowledgeStore.delete_by_vault_document` (dòng 335-363) đã
    xóa đúng thứ tự FK `chunk_embeddings → knowledge_chunks →
    source_versions` — cascade đã có, không cần xây mới ở tầng store.
- **Lỗ hổng thật duy nhất:** không có bước nào trong ingestion pipeline
  (`apps/cosa/knowledge_ingestion/normalization.py:293-327`) tính embedding
  — mọi `KnowledgeChunk` sinh ra đều có `embedding=None`. Write path ghi
  `chunk_embeddings` đã có (`postgres.py:187`, điều kiện `if chunk.embedding
  and chunk.embedding_model and chunk.embedding_version`) nhưng chưa bao
  giờ được cấp dữ liệu thật.
- `packages/agent/knowledge/embedding.py:24-83` — `EmbeddingProvider`
  Protocol đã có, với 2 implementation: `HashingEmbeddingProvider` (giả,
  không semantic thật) và `SentenceTransformerEmbeddingProvider` (model
  local/offline, đã viết đầy đủ, lazy-import).
- DeepSeek (LLM chính qua LiteLLM, `apps/cosa/composition/
  model_provider.py:20-55`) **không có endpoint embedding** — cần provider
  riêng cho embedding.
- Worker đã có cơ chế scheduled-task dispatch tổng quát
  (`apps/cosa/worker/main.py`, `dispatch_one_task` dòng 387, các
  `task_type` hiện có: `knowledge_ingestion`, `vault_purge`,
  `approval_action`, `skill_improvement`) — 1 `task_type` mới cho reindex
  có thể tái dùng cơ chế này, không cần xây job system riêng.

## Quyết định đã chốt

1. **Embedding provider production:** `SentenceTransformerEmbeddingProvider`
   (local, đã có sẵn code) — không cần secret/API key mới, khớp
   `ADR-LOCAL-FIRST-001` đang là kiến trúc chính, tránh phụ thuộc mạng
   ngoài cho một năng lực lõi.
2. **Route `/retrieval/query`:** vẫn giữ 501 cho tới khi có bằng chứng
   (bước 1 + 2 dưới đây chạy được + E2E tenant-isolation xanh) — chỉ khi đó
   mới bỏ `_not_released()` và gọi `retrieve()` thật. Thứ tự này bắt buộc,
   không đảo ngược, đúng tinh thần audit "không quảng bá trước khi có
   proof".
3. **Reindex khi đổi `embedding_model`/`embedding_version`:** tự động —
   worker phát hiện mismatch và tự enqueue, không cần admin bấm tay.

## Kiến trúc

```
1. Ingestion pipeline: normalization.py tạo KnowledgeChunk
   -> THÊM bước gọi SentenceTransformerEmbeddingProvider.embed_texts()
      ngay sau chunk hóa, set chunk.embedding/embedding_model/
      embedding_version/embedding_dimensions
   -> PostgresKnowledgeStore.save_document ghi cả knowledge_chunks.embedding
      lẫn chunk_embeddings (write path đã có, chỉ cần dữ liệu thật)

2. Reindex: worker/main.py thêm task_type "knowledge_reindex"
   (tái dùng cơ chế scheduled-task dispatch đã có)
   -> quét chunk có embedding_model/embedding_version lệch config hiện tại
   -> enqueue re-embed cho từng chunk lệch, KHÔNG đổi content_hash
   -> idempotent: chunk đã đúng version không bị đụng tới ở lần quét sau

3. Retrieval route: vault_routes.py POST /retrieval/query
   -> bỏ _not_released(), gọi agent.knowledge.retrieval.retrieve() thật
      với embedder=SentenceTransformerEmbeddingProvider instance
   -> CHỈ bật sau khi bước 1+2 chạy được và E2E tenant-isolation xanh
```

## Data model / Config

**Version/dimension fingerprint** (cột DB đã tồn tại từ migration 002, chỉ
cần chính sách sử dụng, không cần migration mới):

- Khi ingest, ghi đúng `embedding_model` (tên model sentence-transformers
  cụ thể, không "latest" trôi nổi — đúng nguyên tắc "không floating latest"
  CLAUDE.md), `embedding_version` (string cố định), `embedding_dimensions`.
- Cấu hình đọc từ env var mới theo đúng convention `DEEPSEEK_*`
  (`model_provider.py`): `EMBEDDING_MODEL_NAME` (mặc định trỏ 1 model cụ
  thể), `EMBEDDING_MODEL_VERSION` (đổi thủ công khi nâng cấp model, chính
  giá trị này kích hoạt reindex tự động ở bước 2).
- `PostgresKnowledgeStore.save_document` reject nếu `embedding` có giá trị
  nhưng thiếu 1 trong 3 field metadata đi kèm (nhất quán với cách nó đã
  reject thiếu vault provenance).
- **Dimension mismatch là lỗi cứng, không silent-cast:** `search_chunks_
  semantic` thêm điều kiện `WHERE embedding_dimensions = :current_dim` —
  loại chunk lệch dimension khỏi kết quả thay vì để pgvector query lỗi
  runtime khi so sánh 2 vector khác chiều.

## Purge / Revoke

- `delete_by_vault_document` đã cascade đúng thứ tự FK — không cần code
  mới ở tầng store.
- **Cần xác minh (gap tiềm ẩn, xử lý trong plan):** `POST /documents/{id}/
  revoke` và `.../purge` (`vault_routes.py:428,455`) có thực sự gọi
  `delete_by_vault_document` (hay tương đương), hay chỉ đổi `state` (soft)
  mà không xóa vector thật. Nếu là soft-only, đây là gap cần vá trong
  sub-project này — dữ liệu nhạy cảm không được tồn tại "ẩn" trong index
  sau khi đã revoke.
- **Legal-hold phải chặn cascade delete:** xác minh
  `delete_by_vault_document` tự kiểm tra legal-hold trước khi xóa, hoặc
  route phải tự chặn trước khi gọi — nếu chưa có, thêm guard fail-closed
  (từ chối purge khi legal-hold active).

## Testing

**Unit/integration** (`make agent-test`, `make apps-cosa-test`):

1. `SentenceTransformerEmbeddingProvider.embed_texts()`: vector đúng
   dimension khai báo, deterministic cho cùng input (cần cho reproducibility
   của reindex).
2. Ingestion (`normalization.py`): chunk hóa 1 document mẫu → mọi
   `KnowledgeChunk` sinh ra có đủ `embedding`/`embedding_model`/
   `embedding_version`/`embedding_dimensions` khớp config hiện tại.
3. `save_document`: reject khi `embedding` có giá trị nhưng thiếu
   `embedding_model`/`embedding_version`.
4. `search_chunks_semantic`: seed 1 chunk dimension lệch → không xuất hiện
   trong kết quả, không lỗi runtime.
5. Reindex task: phát hiện đúng chunk lệch `embedding_version`, enqueue
   re-embed, sau khi chạy `embedding_version` khớp config; không đụng chunk
   đã đúng (idempotent).
6. Revoke/Purge: gọi route → query trực tiếp DB xác nhận `chunk_embeddings`
   và `knowledge_chunks` liên quan đã bị xóa thật (không chỉ assert response
   200 — CLAUDE.md quy tắc 6 "test qua process thật"). Test riêng: legal-hold
   active → revoke/purge bị từ chối, dữ liệu còn nguyên.

**E2E tenant-isolation** (bắt buộc trước khi bật route, chạy trong
`make e2e-cross-plane-smoke`):

- 2 workspace A, B, mỗi workspace ingest tài liệu nội dung đặc trưng riêng.
- Query semantic từ A hỏi về nội dung B → kết quả rỗng hoặc chỉ chứa citation
  của A, không rò rỉ citation B.
- Query lexical fallback (giả lập `search_chunks_semantic` lỗi) cũng phải
  giữ tenant-isolation — fallback path không được bỏ qua filter workspace.

**Gate bật route:** chỉ chuyển `/retrieval/query` từ `_not_released()` sang
`retrieve()` thật sau khi cả 2 nhóm test trên xanh — điều kiện gate, không
phải bước song song.

## Ngoài phạm vi (out of scope)

- `/knowledge/graph`, `/knowledge/sources` (vẫn 501) — không thuộc phạm vi
  semantic retrieval, để lại quyết định sản phẩm riêng.
- Đổi provider LLM chính (DeepSeek) hoặc thêm provider chat mới — spec này
  chỉ thêm 1 embedding provider độc lập, không đụng luồng chat.
- UI Founder Hub hiển thị trạng thái "semantic sẵn sàng" — thuộc quyết định
  sản phẩm/frontend riêng, không nằm trong spec backend này.
