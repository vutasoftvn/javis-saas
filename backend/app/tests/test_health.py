import asyncio
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.bootstrap.create_app import FULL_ROLE, create_app
from app.main import app

client = TestClient(app)


def test_api_does_not_start_background_channel_worker():
    source = Path(__file__).parents[1].joinpath("bootstrap/create_app.py").read_text()
    assert "asyncio.create_task(channel_worker_loop())" not in source


def test_api_does_not_apply_schema_changes_at_startup():
    source = Path(__file__).parents[1].joinpath("bootstrap/create_app.py").read_text()
    assert "Base.metadata.create_all" not in source
    assert "ALTER TABLE" not in source


def test_lifespan_starts_and_stops_runtime_dependencies(monkeypatch):
    source = Path(__file__).parents[1].joinpath("bootstrap/create_app.py").read_text()
    assert "@app.on_event" not in source

    ensure_bucket = Mock()
    monkeypatch.setattr("app.integrations.storage.s3_client.ensure_bucket_exists", ensure_bucket)

    async def exercise_lifespan():
        test_app = create_app(FULL_ROLE)
        async with test_app.router.lifespan_context(test_app):
            ensure_bucket.assert_called_once_with()

    asyncio.run(exercise_lifespan())


def test_live_returns_ok():
    response = client.get("/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_api_accepts_preflight_from_development_web_origin():
    response = client.options(
        "/api/v1/auth/sessions",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


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

    monkeypatch.setattr("app.db.session.engine", _FakeEngine())
    monkeypatch.setattr("app.integrations.storage.s3_client.get_s3_client", lambda: _FakeS3Client())
    monkeypatch.setattr("app.core.migration_health.get_migration_health", lambda _engine: (True, "ok"))
    monkeypatch.setattr("app.core.worker_health.get_worker_health", lambda _engine: (True, "ok"))

    test_app = create_app(FULL_ROLE)
    test_client = TestClient(test_app)

    response = test_client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"] == {
        "database": "ok",
        "storage": "ok",
        "migrations": "ok",
        "worker": "ok",
    }


def test_ready_returns_503_when_schema_is_not_at_head(monkeypatch):
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

    monkeypatch.setattr("app.db.session.engine", _FakeEngine())
    monkeypatch.setattr("app.integrations.storage.s3_client.get_s3_client", lambda: _FakeS3Client())
    monkeypatch.setattr("app.core.migration_health.get_migration_health", lambda _engine: (False, "behind"))
    monkeypatch.setattr("app.core.worker_health.get_worker_health", lambda _engine: (True, "ok"))

    test_app = create_app(FULL_ROLE)
    test_client = TestClient(test_app)

    response = test_client.get("/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["migrations"] == "behind"


def test_ready_returns_503_when_worker_has_not_reported_a_heartbeat(monkeypatch):
    @contextmanager
    def fake_connect():
        class _Conn:
            def execute(self, *args, **kwargs):
                class _Result:
                    def scalar(self):
                        return None

                return _Result()

        yield _Conn()

    class _FakeEngine:
        def connect(self):
            return fake_connect()

    class _FakeS3Client:
        def list_buckets(self):
            return {"Buckets": []}

    monkeypatch.setattr("app.db.session.engine", _FakeEngine())
    monkeypatch.setattr("app.integrations.storage.s3_client.get_s3_client", lambda: _FakeS3Client())
    monkeypatch.setattr("app.core.migration_health.get_migration_health", lambda _engine: (True, "ok"))
    monkeypatch.setattr("app.core.worker_health.get_worker_health", lambda _engine: (False, "missing"))

    test_app = create_app(FULL_ROLE)
    test_client = TestClient(test_app)

    response = test_client.get("/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["worker"] == "missing"


def test_ready_returns_503_when_database_unreachable(monkeypatch):
    class _FailingEngine:
        def connect(self):
            raise ConnectionError("db unreachable")

    class _FakeS3Client:
        def list_buckets(self):
            return {"Buckets": []}

    monkeypatch.setattr("app.db.session.engine", _FailingEngine())
    monkeypatch.setattr("app.integrations.storage.s3_client.get_s3_client", lambda: _FakeS3Client())
    monkeypatch.setattr("app.core.worker_health.get_worker_health", lambda _engine: (True, "ok"))
    monkeypatch.setattr("app.core.migration_health.get_migration_health", lambda _engine: (True, "ok"))

    test_app = create_app(FULL_ROLE)
    test_client = TestClient(test_app)

    response = test_client.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["database"].startswith("error:")
    assert body["checks"]["storage"] == "ok"
