"""Test idempotence and lint-compatibility of generated MVP contracts."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_mvp_contracts_generator_is_idempotent() -> None:
    """Test that generating contracts twice produces identical outputs and ruff passes."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Copy generator script and surface manifest to temporary directory
        (tmp_path / "scripts").mkdir(parents=True)
        (tmp_path / "shared" / "contracts").mkdir(parents=True)
        shutil.copy(ROOT / "scripts" / "gen-mvp-contracts.mjs", tmp_path / "scripts")
        shutil.copy(ROOT / "shared" / "contracts" / "mvp-surface.json", tmp_path / "shared" / "contracts")

        # Run generator first time
        run1 = subprocess.run(
            ["node", str(tmp_path / "scripts" / "gen-mvp-contracts.mjs")],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
        )
        assert run1.returncode == 0

        py_path = tmp_path / "apps" / "cosa" / "api" / "mvp_contracts_generated.py"
        assert py_path.exists()
        content1 = py_path.read_text(encoding="utf-8")

        # Run generator second time
        run2 = subprocess.run(
            ["node", str(tmp_path / "scripts" / "gen-mvp-contracts.mjs")],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
        )
        assert run2.returncode == 0
        content2 = py_path.read_text(encoding="utf-8")
        assert content1 == content2, "Generator must be deterministic and idempotent"

        # Verify ruff check passes on generated Python code
        ruff_bin = ROOT / ".venv" / "bin" / "ruff"
        ruff_cmd = [str(ruff_bin) if ruff_bin.exists() else "ruff", "check", str(py_path)]
        ruff_res = subprocess.run(ruff_cmd, capture_output=True, text=True)
        assert ruff_res.returncode == 0, f"Generated Python failed ruff check:\n{ruff_res.stdout}\n{ruff_res.stderr}"
