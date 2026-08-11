from contextlib import contextmanager

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


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
