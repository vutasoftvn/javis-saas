"""Migration runner thủ công cho `packages/agent_core`.

Cùng convention idempotent với services/company/scripts/migrate.mjs và
services/cosa/scripts/migrate.mjs: track migration đã áp trong bảng
public.schema_migrations (service, filename, sha256, applied_at). Nếu
(service, filename) đã applied mà SHA hiện tại khác nội dung file trên đĩa —
FAIL HARD (DB_FINAL_CUTOVER.md §5.2), không âm thầm bỏ qua hay ghi đè.

Chạy: python -m packages.agent_core.scripts.migrate
hoặc: make migrate-agent-platform
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
from pathlib import Path

import asyncpg

SERVICE_NAME = "agent_core"


class MigrationChecksumMismatchError(Exception):
    def __init__(self, filename: str) -> None:
        super().__init__(
            f"migration {SERVICE_NAME}/{filename} was already applied with a different "
            f"checksum — historical migrations are immutable, create a new migration instead "
            f"of editing this one."
        )
        self.filename = filename


def _sorted_migration_files(migrations_dir: Path) -> list[Path]:
    return sorted(migrations_dir.glob("*.sql"), key=lambda p: p.name)


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


async def check_migration_checksums(database_url: str, migrations_dir: Path) -> bool:
    # Verify that all applied migrations have matching checksums (for deploy-preflight).
    # Returns True if OK, False (+ prints error) if any drift found.
    asyncpg_dsn = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(asyncpg_dsn)
    try:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS public.schema_migrations (
                service TEXT NOT NULL,
                filename TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (service, filename)
            );
            """
        )

        errors = []
        for file in _sorted_migration_files(migrations_dir):
            content = file.read_text(encoding="utf-8")
            checksum = _sha256(content)

            row = await conn.fetchrow(
                "SELECT sha256 FROM public.schema_migrations WHERE service = $1 AND filename = $2",
                SERVICE_NAME,
                file.name,
            )

            if row is not None:
                if row["sha256"] != checksum:
                    errors.append(
                        f"❌ migration {SERVICE_NAME}/{file.name} was already applied with a different "
                        f"checksum — historical migrations are immutable, create a new migration instead "
                        f"of editing this one."
                    )

        if errors:
            print("[migrate:agent_core] ❌ Checksum verification failed:")
            for err in errors:
                print(err)
            return False

        print("[migrate:agent_core] ✓ All migration checksums valid (no drift detected)")
        return True
    finally:
        await conn.close()


async def run_migrations(database_url: str, migrations_dir: Path, *, baseline: bool = False) -> int:
    # `asyncpg.connect()` chỉ nhận scheme "postgresql://"/"postgres://" thuần,
    # trong khi AGENT_CORE_DATABASE_URL toàn hệ thống dùng dạng SQLAlchemy async
    # "postgresql+asyncpg://" (xem apps/cosa/composition/agent_plane.py,
    # memory/store.py, knowledge/store.py, governance/store.py) — phát hiện lần
    # đầu chạy migration thật trên Postgres (trước đây chỉ verify bằng đối chiếu
    # tĩnh, chưa từng chạy thật).
    asyncpg_dsn = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(asyncpg_dsn)
    applied_count = 0
    try:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS public.schema_migrations (
                service TEXT NOT NULL,
                filename TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (service, filename)
            );
            """
        )

        for file in _sorted_migration_files(migrations_dir):
            content = file.read_text(encoding="utf-8")
            checksum = _sha256(content)

            row = await conn.fetchrow(
                "SELECT sha256 FROM public.schema_migrations WHERE service = $1 AND filename = $2",
                SERVICE_NAME,
                file.name,
            )

            if row is not None:
                if row["sha256"] != checksum:
                    raise MigrationChecksumMismatchError(file.name)
                continue

            if baseline:
                print(f"[migrate:agent_core] baselining {file.name} (not executed)")
                await conn.execute(
                    "INSERT INTO public.schema_migrations (service, filename, sha256) VALUES ($1, $2, $3)",
                    SERVICE_NAME,
                    file.name,
                    checksum,
                )
                applied_count += 1
                continue

            print(f"[migrate:agent_core] applying {file.name}")
            async with conn.transaction():
                await conn.execute(content)
                await conn.execute(
                    "INSERT INTO public.schema_migrations (service, filename, sha256) VALUES ($1, $2, $3)",
                    SERVICE_NAME,
                    file.name,
                    checksum,
                )
            applied_count += 1

        if applied_count > 0:
            print(f"[migrate:agent_core] {'baselined' if baseline else 'applied'} {applied_count} migration(s)")
        else:
            print("[migrate:agent_core] nothing to apply, already up to date")

        return applied_count
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    database_url = os.environ.get("AGENT_CORE_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("AGENT_CORE_DATABASE_URL or DATABASE_URL must be set")

    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"

    if args.check:
        # Checksum verification mode for deploy-preflight
        ok = asyncio.run(check_migration_checksums(database_url, migrations_dir))
        raise SystemExit(0 if ok else 1)

    asyncio.run(run_migrations(database_url, migrations_dir, baseline=args.baseline))


if __name__ == "__main__":
    main()
