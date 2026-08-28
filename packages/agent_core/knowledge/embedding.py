"""EmbeddingProvider — nguồn vector cho semantic retrieval (P1 Task 6b).

`HashingEmbeddingProvider` là deterministic, không phụ thuộc, dùng cho
dev/test và ingest pipeline chưa có model thật — **không mang ngữ nghĩa**,
chỉ để đường ống chạy end-to-end. Production swap `SentenceTransformer...`
(offline, local-first residency — embedding không rời node) hoặc một provider
API khác.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from typing import Protocol

__all__ = [
    "EmbeddingProvider",
    "HashingEmbeddingProvider",
    "SentenceTransformerEmbeddingProvider",
]


class EmbeddingProvider(Protocol):
    model_name: str
    model_version: str
    dimensions: int

    def embed_query(self, text: str) -> list[float]: ...
    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]: ...


class HashingEmbeddingProvider:
    """Deterministic hashing → vector đơn vị. KHÔNG semantic — placeholder."""

    model_name = "hashing-dev"
    model_version = "1"

    def __init__(self, dimensions: int = 64) -> None:
        self.dimensions = dimensions

    def _vec(self, text: str) -> list[float]:
        acc = [0.0] * self.dimensions
        for tok in text.lower().split():
            h = hashlib.sha256(tok.encode("utf-8")).digest()
            for i in range(self.dimensions):
                acc[i] += (h[i % len(h)] - 128) / 128.0
        norm = math.sqrt(sum(x * x for x in acc)) or 1.0
        return [x / norm for x in acc]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]


class SentenceTransformerEmbeddingProvider:
    """Local offline embeddings (sentence-transformers). Lazy import — chỉ cài
    `sentence-transformers` khi thực sự chọn provider này."""

    model_version = "1"

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "SentenceTransformerEmbeddingProvider requires `sentence-transformers`. "
                "Install it or use HashingEmbeddingProvider / an API provider."
            ) from e
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)
        self.dimensions = int(self._model.get_sentence_embedding_dimension())

    def embed_query(self, text: str) -> list[float]:
        return [float(x) for x in self._model.encode(text, normalize_embeddings=True)]

    def embed_texts(self, texts):
        return [
            [float(x) for x in v]
            for v in self._model.encode(list(texts), normalize_embeddings=True)
        ]
