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

