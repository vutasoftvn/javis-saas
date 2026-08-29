"""Migration runner thủ công cho `packages/agent`.

Cùng convention idempotent với services/company/scripts/migrate.mjs và
services/cosa/scripts/migrate.mjs: track migration đã áp trong bảng
public.schema_migrations (service, filename, sha256, applied_at). Nếu
(service, filename) đã applied mà SHA hiện tại khác nội dung file trên đĩa —
FAIL HARD (DB_FINAL_CUTOVER.md §5.2), không âm thầm bỏ qua hay ghi đè.

Chạy: python -m packages.agent.scripts.migrate
hoặc: make migrate-agent-platform
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
from pathlib import Path

import asyncpg

SERVICE_NAME = "agent"
MIGRATION_LOCK_NAME = f"{SERVICE_NAME}:migrations"


class MigrationChecksumMismatchError(Exception):
    def __init__(self, filename: str) -> None:
        super().__init__(
            f"migration {SERVICE_NAME}/{filename} was already applied with a different "
            f"checksum — historical migrations are immutable, create a new migration instead "
            f"of editing this one."
        )
        self.filename = filename


def _sorted_migration_files(migrations_dir: Path) -> list[Path]:
    return sorted(
        [p for p in migrations_dir.glob("*.sql") if not p.name.endswith(".down.sql")],
        key=lambda p: p.name,
    )


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


async def _acquire_migration_lock(conn: asyncpg.Connection) -> None:
    await conn.execute("SELECT pg_advisory_lock(hashtext($1))", MIGRATION_LOCK_NAME)


async def _release_migration_lock(conn: asyncpg.Connection) -> None:
    await conn.execute("SELECT pg_advisory_unlock(hashtext($1))", MIGRATION_LOCK_NAME)


async def _grant_application_access(conn: asyncpg.Connection) -> None:
    """Give the Agent runtime DML access after migrations create their schemas."""
    statements = await conn.fetch(
        """
        SELECT format('GRANT USAGE ON SCHEMA %I TO agent_app', nspname) AS statement
        FROM pg_namespace
        WHERE nspowner = (SELECT oid FROM pg_roles WHERE rolname = current_user)
          AND nspname NOT IN ('public', 'information_schema')
          AND nspname NOT LIKE 'pg_%'
        UNION ALL
        SELECT format('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA %I TO agent_app', nspname)
        FROM pg_namespace
        WHERE nspowner = (SELECT oid FROM pg_roles WHERE rolname = current_user)
          AND nspname NOT IN ('public', 'information_schema')
          AND nspname NOT LIKE 'pg_%'
        UNION ALL
        SELECT format('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA %I TO agent_app', nspname)
        FROM pg_namespace
        WHERE nspowner = (SELECT oid FROM pg_roles WHERE rolname = current_user)
          AND nspname NOT IN ('public', 'information_schema')
          AND nspname NOT LIKE 'pg_%'
        UNION ALL
        SELECT format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO agent_app', nspname)
        FROM pg_namespace
        WHERE nspowner = (SELECT oid FROM pg_roles WHERE rolname = current_user)
          AND nspname NOT IN ('public', 'information_schema')
          AND nspname NOT LIKE 'pg_%'
        UNION ALL
        SELECT format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT USAGE, SELECT ON SEQUENCES TO agent_app', nspname)
        FROM pg_namespace
        WHERE nspowner = (SELECT oid FROM pg_roles WHERE rolname = current_user)
          AND nspname NOT IN ('public', 'information_schema')
          AND nspname NOT LIKE 'pg_%'
        """
    )
    for row in statements:
        await conn.execute(row["statement"])


async def check_migration_checksums(database_url: str, migrations_dir: Path) -> bool:
    # Verify that all applied migrations have matching checksums (for deploy-preflight).
    # Returns True if OK, False (+ prints error) if any drift found.
    asyncpg_dsn = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(asyncpg_dsn)
    lock_acquired = False
    try:
        await _acquire_migration_lock(conn)
        lock_acquired = True
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

            if row is not None and row["sha256"] != checksum:
                errors.append(
                    f"❌ migration {SERVICE_NAME}/{file.name} was already applied with a different "
                    f"checksum — historical migrations are immutable, create a new migration instead "
                    f"of editing this one."
                )

        if errors:
            print("[migrate:agent] ❌ Checksum verification failed:")
            for err in errors:
                print(err)
            return False

        print("[migrate:agent] ✓ All migration checksums valid (no drift detected)")
        return True
    finally:
        if lock_acquired:
            await _release_migration_lock(conn)
        await conn.close()


async def run_migrations(database_url: str, migrations_dir: Path, *, baseline: bool = False) -> int:
    # `asyncpg.connect()` chỉ nhận scheme "postgresql://"/"postgres://" thuần,
    # trong khi AGENT_DATABASE_URL toàn hệ thống dùng dạng SQLAlchemy async
    # "postgresql+asyncpg://" (xem apps/cosa/composition/agent_plane.py,
    # memory/store.py, knowledge/store.py, governance/store.py) — phát hiện lần
    # đầu chạy migration thật trên Postgres (trước đây chỉ verify bằng đối chiếu
    # tĩnh, chưa từng chạy thật).
    asyncpg_dsn = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(asyncpg_dsn)
    applied_count = 0
    lock_acquired = False
    try:
        await _acquire_migration_lock(conn)
        lock_acquired = True
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
                print(f"[migrate:agent] baselining {file.name} (not executed)")
                await conn.execute(
                    "INSERT INTO public.schema_migrations (service, filename, sha256) VALUES ($1, $2, $3)",
                    SERVICE_NAME,
                    file.name,
                    checksum,
                )
                applied_count += 1
                continue

            print(f"[migrate:agent] applying {file.name}")
            async with conn.transaction():
                await conn.execute(content)
                await conn.execute(
                    "INSERT INTO public.schema_migrations (service, filename, sha256) VALUES ($1, $2, $3)",
                    SERVICE_NAME,
                    file.name,
                    checksum,
                )
            applied_count += 1

        if not baseline:
            await _grant_application_access(conn)

        if applied_count > 0:
            print(
                f"[migrate:agent] {'baselined' if baseline else 'applied'} {applied_count} migration(s)"
            )
        else:
            print("[migrate:agent] nothing to apply, already up to date")

        return applied_count
    finally:
        if lock_acquired:
            await _release_migration_lock(conn)
        await conn.close()


async def rollback_migrations(database_url: str, migrations_dir: Path, steps: int = 1) -> int:
    asyncpg_dsn = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(asyncpg_dsn)
    rolled_back_count = 0
    lock_acquired = False
    try:
        await _acquire_migration_lock(conn)
        lock_acquired = True
        rows = await conn.fetch(
            "SELECT filename FROM public.schema_migrations WHERE service = $1 ORDER BY filename DESC LIMIT $2",
            SERVICE_NAME,
            steps,
        )

        if not rows:
            print("[migrate:agent] No migrations to roll back.")
            return 0

        for row in rows:
            filename = row["filename"]
            stem = filename[:-4] if filename.endswith(".sql") else filename
            down_path = migrations_dir / f"{stem}.down.sql"

            if not down_path.exists():
                raise FileNotFoundError(
                    f"Cannot roll back {filename}: missing down migration {down_path.name}"
                )

            down_content = down_path.read_text(encoding="utf-8")
            print(f"[migrate:agent] rolling back {filename} using {down_path.name}")

            async with conn.transaction():
                await conn.execute(down_content)
                await conn.execute(
                    "DELETE FROM public.schema_migrations WHERE service = $1 AND filename = $2",
                    SERVICE_NAME,
                    filename,
                )
            rolled_back_count += 1

        print(f"[migrate:agent] rolled back {rolled_back_count} migration(s)")
        return rolled_back_count
    finally:
        if lock_acquired:
            await _release_migration_lock(conn)
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--down", type=int, nargs="?", const=1, help="Number of migrations to roll back"
    )
    args = parser.parse_args()

    database_url = os.environ.get("AGENT_MIGRATOR_DATABASE_URL")
    if not database_url:
        raise SystemExit("AGENT_MIGRATOR_DATABASE_URL must be set")

    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"

    if args.check:
        # Checksum verification mode for deploy-preflight
        ok = asyncio.run(check_migration_checksums(database_url, migrations_dir))
        raise SystemExit(0 if ok else 1)

    if args.down is not None:
        asyncio.run(rollback_migrations(database_url, migrations_dir, steps=args.down))
        return

    asyncio.run(run_migrations(database_url, migrations_dir, baseline=args.baseline))


if __name__ == "__main__":
    main()
