# backend/app/tests/migrations/test_control_plane_baseline_migration.py
"""Test tren chinh source code cua migration baseline (khong can DB that) —
theo mau backend/app/tests/migrations/test_workflow_lifecycle_migration.py
da co san trong repo."""
import importlib.util
from pathlib import Path


def _load_migration():
    migration_path = (
        Path(__file__).resolve().parents[3]
        / "alembic_control_plane"
        / "versions"
        / "c9a1f0b2e3d4_unify_central_control_plane_schema.py"
    )
    spec = importlib.util.spec_from_file_location("control_plane_baseline_migration", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RecordingOperations:
    def __init__(self):
        self.executed_sql = []

    def execute(self, statement):
        self.executed_sql.append(str(statement))

    def __getattr__(self, name):
        # Cac phuong thuc khac (create_table/create_index/drop_table/...) da
        # duoc cac test metadata o Task 3-8 cover gian tiep qua
        # ControlPlaneBase.metadata; o day chi can bat lai loi goi khong xac
        # dinh mot cach ro rang thay vi AttributeError kho hieu.
        def _noop(*args, **kwargs):
            return None
        return _noop


def test_baseline_upgrade_seeds_plans_and_programs():
    migration = _load_migration()
    operations = RecordingOperations()
    migration.op = operations

    migration.upgrade()

    combined_sql = "\n".join(operations.executed_sql)
    for plan_id in ("free", "starter", "pro", "enterprise"):
        assert f"'{plan_id}'" in combined_sql, f"seed plan '{plan_id}' bi thieu"
    for program_id in ("sihub_incubation", "cosa_founder_fellowship"):
        assert f"'{program_id}'" in combined_sql, f"seed program '{program_id}' bi thieu"
    assert "ON CONFLICT (id) DO NOTHING" in combined_sql


import os
import subprocess
import sys

import pytest


def _control_plane_database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL", "")


@pytest.mark.skipif(
    os.environ.get("RUN_DB_INTEGRATION") != "1",
    reason="Can RUN_DB_INTEGRATION=1 va TEST_DATABASE_URL toi Postgres that",
)
def test_control_plane_baseline_upgrade_and_downgrade_round_trip_on_real_postgres():
    backend_root = Path(__file__).resolve().parents[3]
    env = {
        **os.environ,
        "PYTHONPATH": str(backend_root),
        "CONTROL_PLANE_DATABASE_URL": _control_plane_database_url(),
    }

    upgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic_control_plane.ini", "upgrade", "head"],
        cwd=str(backend_root), env=env, capture_output=True, text=True,
    )
    assert upgrade.returncode == 0, upgrade.stderr

    check_tables = subprocess.run(
        [
            sys.executable, "-c",
            """
import os
from sqlalchemy import create_engine, inspect
from app.platform.control_plane.db import ControlPlaneBase
import app.platform.control_plane.models  # noqa: F401

engine = create_engine(os.environ['CONTROL_PLANE_DATABASE_URL'])
inspector = inspect(engine)
actual = set(inspector.get_table_names(schema='control_plane'))
expected = {t.split('.', 1)[1] for t in ControlPlaneBase.metadata.tables}
missing = expected - actual
assert not missing, f"Bang thieu sau khi upgrade: {missing}"
""",
        ],
        cwd=str(backend_root), env=env, capture_output=True, text=True,
    )
    assert check_tables.returncode == 0, check_tables.stderr

    downgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic_control_plane.ini", "downgrade", "base"],
        cwd=str(backend_root), env=env, capture_output=True, text=True,
    )
    assert downgrade.returncode == 0, downgrade.stderr

    check_schema_gone = subprocess.run(
        [
            sys.executable, "-c",
            """
import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ['CONTROL_PLANE_DATABASE_URL'])
with engine.connect() as conn:
    exists = conn.execute(
        text("SELECT 1 FROM information_schema.schemata WHERE schema_name = 'control_plane'")
    ).scalar()
    assert exists is None, "Schema control_plane van con sau downgrade base"
""",
        ],
        cwd=str(backend_root), env=env, capture_output=True, text=True,
    )
    assert check_schema_gone.returncode == 0, check_schema_gone.stderr

