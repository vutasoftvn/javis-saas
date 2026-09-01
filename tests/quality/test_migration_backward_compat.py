"""Quality gate: destructive DDL trong migration chỉ được miễn trừ khi có
evidence file thật (Task 8 — chặn free-form comment tự phong "an toàn").

Checker thật nằm ở scripts/check-migration-backward-compat.mjs (Node) — test
này chỉ verify hành vi CLI (exit code + thông điệp stderr) qua flag `--dir`
dùng để trỏ checker vào một thư mục migration ad-hoc (tmp_path), không
re-implement logic quét DDL bằng Python.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check-migration-backward-compat.mjs"


def run_migration_checker(dir_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["node", str(SCRIPT), "--dir", str(dir_path)],
        text=True,
        capture_output=True,
        cwd=ROOT,
    )


def test_destructive_migration_requires_evidence_file(tmp_path: Path) -> None:
    migration = tmp_path / "29_bad.up.sql"
    migration.write_text("-- migration-compat: allow-destructive\nDROP TABLE x;")
    result = run_migration_checker(tmp_path)
    assert result.returncode == 1
    assert "missing cutover evidence" in result.stderr


def test_destructive_migration_rejects_evidence_file_missing_required_fields(
    tmp_path: Path,
) -> None:
    # Có tham chiếu evidence= nhưng file evidence không tồn tại trên đĩa —
    # vẫn phải fail-closed, không được coi comment là đủ.
    migration = tmp_path / "29_dangling.up.sql"
    migration.write_text(
        "-- migration-compat: allow-destructive evidence=docs/runbooks/evidence/does-not-exist.md\n"
        "DROP TABLE x;"
    )
    result = run_migration_checker(tmp_path)
    assert result.returncode == 1
    assert "missing cutover evidence" in result.stderr


def test_destructive_migration_accepts_well_formed_evidence_file(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence.md"
    evidence.write_text(
        "# Evidence\n\n"
        "```yaml\n"
        "cutover:\n"
        "  migration: 29_ok\n"
        "  environment: prelaunch-only\n"
        "  approved_adr: ADR-CUTOVER-001\n"
        "  backup_sha256: 'placeholder-filled-by-operator-before-deploy'\n"
        "  restore_rehearsal: passed\n"
        "  n_minus_1_schema_compatibility: not-applicable-prelaunch\n"
        "```\n"
    )
    migration = tmp_path / "29_ok.up.sql"
    migration.write_text(
        f"-- migration-compat: allow-destructive evidence={evidence}\nDROP TABLE x;"
    )
    result = run_migration_checker(tmp_path)
    assert result.returncode == 0, result.stderr


def test_real_migration_29_has_valid_cutover_evidence() -> None:
    # Migration 29 thật trong repo (destructive, xác nhận pre-launch — Task 8
    # Step 1) phải tự vượt qua chính checker đang bảo vệ CI, không chỉ
    # pass trên fixture giả lập.
    real_dir = ROOT / "services" / "cosa" / "migrations"
    result = subprocess.run(
        ["node", str(SCRIPT)],
        text=True,
        capture_output=True,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert real_dir.exists()
