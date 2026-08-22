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

## Knowledge Layer (§66) — implement 2026-08-22, chọn pgvector (user quyết)

Ban đầu chưa implement (xác nhận qua `AI_AGENT_OS_AUDIT_NOTES.md` §0.3). Sau khi user chọn **pgvector** làm vector DB, đã build đủ pipeline ingest→embed→index→retrieve trong `agentos/knowledge/`:

| Thành phần | File |
|---|---|
| Models (`KnowledgeSource`, `KnowledgeChunk`, `KnowledgeSearchResult`) | `agentos/knowledge/models.py` |
| Chunk (theo ký tự, có overlap) | `agentos/knowledge/chunking.py` |
| Embedding provider (thật, OpenAI-compatible `/embeddings` API qua httpx) | `agentos/core/embedding_provider.py` (`OpenAICompatibleEmbeddingProvider`) |
| Store: `InMemoryKnowledgeStore` (cosine similarity thật bằng Python, không term-overlap giả) + `PgVectorKnowledgeStore` (SQL dùng `<=>` cosine-distance operator của pgvector) | `agentos/knowledge/store.py` |
| Ingest pipeline (chunk → embed → index) | `agentos/knowledge/ingest.py` (`KnowledgeIngestPipeline`) |
| Retrieval (embed query → search) | `agentos/knowledge/retrieval.py` (`KnowledgeRetriever`) |

Ranh giới cố tình: **parse** (trích text từ PDF/HTML/docx) KHÔNG thuộc phạm vi — pipeline nhận `raw_text` đã trích sẵn, giống cách `EpisodeConsolidator` nhận `raw_episode_text` thay vì tự parse trace.

**Migration cho `knowledge_sources`/`knowledge_chunks` (cần extension `pgvector` + cột `embedding vector(N)`) CỐ TÌNH CHƯA VIẾT** — cùng lý do và cùng tiền lệ đã được chấp nhận với `PgVectorMemoryStore`/`agent_memories` (ADR-012: "a real scope decision, not a quick fix" về việc `agentos/` sống chung DB với `services/` hay riêng). `PgVectorKnowledgeStore` được test bằng fake session (`tests/agentos/knowledge/test_pgvector_store.py`) để xác nhận đúng SQL/params, không phải test tích hợp thật.

29 test mới (`tests/agentos/knowledge/`, `tests/agentos/core/test_embedding_provider.py`).

## Còn thiếu

- Migration Postgres cho `knowledge_sources`/`knowledge_chunks` (+ extension `pgvector`) — quyết định "agentos/ dùng DB nào" cần chốt trước (cùng vấn đề treo với `agent_memories`).
- `PgVectorMemoryStore` (Memory, khác Knowledge) vẫn cần migration riêng cho `agent_memories` — chưa đổi.
- Parse (PDF/HTML/docx → text) — ngoài phạm vi, caller tự làm trước khi gọi `ingest()`.
- Chưa có tool/skill nào thật sự gọi `KnowledgeRetriever` trong 1 Agent run — pipeline đã hoạt động độc lập, chưa wire vào `Executor`/`ContextBuilder`.

Chi tiết đầy đủ: `docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md` Phần A3.
