import pytest

from app.modules.integrations.connector_health import check_connector_health


@pytest.mark.asyncio
async def test_connector_health_returns_false_without_a_supported_endpoint():
    assert await check_connector_health({"name": "local"}) is False


@pytest.mark.asyncio
async def test_connector_health_reports_success_for_a_2xx_endpoint(monkeypatch):
    class Response:
        status_code = 204

    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def get(self, url): return Response()

    monkeypatch.setattr("app.modules.integrations.connector_health.httpx.AsyncClient", lambda **_: Client())
    assert await check_connector_health({"name": "api", "health_url": "https://example.test/health"}) is True
