import asyncio
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_api_does_not_start_background_channel_worker():
    source = Path(__file__).parents[1].joinpath("main.py").read_text()
    assert "asyncio.create_task(channel_worker_loop())" not in source


def test_api_does_not_apply_schema_changes_at_startup():
    source = Path(__file__).parents[1].joinpath("main.py").read_text()
    assert "Base.metadata.create_all" not in source
    assert "ALTER TABLE" not in source


def test_lifespan_starts_and_stops_runtime_dependencies(monkeypatch):
    source = Path(__file__).parents[1].joinpath("main.py").read_text()
    assert "@app.on_event" not in source

    ensure_bucket = Mock()
    listener_start = AsyncMock()
    listener_stop = AsyncMock()
    monkeypatch.setattr("app.main.ensure_bucket_exists", ensure_bucket)
    monkeypatch.setattr("app.main.cross_process_event_listener.start", listener_start)
    monkeypatch.setattr("app.main.cross_process_event_listener.stop", listener_stop)

    async def exercise_lifespan():
        async with app.router.lifespan_context(app):
            ensure_bucket.assert_called_once_with()
            listener_start.assert_awaited_once_with()
        listener_stop.assert_awaited_once_with()

    asyncio.run(exercise_lifespan())


def test_live_returns_ok():
    response = client.get("/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_ready_returns_ok_when_db_and_storage_healthy(monkeypatch):
    @contextmanager
    def fake_connect():
        class _Conn:
            def execute(self, *args, **kwargs):
                return None

        yield _Conn()

    class _FakeEngine:
        def connect(self):
            return fake_connect()

    class _FakeS3Client:
        def list_buckets(self):
            return {"Buckets": []}

    monkeypatch.setattr("app.main.engine", _FakeEngine())
    monkeypatch.setattr("app.main.get_s3_client", lambda: _FakeS3Client())

    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"] == {"database": "ok", "storage": "ok"}


def test_ready_returns_503_when_database_unreachable(monkeypatch):
    class _FailingEngine:
        def connect(self):
            raise ConnectionError("db unreachable")

    class _FakeS3Client:
        def list_buckets(self):
            return {"Buckets": []}

    monkeypatch.setattr("app.main.engine", _FailingEngine())
    monkeypatch.setattr("app.main.get_s3_client", lambda: _FakeS3Client())

    response = client.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["database"].startswith("error:")
    assert body["checks"]["storage"] == "ok"
