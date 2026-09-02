"""Cluster Postgres disposable cho E2E: mỗi lần chạy tạo 3 DB mới có suffix
run_id, áp toàn bộ migration, rồi DROP khi teardown. Đáp ứng yêu cầu
"disposable CI PostgreSQL with unique names/fresh database" trong
docs/superpowers/plans/2026-09-01-truthful-mvp-hardening.md.
"""

from __future__ import annotations

import contextlib
import os
import subprocess
from dataclasses import dataclass

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

_ADMIN = {
    "host": os.environ.get("PGHOST", "127.0.0.1"),
    "port": int(os.environ.get("PGPORT", "5432")),
    "user": os.environ.get("PGUSER", "postgres"),
    "password": os.environ.get("PGPASSWORD", "postgres"),
    "dbname": "postgres",
}
_APP_PWD = {
    "agent": "change-me-agent-app",
    "cosa": "change-me-cosa-app",
    "workspace": "change-me-workspace-app",
}
_MIG_PWD = {
    "agent": "change-me-agent-migrator",
    "cosa": "change-me-cosa-migrator",
    "workspace": "change-me-workspace-migrator",
}


@dataclass
class DisposableCluster:
    run_id: str
    agent_app_url: str
    agent_migrator_url: str
    cosa_app_url: str
    cosa_migrator_url: str
    workspace_app_url: str
    workspace_migrator_url: str


def _db_name(svc: str, run_id: str) -> str:
    return f"{svc}_{run_id}"


def _url(svc: str, run_id: str, *, role: str, pwd: str, driver: str = "postgresql") -> str:
    host, port = _ADMIN["host"], _ADMIN["port"]
    return f"{driver}://{role}:{pwd}@{host}:{port}/{_db_name(svc, run_id)}?sslmode=disable"


def _admin_conn() -> psycopg2.extensions.connection:
    conn = psycopg2.connect(connect_timeout=5, **_ADMIN)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return conn


def create_disposable_cluster(run_id: str) -> DisposableCluster:
    conn = _admin_conn()
    try:
        with conn.cursor() as cur:
            for svc in ("agent", "cosa", "workspace"):
                name = _db_name(svc, run_id)
                # Dọn DB sót lại từ lần chạy trước bị abort để CREATE không
                # hard-fail khi tên trùng.
                cur.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
                cur.execute(f'CREATE DATABASE "{name}" OWNER {svc}_migrator')
                cur.execute(f'GRANT CONNECT ON DATABASE "{name}" TO {svc}_app, {svc}_migrator')
    finally:
        conn.close()

    # Per-DB: chặn CREATE trên public cho PUBLIC, cho app USAGE, bật vector cho agent.
    for svc in ("agent", "cosa", "workspace"):
        db_conn = psycopg2.connect(
            connect_timeout=5,
            host=_ADMIN["host"],
            port=_ADMIN["port"],
            user=_ADMIN["user"],
            password=_ADMIN["password"],
            dbname=_db_name(svc, run_id),
        )
        db_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        try:
            with db_conn.cursor() as cur:
                if svc == "agent":
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                cur.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
                cur.execute(f"GRANT USAGE ON SCHEMA public TO {svc}_app")
        finally:
            db_conn.close()

    return DisposableCluster(
        run_id=run_id,
        agent_app_url=_url("agent", run_id, role="agent_app", pwd=_APP_PWD["agent"]),
        agent_migrator_url=_url(
            "agent",
            run_id,
            role="agent_migrator",
            pwd=_MIG_PWD["agent"],
            driver="postgresql+asyncpg",
        ),
        cosa_app_url=_url("cosa", run_id, role="cosa_app", pwd=_APP_PWD["cosa"]),
        cosa_migrator_url=_url("cosa", run_id, role="cosa_migrator", pwd=_MIG_PWD["cosa"]),
        workspace_app_url=_url(
            "workspace", run_id, role="workspace_app", pwd=_APP_PWD["workspace"]
        ),
        workspace_migrator_url=_url(
            "workspace", run_id, role="workspace_migrator", pwd=_MIG_PWD["workspace"]
        ),
    )


def apply_migrations(cluster: DisposableCluster) -> None:
    steps = [
        (
            [
                os.environ.get("PYTHON", ".venv/bin/python"),
                "-m",
                "packages.agent.scripts.migrate",
            ],
            _REPO_ROOT,
            {"AGENT_MIGRATOR_DATABASE_URL": cluster.agent_migrator_url},
        ),
        (
            ["node", "scripts/migrate.mjs"],
            os.path.join(_REPO_ROOT, "services", "cosa"),
            {"COSA_MIGRATOR_DATABASE_URL": cluster.cosa_migrator_url},
        ),
        (
            ["node", "scripts/migrate.mjs"],
            os.path.join(_REPO_ROOT, "services", "company"),
            {"WORKSPACE_MIGRATOR_DATABASE_URL": cluster.workspace_migrator_url},
        ),
    ]
    for argv, cwd, extra_env in steps:
        result = subprocess.run(
            argv,
            cwd=cwd,
            env={**os.environ, **extra_env},
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"disposable migrate failed: {' '.join(argv)} (cwd={cwd})\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )


def drop_disposable_cluster(cluster: DisposableCluster) -> None:
    # Contract: teardown KHÔNG được raise — chạy trong fixture `finally`, một
    # exception ở đây sẽ che kết quả test thật. Nuốt cả lỗi connect admin.
    conn = None
    try:
        conn = _admin_conn()
        with conn.cursor() as cur:
            for svc in ("agent", "cosa", "workspace"):
                with contextlib.suppress(Exception):
                    cur.execute(
                        f'DROP DATABASE IF EXISTS "{_db_name(svc, cluster.run_id)}" WITH (FORCE)'
                    )
    except Exception:
        pass
    finally:
        if conn is not None:
            with contextlib.suppress(Exception):
                conn.close()
