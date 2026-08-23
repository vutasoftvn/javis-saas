from __future__ import annotations

from typing import Protocol, runtime_checkable

import httpx


@runtime_checkable
class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class EmbeddingProviderUnavailableError(RuntimeError):
    """Provider embedding được gọi mà không có API key, hoặc HTTP call thất bại."""


class OpenAICompatibleEmbeddingProvider:
    """`EmbeddingProvider` cho bất kỳ API tương thích OpenAI Embeddings nào
    (OpenAI, OpenRouter, các gateway tương thích khác) — tự chủ qua httpx,
    cùng pattern với `agentos/core/adapters/openai_compatible_provider.py`
    (không import ngược `legacy/backend`, theo ADR-012).

    Khác `/chat/completions` (dùng cho generate text), embeddings API dùng
    endpoint `/embeddings` riêng, input là list[str], output là 1 vector
    float per input theo đúng thứ tự — không phải chat message.
    """

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        model: str,
        timeout: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not self._api_key:
            raise EmbeddingProviderUnavailableError(
                f"No API key configured for embedding model '{self._model}' at {self._base_url}"
            )
        if not texts:
            return []

        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        body = {"model": self._model, "input": texts}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(f"{self._base_url}/embeddings", headers=headers, json=body)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise EmbeddingProviderUnavailableError(f"Embedding API returned {exc.response.status_code}") from exc
            except httpx.RequestError as exc:
                raise EmbeddingProviderUnavailableError(f"Embedding request failed: {exc}") from exc
            data = response.json()

        # API trả `data` là list các object {embedding, index, ...} — sort
        # lại theo index để đảm bảo thứ tự khớp với `texts` đầu vào, không
        # tin tưởng thứ tự trả về nguyên trạng.
        items = sorted(data["data"], key=lambda item: item["index"])
        return [item["embedding"] for item in items]


class StubEmbeddingProvider:
    """Test double tất định: sinh vector giả từ hash của text (không phải
    embedding thật, chỉ đủ để test pipeline chunk->embed->store->retrieve
    hoạt động đúng shape, giống StubModelProvider cho ModelProvider).
    """

    def __init__(self, *, dimensions: int = 8) -> None:
        self._dimensions = dimensions
        self.calls: list[list[str]] = []

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [self._fake_vector(text) for text in texts]

    def _fake_vector(self, text: str) -> list[float]:
        seed = sum(ord(c) for c in text) or 1
        return [((seed * (i + 1)) % 97) / 97.0 for i in range(self._dimensions)]
