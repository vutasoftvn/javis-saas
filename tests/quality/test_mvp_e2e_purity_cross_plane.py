"""Purity check phải phủ file cross-plane mới, và bắt được mock nếu lỡ đưa vào."""

from __future__ import annotations

from pathlib import Path

from scripts.check_mvp_e2e_purity import (
    REQUIRED_MVP_E2E_FILES,
    check_file,
    run_check,
)

ROOT = Path(__file__).resolve().parents[2]


def test_cross_plane_smoke_is_required() -> None:
    # test_cross_plane_smoke.py nằm trong danh sách bắt buộc của release gate.
    assert "test_cross_plane_smoke.py" in REQUIRED_MVP_E2E_FILES


def test_cross_plane_tree_is_clean() -> None:
    # Không có vi phạm trên cây e2e sạch hiện tại (bao gồm scenarios/stack/seed).
    violations = run_check(target_dir=ROOT / "tests" / "e2e", required_files=None)
    assert violations == [], violations


def test_run_check_scans_scenario_files(tmp_path: Path) -> None:
    # run_check phải soi file trong scenarios/ (không chỉ test_mvp_*.py).
    scenarios = tmp_path / "scenarios"
    scenarios.mkdir()
    (scenarios / "x.py").write_text("from unittest.mock import Mock\n\nMock()\n")

    violations = run_check(target_dir=tmp_path, required_files=None)
    assert any("NO_MOCK_IMPORT" in v for v in violations), violations
    assert any("scenarios/x.py" in v for v in violations), violations


def test_run_check_scans_stack_and_seed_files(tmp_path: Path) -> None:
    for sub in ("stack", "seed"):
        d = tmp_path / sub
        d.mkdir()
        (d / "helper.py").write_text("from unittest.mock import MagicMock\n")

    violations = run_check(target_dir=tmp_path, required_files=None)
    assert any("stack/helper.py" in v for v in violations), violations
    assert any("seed/helper.py" in v for v in violations), violations


def test_run_check_skips_init_files(tmp_path: Path) -> None:
    scenarios = tmp_path / "scenarios"
    scenarios.mkdir()
    (scenarios / "__init__.py").write_text("from unittest.mock import Mock\n")

    violations = run_check(target_dir=tmp_path, required_files=None)
    assert violations == [], violations


def test_check_file_flags_mock_in_scenario(tmp_path: Path) -> None:
    bad = tmp_path / "auth_tenant_isolation.py"
    bad.write_text("from unittest.mock import Mock\n\ndef run(s, w):\n    Mock()\n")
    violations = check_file(bad, base_dir=tmp_path)
    assert any("NO_MOCK_IMPORT" in v for v in violations)


def test_missing_cross_plane_smoke_reported(tmp_path: Path) -> None:
    violations = run_check(target_dir=tmp_path, required_files=REQUIRED_MVP_E2E_FILES)
    assert any(
        "MISSING_REQUIRED_MVP_TEST" in v and "test_cross_plane_smoke.py" in v
        for v in violations
    ), violations
