# Hướng dẫn: Thêm knowledge source mới

## Khi nào cần

Khi muốn agent có thể truy xuất tri thức từ 1 nguồn mới (tài liệu nội bộ, API tra cứu, kho dữ liệu) qua `KnowledgeStore`, không phải khi chỉ cần thêm 1 fact tĩnh vào prompt (đó nên là skill instruction hoặc locale glossary).

## Các bước

1. Đọc `packages/agent/knowledge/models.py` — `KnowledgeDocument` (có `authority_class` — phân biệt nguồn chính thống vs tham khảo) và `KnowledgeChunk` (`content_hash`, `chunker_name/version`, `embedding_model/version` — cho phép biết chunk này được tạo bằng thuật toán/model nào, quan trọng khi đổi chunker/embedding model sau này).
2. Nếu nguồn có API/DB riêng → viết provider mới implement `KnowledgeStore` Protocol (`packages/agent/knowledge/store.py`) tương tự `PostgresKnowledgeStore` (`packages/agent/knowledge/providers/postgres.py`).
3. `save_document()` phải tạo `source_version` mới khi nội dung đổi (dựa vào `content_hash` so sánh) — không overwrite silent, giữ lịch sử version.
4. **Lưu ý hiện trạng**: `PostgresKnowledgeStore.search_chunks()` hiện dùng `ILIKE` (text match), CHƯA phải semantic search — nếu nguồn mới cần vector search thật, cần bổ sung embedding pipeline + vector column, đây là việc CHƯA làm trong phiên Wave 0-11.
5. Viết `docs/features/knowledge.md` cập nhật nếu thêm provider mới đáng chú ý.

## Không được làm

- Không để agent tự quyết định "nguồn này đáng tin" qua prompt — `authority_class` là field structured, set khi đăng ký document, không suy diễn từ nội dung.
