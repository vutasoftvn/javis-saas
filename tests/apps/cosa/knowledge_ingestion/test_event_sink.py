"""Closeout Task 3: CompanyOutboxEventSink POSTs the envelope to the
services/company internal endpoint; publish_knowledge_source uses it by
default."""
import httpx
import pytest

from agent.knowledge.snapshot import KnowledgeSnapshot
from apps.cosa.knowledge_ingestion.event_sink import CompanyOutboxEventSink
from apps.cosa.knowledge_ingestion.publish import publish_knowledge_source

pytestmark = pytest.mark.asyncio


def _snapshot():
    return KnowledgeSnapshot(
        id="src_1", workspace_id="ws_1", embedding_model="none", embedding_version="0"
    ).with_hash()


async def test_sink_posts_envelope_with_service_token():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["token"] = request.headers.get("X-Service-Token")
        seen["body"] = request.read().decode()
        return httpx.Response(202, json={"stored": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    sink = CompanyOutboxEventSink(base_url="http://company.test", service_token="tok", client=client)
    await sink({"eventType": "knowledge.source.published.v1", "payload": {"sourceId": "src_1"}})
    await client.aclose()

    assert seen["url"].endswith("/events/internal/knowledge-published")
    assert seen["token"] == "tok"
    assert "knowledge.source.published.v1" in seen["body"]
    assert seen["body"].startswith('{"envelope":')


async def test_publish_knowledge_source_default_sink_hits_company(monkeypatch):
    calls = []

    class _StubClient:
        async def post(self, url, json, headers):
            calls.append((url, headers.get("X-Service-Token")))
            return httpx.Response(202, json={"stored": True}, request=httpx.Request("POST", url))

        async def aclose(self):
            pass

    monkeypatch.setenv("COMPANY_SERVICE_URL", "http://company.test")
    monkeypatch.setenv("COSA_WORKER_SERVICE_TOKEN", "tok")
    monkeypatch.setattr(
        "apps.cosa.knowledge_ingestion.event_sink.httpx.AsyncClient",
        lambda *a, **k: _StubClient(),
    )

    await publish_knowledge_source(
        snapshot=_snapshot(), approved=True, persisted=True,
        reviewed_by="u_1", reviewed_at="t", correlation_id="c",
    )
    assert calls and calls[0][0].endswith("/events/internal/knowledge-published")
    assert calls[0][1] == "tok"
