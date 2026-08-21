"""Regression tests cho schema Alembic riêng của COSA Central Control Plane
(Quyết định 2, docs/architecture/COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md)."""

import os
import subprocess
import sys
from pathlib import Path


def _run(code: str) -> subprocess.CompletedProcess:
    backend_root = Path(__file__).resolve().parents[2]
    environment = {**os.environ, "PYTHONPATH": str(backend_root)}
    return subprocess.run(
        [sys.executable, "-c", code],
        env=environment,
        capture_output=True,
        text=True,
    )


def test_control_plane_base_is_isolated_from_local_business_metadata():
    code = """
from app.platform.control_plane.db import ControlPlaneBase, CONTROL_PLANE_SCHEMA
from app.db.base_class import Base as LocalBase

assert CONTROL_PLANE_SCHEMA == "control_plane"
assert ControlPlaneBase.metadata.schema == "control_plane"
assert ControlPlaneBase.metadata is not LocalBase.metadata
"""
    result = _run(code)
    assert result.returncode == 0, result.stderr


def test_control_plane_alembic_ini_points_at_its_own_script_location():
    ini_path = Path(__file__).resolve().parents[2] / "alembic_control_plane.ini"
    assert ini_path.exists(), "backend/alembic_control_plane.ini chưa tồn tại"
    content = ini_path.read_text()
    assert "script_location = %(here)s/alembic_control_plane" in content


def test_control_plane_alembic_heads_loads_without_error():
    backend_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic_control_plane.ini", "heads"],
        cwd=str(backend_root),
        env={**os.environ, "PYTHONPATH": str(backend_root)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_platform_identity_tables_use_bigint_snowflake_pk_in_control_plane_schema():
    code = """
from app.platform.control_plane.db import ControlPlaneBase
import app.platform.control_plane.models  # noqa: F401
from sqlalchemy import BigInteger

tables = ControlPlaneBase.metadata.tables
for name in ("control_plane.platform_users", "control_plane.companies", "control_plane.company_memberships"):
    assert name in tables, name

pu = tables["control_plane.platform_users"]
assert isinstance(pu.c.id.type, BigInteger)
assert "hashed_password" in pu.c
assert "password_hash" not in pu.c  # ten cot da lech o deploy/central_vps, KHONG mang theo
assert pu.c.email.nullable is True
assert pu.c.phone.nullable is True
assert "last_login_at" in pu.c  # chi co o infra/supabase, central_vps thieu

company = tables["control_plane.companies"]
assert isinstance(company.c.id.type, BigInteger)
assert isinstance(company.c.created_by.type, BigInteger)

membership = tables["control_plane.company_memberships"]
assert isinstance(membership.c.company_id.type, BigInteger)
assert isinstance(membership.c.user_id.type, BigInteger)
"""
    result = _run(code)
    assert result.returncode == 0, result.stderr


def test_control_plane_baseline_revision_has_no_down_revision():
    versions_dir = Path(__file__).resolve().parents[2] / "alembic_control_plane" / "versions"
    migration = versions_dir / "c9a1f0b2e3d4_unify_central_control_plane_schema.py"
    assert migration.exists()
    content = migration.read_text()
    assert 'revision: str = "c9a1f0b2e3d4"' in content
    assert "down_revision: Union[str, Sequence[str], None] = None" in content


def test_commercial_tables_reference_companies_with_bigint_fk():
    code = """
from app.platform.control_plane.db import ControlPlaneBase
import app.platform.control_plane.models  # noqa: F401
from sqlalchemy import BigInteger, String

tables = ControlPlaneBase.metadata.tables
plan = tables["control_plane.plans"]
assert isinstance(plan.c.id.type, String)  # business key, khong phai Snowflake

license_ = tables["control_plane.licenses"]
assert isinstance(license_.c.id.type, BigInteger)
assert isinstance(license_.c.company_id.type, BigInteger)

entitlement = tables["control_plane.company_entitlements"]
assert isinstance(entitlement.c.company_id.type, BigInteger)
assert entitlement.c.company_id.primary_key is True
"""
    result = _run(code)
    assert result.returncode == 0, result.stderr


def test_projects_registry_drops_redundant_local_snowflake_column():
    """Regression test cho phat hien drift cu the o Quyet dinh 2: cot
    `local_project_snowflake` va constraint `uq_company_project_local` chi co
    y nghia khi PK trung tam la UUID — phai bi xoa khi PK da la BigInt
    Snowflake."""
    code = """
from app.platform.control_plane.db import ControlPlaneBase
import app.platform.control_plane.models  # noqa: F401
from sqlalchemy import BigInteger

tables = ControlPlaneBase.metadata.tables
registry = tables["control_plane.projects_registry"]
assert isinstance(registry.c.id.type, BigInteger)
assert "local_project_snowflake" not in registry.c
assert "uq_company_project_local" not in {c.name for c in registry.constraints}

history = tables["control_plane.project_stage_history"]
assert isinstance(history.c.project_id.type, BigInteger)
assert "metadata_json" in {col.name for col in history.c} or "metadata" in history.c

outcomes = tables["control_plane.project_outcomes"]
assert outcomes.c.project_id.primary_key is True

metrics = tables["control_plane.project_metrics"]
assert metrics.c.project_id.primary_key is True
"""
    result = _run(code)
    assert result.returncode == 0, result.stderr




