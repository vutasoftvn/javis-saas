"""Part 2C.4 — MaxBodySizeMiddleware: từ chối body request vượt ngưỡng (HTTP 413)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from apps.cosa.api.middleware import MaxBodySizeMiddleware, resolve_max_request_bytes


@pytest.fixture
def app():
    application = FastAPI()
    application.add_middleware(MaxBodySizeMiddleware, max_bytes=1024)

    @application.post("/echo")
    async def echo(payload: dict):
        return {"len": len(payload.get("data", ""))}

    return application


def test_body_under_limit_passes(app):
    with TestClient(app) as client:
        res = client.post("/echo", json={"data": "x" * 100})
    assert res.status_code == 200
    assert res.json()["len"] == 100


def test_body_over_limit_rejected_by_content_length(app):
    with TestClient(app) as client:
        res = client.post("/echo", json={"data": "x" * 5000})
    assert res.status_code == 413
    assert "exceeds limit" in res.json()["detail"]


def test_invalid_content_length_rejected(app):
    with TestClient(app) as client:
        res = client.post(
            "/echo", data=b"{}", headers={"Content-Length": "not-a-number"}
        )
    assert res.status_code == 400


def test_resolve_max_request_bytes_env(monkeypatch):
    monkeypatch.setenv("COSA_MAX_REQUEST_BYTES", "2048")
    assert resolve_max_request_bytes() == 2048

    monkeypatch.setenv("COSA_MAX_REQUEST_BYTES", "0")
    with pytest.raises(RuntimeError):
        resolve_max_request_bytes()

    monkeypatch.setenv("COSA_MAX_REQUEST_BYTES", "abc")
    with pytest.raises(RuntimeError):
        resolve_max_request_bytes()

    monkeypatch.delenv("COSA_MAX_REQUEST_BYTES", raising=False)
    assert resolve_max_request_bytes() == 10 * 1024 * 1024
