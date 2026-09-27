"""Parity InMemory ↔ Postgres cho repository (G-2 của review 2026-09-27).

Cùng một kịch bản chạy trên cả 2 implementation. Bug thật đã lọt vì test route
chỉ dùng InMemory (list_runs SELECT cột không tồn tại; DTO activity bắt buộc
field Postgres lưu NULL). Postgres chỉ chạy khi có AGENT_TEST_DATABASE_URL
(schema đã migrate) — CI job durability/quality-integration có sẵn biến này.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

_RAW = os.environ.get("AGENT_TEST_DATABASE_URL") or ""
PG_URL = (
    _RAW.replace("postgresql://", "postgresql+asyncpg://", 1)
    if _RAW.startswith("postgresql://")
    else _RAW
)

BACKENDS = [
    "memory",
    pytest.param(
        "postgres",
        marks=pytest.mark.skipif(not PG_URL, reason="AGENT_TEST_DATABASE_URL not set"),
    ),
]


@pytest_asyncio.fixture
async def pg_session_factory() -> AsyncIterator[object]:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(PG_URL)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()
