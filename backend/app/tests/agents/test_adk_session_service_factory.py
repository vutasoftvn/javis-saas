# backend/app/tests/agents/test_adk_session_service_factory.py
from unittest.mock import patch

from app.workforce.agents.orchestration.adk.session_service_factory import (
    build_adk_session_service,
    resolve_adk_runtime_database_url,
)


def test_resolve_adk_runtime_database_url_derives_from_database_url(monkeypatch):
    monkeypatch.delenv("ADK_RUNTIME_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://javis:javis@localhost:5432/javis")
    url = resolve_adk_runtime_database_url()
    assert url.startswith("postgresql+asyncpg://")
    assert url == "postgresql+asyncpg://javis:javis@localhost:5432/javis"


def test_resolve_adk_runtime_database_url_respects_explicit_override(monkeypatch):
    monkeypatch.setenv("ADK_RUNTIME_DATABASE_URL", "postgresql+asyncpg://custom/adk_runtime_db")
    url = resolve_adk_runtime_database_url()
    assert url == "postgresql+asyncpg://custom/adk_runtime_db"


def test_build_adk_session_service_constructs_with_resolved_url(monkeypatch):
    monkeypatch.setenv("ADK_RUNTIME_DATABASE_URL", "postgresql+asyncpg://custom/adk_runtime_db")
    with patch(
        "app.workforce.agents.orchestration.adk.session_service_factory.DatabaseSessionService"
    ) as mock_cls:
        build_adk_session_service()
        assert mock_cls.call_count == 1
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["db_url"] == "postgresql+asyncpg://custom/adk_runtime_db"
        assert call_kwargs["connect_args"] == {"server_settings": {"search_path": "adk_runtime"}}
        assert "json_serializer" in call_kwargs

