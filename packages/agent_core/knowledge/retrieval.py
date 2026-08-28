"""Retrieval có gate eval (P1 Task 6).

Semantic retrieval CHỈ chạy khi: config.mode == "semantic", eval score đạt
`min_eval_score`, có query embedding, và store hỗ trợ `search_chunks_semantic`.
Ngược lại luôn fallback về lexical (`search_chunks`). Kết quả luôn kèm
`CitationProvenance` — store đã lọc theo `workspace_id` nên citations không
bao giờ rò rỉ sang workspace khác.

Ranking semantic hiện dựa cosine similarity trên vector `KnowledgeChunk.embedding`
do caller cung cấp. Chưa có embedding model production nào được wire — cho tới
khi có, đường semantic chỉ hoạt động khi caller tự truyền `query_embedding`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Sequence

from agent_core.knowledge.models import CitationProvenance

__all__ = ["KnowledgeRetrievalConfig", "RetrievalResult", "retrieve"]


@dataclass(frozen=True)
class KnowledgeRetrievalConfig:
    mode: Literal["lexical", "semantic"] = "lexical"
    min_eval_score: float = 0.7


@dataclass
class RetrievalResult:
    citations: list[CitationProvenance]
    mode_used: Literal["lexical", "semantic"]
    fell_back: bool


async def retrieve(
    store,
    config: KnowledgeRetrievalConfig,
    *,
    workspace_id: str,
    query: str,
    limit: int = 5,
    eval_score: Optional[float] = None,
    query_embedding: Optional[Sequence[float]] = None,
) -> RetrievalResult:
    want_semantic = (
        config.mode == "semantic"
        and eval_score is not None
        and eval_score >= config.min_eval_score
        and query_embedding is not None
        and hasattr(store, "search_chunks_semantic")
    )
    if want_semantic:
        try:
            citations = await store.search_chunks_semantic(
                workspace_id=workspace_id,
                query_embedding=list(query_embedding),
                limit=limit,
            )
            return RetrievalResult(citations=list(citations), mode_used="semantic", fell_back=False)
        except NotImplementedError:
            pass  # store chưa có semantic thật → fallback

    citations = await store.search_chunks(workspace_id=workspace_id, query=query, limit=limit)
    return RetrievalResult(
        citations=list(citations),
        mode_used="lexical",
        fell_back=config.mode == "semantic",
    )
