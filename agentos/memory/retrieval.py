from __future__ import annotations

import re
import unicodedata

from pydantic import BaseModel, Field

# Unicode word pattern matching alphanumeric and international characters (including Vietnamese diacritics)
_TOKEN_PATTERN = re.compile(r"[\w]+", re.UNICODE)


class MemoryQuery(BaseModel):
    workspace_id: str
    agent_key: str
    text: str
    limit: int = Field(default=20, gt=0)


def _normalize(text: str) -> str:
    """Normalize Unicode text to standard NFC form and convert to lowercase."""
    return unicodedata.normalize("NFC", text).lower()


def _tokenize(text: str) -> set[str]:
    """Extract word tokens from normalized Unicode text."""
    normalized = _normalize(text)
    return set(_TOKEN_PATTERN.findall(normalized))


def score_relevance(query_text: str, content: str) -> float:
    """Term-overlap relevance score in [0, 1] supporting Unicode & Vietnamese accented words.
    Computes Jaccard/overlap ratio of query tokens present in content tokens.
    """
    query_tokens = _tokenize(query_text)
    content_tokens = _tokenize(content)
    if not query_tokens or not content_tokens:
        return 0.0
    overlap = query_tokens & content_tokens
    return len(overlap) / len(query_tokens)
