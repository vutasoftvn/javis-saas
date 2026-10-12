"""Migration 043 (A0): the legacy OKR family is dropped, the unified one survives."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg2
import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load_env():
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k, v)


_load_env()


@pytest.fixture()
def workspace_conn():
    url = os.environ.get("WORKSPACE_TEST_MIGRATOR_DATABASE_URL") or os.environ.get(
        "WORKSPACE_DATABASE_URL"
    )
    if not url:
        pytest.skip("WORKSPACE database URL not configured")
    conn = psycopg2.connect(url.replace("+asyncpg", ""))
    try:
        yield conn
    finally:
        conn.close()


def _fetch(conn, sql):
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def test_legacy_okr_tables_are_gone(workspace_conn):
    rows = _fetch(
        workspace_conn,
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'strategy' AND table_name IN ('objectives', 'cosa_key_results')",
    )
    assert rows == []


def test_unified_okr_tables_survive(workspace_conn):
    rows = _fetch(
        workspace_conn,
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'strategy' AND table_name IN ('okr_objectives', 'key_results')",
    )
    assert {r[0] for r in rows} == {"okr_objectives", "key_results"}


def test_legacy_function_is_gone(workspace_conn):
    rows = _fetch(
        workspace_conn,
        "SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
        "WHERE n.nspname = 'strategy' AND p.proname = 'fn_goals_needing_review'",
    )
    assert rows == []
