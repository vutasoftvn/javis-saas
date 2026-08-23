"""Integration test cho migration runner của packages/agent_core.

Yêu cầu env var `AGENT_CORE_TEST_DATABASE_URL` trỏ tới 1 Postgres rỗng
(pgvector extension khả dụng). Bỏ qua nếu không set.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("asyncpg")

TEST_DATABASE_URL = os.environ.get("AGENT_CORE_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="AGENT_CORE_TEST_DATABASE_URL not set — skipping real-Postgres migration runner test",
)


@pytest.mark.asyncio
async def test_run_migrations_applies_all_and_is_idempotent_on_rerun():
    from packages.agent_core.scripts.migrate import run_migrations

    migrations_dir = Path(__file__).resolve().parents[3] / "packages" / "agent_core" / "migrations"

    applied_first = await run_migrations(TEST_DATABASE_URL, migrations_dir)
    assert applied_first >= 3  # 001 runs, 002 governance, 003 memory/knowledge

    applied_second = await run_migrations(TEST_DATABASE_URL, migrations_dir)
    assert applied_second == 0  # rerun: 0 change, 0 error (Gate B)


@pytest.mark.asyncio
async def test_run_migrations_fails_hard_on_checksum_mismatch(tmp_path: Path):
    from packages.agent_core.scripts.migrate import run_migrations, MigrationChecksumMismatchError

    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "001_test.sql").write_text("CREATE TABLE IF NOT EXISTS public.__migrate_test_a (id INT);")

    await run_migrations(TEST_DATABASE_URL, migrations_dir)

    # Sửa nội dung file ĐÃ applied — phải fail hard, không được âm thầm bỏ qua.
    (migrations_dir / "001_test.sql").write_text("CREATE TABLE IF NOT EXISTS public.__migrate_test_a (id INT, extra TEXT);")

    with pytest.raises(MigrationChecksumMismatchError):
        await run_migrations(TEST_DATABASE_URL, migrations_dir)
