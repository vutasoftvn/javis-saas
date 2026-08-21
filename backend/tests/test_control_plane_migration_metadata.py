"""Regression tests cho schema Alembic riêng của COSA Central Control Plane
(Quyết định 2, docs/architecture/COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md)."""

import os
import subprocess
import sys
from pathlib import Path


def _run(code: str) -> subprocess.CompletedProcess:
    backend_root = Path(__file__).resolve().parents[1]
    environment = {**os.environ, "PYTHONPATH": str(backend_root)}
    return subprocess.run(
        [sys.executable, "-c", code],
        env=environment,
        capture_output=True,
        text=True,
    )


def test_control_plane_base_is_isolated_from_local_business_metadata():
    code = """
from platform_core.control_plane.db import ControlPlaneBase, CONTROL_PLANE_SCHEMA
from db.base_class import Base as LocalBase

assert CONTROL_PLANE_SCHEMA == "control_plane"
assert ControlPlaneBase.metadata.schema == "control_plane"
assert ControlPlaneBase.metadata is not LocalBase.metadata
"""
    result = _run(code)
    assert result.returncode == 0, result.stderr


def test_control_plane_alembic_ini_points_at_its_own_script_location():
    ini_path = Path(__file__).resolve().parents[1] / "alembic_control_plane.ini"
    assert ini_path.exists(), "backend/alembic_control_plane.ini chưa tồn tại"
    content = ini_path.read_text()
    assert "script_location = %(here)s/alembic_control_plane" in content


def test_control_plane_alembic_heads_loads_without_error():
    backend_root = Path(__file__).resolve().parents[1]
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
from platform_core.control_plane.db import ControlPlaneBase
import platform_core.control_plane.models  # noqa: F401
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
    versions_dir = Path(__file__).resolve().parents[1] / "alembic_control_plane" / "versions"
    migration = versions_dir / "c9a1f0b2e3d4_unify_central_control_plane_schema.py"
    assert migration.exists()
    content = migration.read_text()
    assert 'revision: str = "c9a1f0b2e3d4"' in content
    assert "down_revision: Union[str, Sequence[str], None] = None" in content


def test_commercial_tables_reference_companies_with_bigint_fk():
    code = """
from platform_core.control_plane.db import ControlPlaneBase
import platform_core.control_plane.models  # noqa: F401
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
from platform_core.control_plane.db import ControlPlaneBase
import platform_core.control_plane.models  # noqa: F401
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


def test_ecosystem_tables_use_correct_pk_types():
    code = """
from platform_core.control_plane.db import ControlPlaneBase
import platform_core.control_plane.models  # noqa: F401
from sqlalchemy import String, BigInteger

tables = ControlPlaneBase.metadata.tables
program = tables["control_plane.programs"]
assert isinstance(program.c.id.type, String)

cohort = tables["control_plane.cohorts"]
assert isinstance(cohort.c.id.type, String)
assert isinstance(cohort.c.program_id.type, String)

participant = tables["control_plane.program_participants"]
assert isinstance(participant.c.id.type, BigInteger)
assert isinstance(participant.c.user_id.type, BigInteger)

link = tables["control_plane.project_program_links"]
assert {c.name for c in link.primary_key.columns} == {"project_id", "cohort_id"}
"""
    result = _run(code)
    assert result.returncode == 0, result.stderr


def test_control_plane_deployments_table_does_not_collide_with_local_business_db():
    """Regression test cho va cham ten bang thuc te da verify:
    app.platform.core.deployment_models.Deployment (Local Business DB,
    __tablename__ = 'deployments', schema public) trung ten voi bang
    control-plane 'deployments' (VPS deployment registry). Ca 2 phai la 2
    Table object khac nhau, khac schema, khac cot."""
    code = """
from platform_core.control_plane.db import ControlPlaneBase
import platform_core.control_plane.models  # noqa: F401
from db.base import Base as LocalBase  # import day du model Local Business DB

cp_deployments = ControlPlaneBase.metadata.tables["control_plane.deployments"]
local_deployments = LocalBase.metadata.tables["deployments"]

assert cp_deployments is not local_deployments
assert cp_deployments.schema == "control_plane"
assert local_deployments.schema is None  # public (mac dinh)
assert {c.name for c in cp_deployments.c} != {c.name for c in local_deployments.c}
assert "app_id" in cp_deployments.c  # cot rieng cua control-plane
assert "vps_id" in local_deployments.c  # cot rieng cua Local Business DB
"""
    result = _run(code)
    assert result.returncode == 0, result.stderr


def test_user_sessions_table_carried_over_from_infra_supabase_only():
    """Regression test: bang nay chi co o infra/supabase/migrations/... (bi
    thieu o deploy/central_vps/init_central_postgres.sql) — phai duoc mang
    sang baseline moi, khong bi mat khi hop nhat."""
    code = """
from platform_core.control_plane.db import ControlPlaneBase
import platform_core.control_plane.models  # noqa: F401
from sqlalchemy import BigInteger

tables = ControlPlaneBase.metadata.tables
sessions = tables["control_plane.user_sessions"]
assert isinstance(sessions.c.id.type, BigInteger)
assert isinstance(sessions.c.user_id.type, BigInteger)
assert "refresh_token_hash" in sessions.c
assert "device_info" in sessions.c
"""
    result = _run(code)
    assert result.returncode == 0, result.stderr







