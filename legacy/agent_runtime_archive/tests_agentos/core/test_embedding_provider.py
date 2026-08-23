from __future__ import annotations

import httpx
import pytest

from agentos.core.embedding_provider import (
    EmbeddingProviderUnavailableError,
    OpenAICompatibleEmbeddingProvider,
    StubEmbeddingProvider,
)

_RealAsyncClient = httpx.AsyncClient


def _mock_client(handler):
    return lambda *a, **kw: _RealAsyncClient(*a, transport=httpx.MockTransport(handler), **kw)


@pytest.mark.asyncio
async def test_embed_raises_when_api_key_missing():
    provider = OpenAICompatibleEmbeddingProvider(api_key=None, base_url="https://example.test/v1", model="m")

    with pytest.raises(EmbeddingProviderUnavailableError, match="m"):
        await provider.embed(["hello"])


@pytest.mark.asyncio
async def test_embed_returns_empty_list_for_empty_input():
    provider = OpenAICompatibleEmbeddingProvider(api_key="k", base_url="https://example.test/v1", model="m")

    result = await provider.embed([])

    assert result == []


@pytest.mark.asyncio
async def test_embed_calls_the_embeddings_endpoint_and_returns_vectors_in_order(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/embeddings"
        assert request.headers["authorization"] == "Bearer test-key"
        import json

        body = json.loads(request.content)
        assert body == {"model": "m", "input": ["a", "b"]}
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0.4, 0.5]},
                    {"index": 0, "embedding": [0.1, 0.2]},
                ]
            },
        )

    monkeypatch.setattr(httpx, "AsyncClient", _mock_client(handler))
    provider = OpenAICompatibleEmbeddingProvider(api_key="test-key", base_url="https://example.test/v1", model="m")

    vectors = await provider.embed(["a", "b"])

    # sắp lại theo index dù response trả không đúng thứ tự
    assert vectors == [[0.1, 0.2], [0.4, 0.5]]


@pytest.mark.asyncio
async def test_embed_raises_on_http_error(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    monkeypatch.setattr(httpx, "AsyncClient", _mock_client(handler))
    provider = OpenAICompatibleEmbeddingProvider(api_key="test-key", base_url="https://example.test/v1", model="m")

    with pytest.raises(EmbeddingProviderUnavailableError, match="500"):
        await provider.embed(["a"])


@pytest.mark.asyncio
async def test_stub_embedding_provider_is_deterministic_and_records_calls():
    provider = StubEmbeddingProvider(dimensions=4)

    first = await provider.embed(["hello world"])
    second = await provider.embed(["hello world"])

    assert first == second
    assert len(first[0]) == 4
    assert provider.calls == [["hello world"], ["hello world"]]


@pytest.mark.asyncio
async def test_stub_embedding_provider_gives_different_vectors_for_different_text():
    provider = StubEmbeddingProvider(dimensions=4)

    a, b = await provider.embed(["alpha", "beta"])

    assert a != b
