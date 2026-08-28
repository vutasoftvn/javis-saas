"""Part 2C.4 — CORS origins guard cho apps/cosa/api (defense-in-depth).

Xác nhận `create_cosa_app()`:
  - staging/production BẮT BUỘC set `CORS_ORIGINS` tường minh (không có default "*"),
  - từ chối wildcard "*" khi `allow_credentials=True`,
  - chấp nhận origin cụ thể và gắn đúng vào CORSMiddleware.

Guard nằm ngay trong thân `create_cosa_app` (chạy lúc tạo app, TRƯỚC lifespan),
nên test chỉ cần plane inject giả — không cần DB/model thật.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from starlette.middleware.cors import CORSMiddleware

from apps.cosa.api.app import create_cosa_app


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    yield


def _cors_option(app, key):
    for mw in app.user_middleware:
        if mw.cls is CORSMiddleware:
            return mw.kwargs.get(key)
    raise AssertionError("CORSMiddleware không được gắn vào app")


@pytest.mark.parametrize("env", ["production", "staging", "prod"])
def test_staging_prod_requires_explicit_cors_origins(monkeypatch, env):
    monkeypatch.setenv("APP_ENV", env)
    with pytest.raises(RuntimeError, match="CORS_ORIGINS must be explicitly configured"):
        create_cosa_app(plane=MagicMock())


@pytest.mark.parametrize("env", ["production", "staging"])
def test_staging_prod_rejects_wildcard_origin(monkeypatch, env):
    monkeypatch.setenv("APP_ENV", env)
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com,*")
    with pytest.raises(RuntimeError, match="Wildcard CORS origin"):
        create_cosa_app(plane=MagicMock())


def test_prod_accepts_explicit_origins(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com, https://admin.example.com")
    app = create_cosa_app(plane=MagicMock())
    assert _cors_option(app, "allow_origins") == [
        "https://app.example.com",
        "https://admin.example.com",
    ]


def test_development_defaults_to_wildcard(monkeypatch):
    """Dev không bắt buộc CORS_ORIGINS — vẫn cho "*" để DX local không vỡ."""
    monkeypatch.setenv("APP_ENV", "development")
    app = create_cosa_app(plane=MagicMock())
    assert _cors_option(app, "allow_origins") == ["*"]
