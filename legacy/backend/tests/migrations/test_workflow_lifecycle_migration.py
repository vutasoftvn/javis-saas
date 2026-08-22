import importlib.util
from pathlib import Path


class RecordingOperations:
    def __init__(self):
        self.added_columns = {}
        self.executed_sql = []
        self.altered_columns = []

    def add_column(self, table_name, column):
        self.added_columns[(table_name, column.name)] = column

    def execute(self, statement):
        self.executed_sql.append(str(statement))

    def alter_column(self, table_name, column_name, **kwargs):
        self.altered_columns.append((table_name, column_name, kwargs))


def _load_migration():
    migration_path = (
        Path(__file__).parents[2]
        / "alembic"
        / "versions"
        / "ad6a74ebb1c7_add_workflow_lifecycle_fields.py"
    )
    spec = importlib.util.spec_from_file_location("workflow_lifecycle_migration", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_workflow_lifecycle_upgrade_backfills_existing_versions_before_not_null():
    """Adding lifecycle fields to a populated workflow_versions table must succeed."""
    migration = _load_migration()
    operations = RecordingOperations()
    migration.op = operations

    migration.upgrade()

    state = operations.added_columns[("workflow_versions", "state")]
    schema_version = operations.added_columns[
        ("workflow_versions", "graph_schema_version")
    ]
    revision_token = operations.added_columns[("workflow_versions", "revision_token")]

    assert state.server_default is not None
    assert schema_version.server_default is not None
    assert revision_token.nullable is True
    assert any(
        "UPDATE workflow_versions" in statement
        and "legacy-" in statement
        for statement in operations.executed_sql
    )
    assert any(
        table == "workflow_versions"
        and column == "revision_token"
        and options.get("nullable") is False
        for table, column, options in operations.altered_columns
    )
