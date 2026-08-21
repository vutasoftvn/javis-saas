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
