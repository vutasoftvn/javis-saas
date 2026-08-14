"""Read-only Alembic schema readiness checks."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.engine import Engine


def _head_revisions() -> set[str]:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    return set(ScriptDirectory.from_config(config).get_heads())


def get_migration_health(engine: Engine) -> tuple[bool, str]:
    """Return whether the database records exactly the current Alembic head."""
    try:
        with engine.connect() as connection:
            revisions = set(connection.execute(text("SELECT version_num FROM alembic_version")).scalars())
        if not revisions:
            return False, "missing"
        if revisions == _head_revisions():
            return True, "ok"
        return False, "behind"
    except Exception:
        return False, "error"
