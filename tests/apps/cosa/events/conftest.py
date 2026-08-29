from __future__ import annotations

import os

import pytest_asyncio

try:
    import asyncpg
except ImportError:  # pragma: no cover
    asyncpg = None


def _dsn() -> str | None:
    raw = os.environ.get("AGENT_TEST_DATABASE_URL") or os.environ.get("AGENT_DATABASE_URL")
    if not raw:
        return None
    return raw.replace("postgresql+asyncpg://", "postgresql://").replace("+asyncpg", "")


@pytest_asyncio.fixture
async def pg_pool():
    """asyncpg pool tới Agent Core DB. Skip nếu không có URL / không connect được."""
    import pytest

    if asyncpg is None:
        pytest.skip("asyncpg not installed")
    dsn = _dsn()
    if not dsn:
        pytest.skip("AGENT_TEST_DATABASE_URL not set")
    try:
        pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2)
    except Exception as e:  # pragma: no cover
        pytest.skip(f"cannot connect to {dsn}: {e}")
    try:
        yield pool
    finally:
        await pool.close()
