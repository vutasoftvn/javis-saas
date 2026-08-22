# 02 — Memory & Knowledge Spec

**Blueprint gốc:** §11–§15, §66–§67 của `markdown/AI_Agent_OS_Master_Architecture.md`.
**Áp dụng cho:** `agentos/` (target theo ADR-013). `legacy/agent_runtime` chỉ có `memory/models.py` tối giản, không có retrieval/consolidation pipeline — Memory là layer `agentos/` vượt trội rõ rệt so với production.

## Trạng thái hiện tại

| Thành phần blueprint | File | Ghi chú |
|---|---|---|
| MemoryStore protocol + InMemory/PgVector | `agentos/memory/store.py`, `pgvector_store.py` | Đúng §12 |
| MemoryItem (5 kind: WORKING/EPISODIC/SEMANTIC/PROCEDURAL/ORGANIZATIONAL) | `agentos/memory/models.py` | Đúng §11.1 |
| Retrieval | `agentos/memory/retrieval.py`, `retriever.py` | Naive term-overlap (`score_relevance`) — không phải semantic embedding thật, ghi rõ trong docstring |
| Episodic consolidation | `agentos/memory/consolidation.py` (`EpisodeConsolidator`) | raw run → summary → EPISODIC MemoryItem |
| Procedural consolidation | `agentos/memory/consolidation.py` (`ProceduralConsolidator`) | Mới thêm (Giai đoạn 3.6): episodic lặp lại theo `pattern_tag` tường minh (không có semantic clustering thật) → 1 MemoryItem kind=PROCEDURAL khi đủ ngưỡng `min_occurrences`, không tạo trùng lặp khi gọi lại |

## Knowledge Layer (§66)

**Chưa implement** — xác nhận dứt khoát qua audit (`docs/architecture/AI_AGENT_OS_AUDIT_NOTES.md` §0.3): không có ingest/parse/chunk/embed/index pipeline, không có bảng `knowledge_sources` trong bất kỳ migration nào. `agentos/memory/retrieval.py` chỉ làm term-overlap, không gọi embedding, không có vector DB thật đứng sau (dù `PgVectorMemoryStore` tồn tại, bảng `agent_memories` nó cần chưa có migration nào theo ADR-012).

## Còn thiếu

- Knowledge Layer toàn bộ (§66) — chưa bắt đầu.
- `PgVectorMemoryStore` cần 1 migration cho bảng `agent_memories` trước khi dùng được thật (ADR-012 "Follow-up" note).
- Semantic retrieval thật (embedding-based) thay cho term-overlap — cần quyết định vector DB trước (pgvector/Qdrant/khác).

Chi tiết đầy đủ: `docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md` Phần A3.
