"""Rate limit ở app (review 2026-09-27, G-4)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.cosa.api.middleware import (
    RateLimitMiddleware,
    SlidingWindowLimiter,
    resolve_rate_limit,
)


class _Clock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def test_sliding_window_allows_limit_then_blocks_until_window_slides():
    clock = _Clock()
    lim = SlidingWindowLimiter(3, window_sec=60, clock=clock)
    assert [lim.hit("k") for _ in range(3)] == [None, None, None]
    wait = lim.hit("k")
    assert wait is not None and 59 <= wait <= 60
    assert lim.hit("other") is None  # khoá độc lập
    clock.t += 61
    assert lim.hit("k") is None


def test_zero_disables():
    lim = SlidingWindowLimiter(0)
    assert all(lim.hit("k") is None for _ in range(1000))


def test_resolve_rate_limit_rejects_garbage(monkeypatch):
    monkeypatch.setenv("X_LIMIT", "abc")
    with pytest.raises(RuntimeError):
        resolve_rate_limit("X_LIMIT", 5)
    monkeypatch.setenv("X_LIMIT", "")
    assert resolve_rate_limit("X_LIMIT", 5) == 5


def test_middleware_returns_429_with_retry_after_and_exempts_health():
    app = FastAPI()

    @app.get("/agent/ping")
    def ping():
        return {"ok": True}

    @app.get("/healthz")
    def health():
        return {"ok": True}

    app.add_middleware(RateLimitMiddleware, limiter=SlidingWindowLimiter(2))
    c = TestClient(app)
    assert [c.get("/agent/ping").status_code for _ in range(2)] == [200, 200]
    r = c.get("/agent/ping")
    assert r.status_code == 429
    assert int(r.headers["retry-after"]) >= 1
    assert r.json()["code"] == "RATE_LIMITED"
    assert all(c.get("/healthz").status_code == 200 for _ in range(5))
