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
