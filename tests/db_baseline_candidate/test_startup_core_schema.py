"""Introspection test for the clean-slate Startup Core database baseline.

Asserts required direct hierarchy columns and strictly forbids legacy
framework / Academy tables.
"""

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

REQUIRED = {
    "strategy.projects": {"workspace_id"},
    "strategy.okr_objectives": {"workspace_id", "project_id"},
    "strategy.key_results": {"workspace_id", "objective_id"},
    "strategy.initiatives": {"workspace_id", "project_id", "key_result_id"},
    "operating.twelve_week_cycles": {"workspace_id", "project_id", "duration_weeks"},
    "operating.weekly_plans": {"workspace_id", "project_id", "cycle_id", "week_no"},
    "operating.weekly_commitments": {"workspace_id", "project_id", "weekly_plan_id"},
    "operating.tasks": {"workspace_id", "project_id", "weekly_commitment_id"},
}

FORBIDDEN_TABLES = {
    "strategy.pestel_signals",
    "strategy.swot_items",
    "strategy.tows_options",
    "strategy.portfolios",
    "academy.lesson_attempts",
}


def _get_connection():
    url = os.environ.get("WORKSPACE_TEST_MIGRATOR_DATABASE_URL") or os.environ.get(
        "WORKSPACE_DATABASE_URL"
    )
    if not url:
        pytest.skip("WORKSPACE database URL not configured")
    clean_url = url.replace("+asyncpg", "")
    return psycopg2.connect(clean_url)


def test_required_hierarchy_columns():
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            for table_full, required_cols in REQUIRED.items():
                schema, table = table_full.split(".", 1)
                cur.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    """,
                    (schema, table),
                )
                existing_cols = {r[0] for r in cur.fetchall()}
                missing = required_cols - existing_cols
                assert not missing, f"Table {table_full} is missing required columns: {missing}"
    finally:
        conn.close()


def test_no_forbidden_framework_tables():
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_schema || '.' || table_name
                FROM information_schema.tables
                WHERE table_schema IN ('strategy', 'operating', 'academy')
                """
            )
            existing_tables = {r[0] for r in cur.fetchall()}
            present_forbidden = FORBIDDEN_TABLES & existing_tables
            assert not present_forbidden, f"Forbidden framework tables present: {present_forbidden}"
    finally:
        conn.close()
