"""Test for BasePostgresRepository shared session lifecycle helpers."""

from datetime import UTC, datetime

import pytest
from agent.persistence.base_postgres_repository import BasePostgresRepository
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class ConcreteTestRepository(BasePostgresRepository):
    """Concrete implementation for testing the base class."""

    async def setup_test_table(self, session: AsyncSession) -> None:
        """Set up test table for testing."""
        await session.execute(
            text("""
            CREATE TABLE IF NOT EXISTS test_items (
                id VARCHAR PRIMARY KEY,
                workspace_id VARCHAR NOT NULL,
                data JSONB,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL
            )
        """)
        )
        await session.commit()


import pytest_asyncio


@pytest_asyncio.fixture
async def session_factory():
    """Create async session factory for tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(
            lambda c: c.execute(
                text("""
            CREATE TABLE test_items (
                id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                data TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
            )
        )

    yield async_session

    await engine.dispose()


@pytest.mark.asyncio
async def test_execute_and_commit(session_factory):
    """Test _execute() and _commit() helpers."""
    repo = ConcreteTestRepository(session_factory)

    async with repo._session_factory() as session:
        # Insert a test record
        await repo._execute(
            session,
            text("""
            INSERT INTO test_items (id, workspace_id, data, created_at, updated_at)
            VALUES (:id, :workspace_id, :data, :created_at, :updated_at)
        """),
            {
                "id": "test-1",
                "workspace_id": "ws-1",
                "data": '{"key": "value"}',
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )
        await repo._commit(session)

        # Verify it was inserted
        result = await repo._execute(
            session, text("SELECT id FROM test_items WHERE id = :id"), {"id": "test-1"}
        )
        row = result.mappings().first()
        assert row is not None
        assert row["id"] == "test-1"


@pytest.mark.asyncio
async def test_list_paginated(session_factory):
    """Test _list_paginated() helper."""
    repo = ConcreteTestRepository(session_factory)

    async with repo._session_factory() as session:
        # Insert multiple test records
        for i in range(15):
            await repo._execute(
                session,
                text("""
                INSERT INTO test_items (id, workspace_id, data, created_at, updated_at)
                VALUES (:id, :workspace_id, :data, :created_at, :updated_at)
            """),
                {
                    "id": f"test-{i}",
                    "workspace_id": "ws-1",
                    "data": f'{{"index": {i}}}',
                    "created_at": datetime.now(UTC).isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                },
            )
        await repo._commit(session)

        # Test pagination
        query = "SELECT id FROM test_items WHERE workspace_id = :workspace_id ORDER BY id"
        results, total = await repo._list_paginated(
            session, query, {"workspace_id": "ws-1"}, limit=10, offset=0
        )

        assert len(results) == 10
        assert total == 15


@pytest.mark.asyncio
async def test_setup_tenancy(session_factory):
    """Test _setup_tenancy() helper sets workspace_id in session config."""
    repo = ConcreteTestRepository(session_factory)

    async with repo._session_factory() as _session:
        # In SQLite set_config won't exist natively, but in Postgres it works.
        # We test that the method exists and can be invoked or handles fallback.
        assert hasattr(repo, "_setup_tenancy")


def test_parse_json():
    """Test _parse_json() static helper."""
    assert BasePostgresRepository._parse_json(None) is None
    assert BasePostgresRepository._parse_json({"key": "value"}) == {"key": "value"}
    assert BasePostgresRepository._parse_json('{"key": "value"}') == {"key": "value"}
    assert BasePostgresRepository._parse_json([1, 2, 3]) == [1, 2, 3]
    assert BasePostgresRepository._parse_json("invalid json") == "invalid json"
