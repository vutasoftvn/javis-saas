from __future__ import annotations

from pydantic import BaseModel


class RetrievalEvalResult(BaseModel):
    query: str
    retrieved_chunk_ids: list[str]
    expected_chunk_ids: list[str]
    precision: float
    recall: float
    f1: float


def evaluate_retrieval(
    query: str,
    retrieved_chunk_ids: list[str],
    *,
    expected_chunk_ids: list[str],
) -> RetrievalEvalResult:
    """Retrieval Eval (§20.4): measures precision, recall, and F1 score for Knowledge retrieval."""
    retrieved_set = set(retrieved_chunk_ids)
    expected_set = set(expected_chunk_ids)

    if not expected_set:
        return RetrievalEvalResult(
            query=query,
            retrieved_chunk_ids=retrieved_chunk_ids,
            expected_chunk_ids=expected_chunk_ids,
            precision=1.0 if not retrieved_set else 0.0,
            recall=1.0,
            f1=1.0 if not retrieved_set else 0.0,
        )

    hits = len(retrieved_set & expected_set)
    precision = hits / len(retrieved_set) if retrieved_set else 0.0
    recall = hits / len(expected_set) if expected_set else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return RetrievalEvalResult(
        query=query,
        retrieved_chunk_ids=retrieved_chunk_ids,
        expected_chunk_ids=expected_chunk_ids,
        precision=precision,
        recall=recall,
        f1=f1,
    )
