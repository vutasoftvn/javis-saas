from __future__ import annotations

import re

from pydantic import BaseModel, Field

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class MemoryQuery(BaseModel):
    workspace_id: str
    agent_key: str
    text: str
    limit: int = Field(default=20, gt=0)


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_PATTERN.findall(text.lower()))


def score_relevance(query_text: str, content: str) -> float:
    """Naive term-overlap relevance score in [0, 1]. A placeholder for real
    embedding-based semantic retrieval (blueprint §3.6) — good enough to
    prove the retrieval pipeline shape without adding a vector DB dependency
    in this phase.
    """
    query_tokens = _tokenize(query_text)
    content_tokens = _tokenize(content)
    if not query_tokens or not content_tokens:
        return 0.0
    overlap = query_tokens & content_tokens
    return len(overlap) / len(query_tokens)
