"""Xác nhận build_cosa_agent_plane() không còn âm thầm mặc định
InMemoryRunRepository cho production — đây là gap DB_FINAL_CUTOVER.md §8.1
đã audit xác nhận."""
from __future__ import annotations

import os

import pytest


def test_build_cosa_agent_plane_uses_postgres_when_database_url_given():
    from agent_core.runs.repository import PostgresRunRepository
    from apps.cosa.composition.agent_plane import build_cosa_agent_plane

    plane = build_cosa_agent_plane(database_url="postgresql+asyncpg://x:x@localhost/x")

    assert isinstance(plane.repository, PostgresRunRepository)


def test_build_cosa_agent_plane_uses_postgres_from_env_var(monkeypatch):
    from agent_core.runs.repository import PostgresRunRepository
    from apps.cosa.composition.agent_plane import build_cosa_agent_plane

    monkeypatch.setenv("AGENT_CORE_DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
    plane = build_cosa_agent_plane()

    assert isinstance(plane.repository, PostgresRunRepository)


def test_build_cosa_agent_plane_raises_without_database_url_or_explicit_repository(monkeypatch):
    from apps.cosa.composition.agent_plane import build_cosa_agent_plane

    monkeypatch.delenv("AGENT_CORE_DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="AGENT_CORE_DATABASE_URL"):
        build_cosa_agent_plane()


def test_build_cosa_agent_plane_still_accepts_explicit_in_memory_repository_for_tests():
    from agent_core.runs.repository import InMemoryRunRepository
    from apps.cosa.composition.agent_plane import build_cosa_agent_plane

    explicit_repo = InMemoryRunRepository()
    plane = build_cosa_agent_plane(repository=explicit_repo)

    assert plane.repository is explicit_repo
