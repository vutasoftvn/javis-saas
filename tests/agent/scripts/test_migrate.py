"""Integration test cho migration runner của packages/agent.

Yêu cầu env var `AGENT_MIGRATION_TEST_DATABASE_URL` trỏ tới 1 Postgres
RỖNG (chưa từng migrate, pgvector extension khả dụng). Bỏ qua nếu không set.

Cố ý dùng biến RIÊNG, không dùng chung `AGENT_TEST_DATABASE_URL` với các
test khác trong `tests/agent/{memory,knowledge,governance,runs}/` — những
test đó cần schema ĐÃ migrate sẵn, trong khi test này cần DB rỗng để đếm đúng
số migration áp dụng lần đầu. Dùng chung 1 biến cho cả 2 yêu cầu trái ngược
nhau sẽ khiến 1 trong 2 nhóm fail tuỳ thứ tự chạy — phát hiện thật khi lần đầu
chạy toàn bộ suite trên Postgres thật (trước đó chưa ai verify được vì máy
không có Postgres/Docker).
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("asyncpg")

TEST_DATABASE_URL = os.environ.get("AGENT_MIGRATION_TEST_DATABASE_URL")

requires_migration_database = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="AGENT_MIGRATION_TEST_DATABASE_URL not set — skipping real-Postgres migration runner test",
)


def test_canonical_agent_package_and_primary_schema_are_available():
    """The reusable runtime package and its main persistence schema share `agent`."""
    repo_root = Path(__file__).resolve().parents[3]
    migration = repo_root / "packages" / "agent" / "migrations" / "001_canonical_agent_schema.sql"

    assert migration.exists()
    assert "CREATE SCHEMA IF NOT EXISTS agent" in migration.read_text(encoding="utf-8")


def test_migration_runner_uses_a_dedicated_canonical_migrator_url_and_advisory_lock():
    source = (Path(__file__).resolve().parents[3] / "packages" / "agent" / "scripts" / "migrate.py").read_text(
        encoding="utf-8"
    )

    assert 'os.environ.get("AGENT_MIGRATOR_DATABASE_URL")' in source
    assert 'os.environ.get("AGENT_DATABASE_URL")' not in source
    assert 'os.environ.get("DATABASE_URL")' not in source
    assert "pg_advisory_lock" in source
    assert "pg_advisory_unlock" in source


@pytest.mark.asyncio
@requires_migration_database
async def test_run_migrations_applies_all_and_is_idempotent_on_rerun():
    from packages.agent.scripts.migrate import run_migrations

    migrations_dir = Path(__file__).resolve().parents[3] / "packages" / "agent" / "migrations"

    applied_first = await run_migrations(TEST_DATABASE_URL, migrations_dir)
    assert applied_first >= 3  # 001 runs, 002 governance, 003 memory/knowledge

    applied_second = await run_migrations(TEST_DATABASE_URL, migrations_dir)
    assert applied_second == 0  # rerun: 0 change, 0 error (Gate B)


@pytest.mark.asyncio
@requires_migration_database
async def test_run_migrations_fails_hard_on_checksum_mismatch(tmp_path: Path):
    from packages.agent.scripts.migrate import run_migrations, MigrationChecksumMismatchError

    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "001_test.sql").write_text("CREATE TABLE IF NOT EXISTS public.__migrate_test_a (id INT);")

    await run_migrations(TEST_DATABASE_URL, migrations_dir)

    # Sửa nội dung file ĐÃ applied — phải fail hard, không được âm thầm bỏ qua.
    (migrations_dir / "001_test.sql").write_text("CREATE TABLE IF NOT EXISTS public.__migrate_test_a (id INT, extra TEXT);")

    with pytest.raises(MigrationChecksumMismatchError):
        await run_migrations(TEST_DATABASE_URL, migrations_dir)
