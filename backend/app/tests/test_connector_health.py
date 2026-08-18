import pytest

from app.integrations.channels.connector_health import check_connector_health


@pytest.mark.asyncio
async def test_connector_health_returns_false_without_a_supported_endpoint():
    assert await check_connector_health({"name": "local"}) is False


@pytest.mark.asyncio
async def test_connector_health_rejects_private_or_local_endpoints(monkeypatch):
    monkeypatch.setattr(
        "app.integrations.channels.connector_health.socket.getaddrinfo",
        lambda *_, **__: [(None, None, None, None, ("127.0.0.1", 443))],
    )
    assert await check_connector_health({"health_url": "https://127.0.0.1/health"}) is False
    assert await check_connector_health({"health_url": "https://localhost/health"}) is False
    assert await check_connector_health({"health_url": "https://192.168.1.20/health"}) is False


@pytest.mark.asyncio
async def test_connector_health_reports_success_for_a_2xx_endpoint(monkeypatch):
    class Response:
        status_code = 204

    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def get(self, url): return Response()

    monkeypatch.setattr(
        "app.integrations.channels.connector_health.socket.getaddrinfo",
        lambda *_, **__: [(None, None, None, None, ("93.184.216.34", 443))],
    )
    monkeypatch.setattr("app.integrations.channels.connector_health.httpx.AsyncClient", lambda **_: Client())
    assert await check_connector_health({"name": "api", "health_url": "https://example.test/health"}) is True
