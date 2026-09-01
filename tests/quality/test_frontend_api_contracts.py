"""Quality gate: chặn literal route trong frontend/lib lệch khỏi
shared/contracts/mvp-surface.json (Task 7 — ngăn route literal drift).

Checker thật nằm ở scripts/check_frontend_api_contracts.mjs (Node, không phải
Python) — test này chỉ verify hành vi CLI (exit code + thông điệp stderr) và
tính hợp lệ của allowlist, không re-implement matcher bằng Python.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check_frontend_api_contracts.mjs"
MANIFEST = ROOT / "shared" / "contracts" / "mvp-surface.json"
ALLOWLIST = ROOT / "scripts" / "frontend-api-contract-allowlist.json"


def run_checker(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            "node",
            str(SCRIPT),
            "--root",
            str(root),
            "--manifest",
            str(MANIFEST),
            "--allowlist",
            str(ALLOWLIST),
        ],
        text=True,
        capture_output=True,
    )


def test_checker_rejects_unknown_api_client_literal(tmp_path: Path) -> None:
    source = tmp_path / "frontend/lib/x.dart"
    source.parent.mkdir(parents=True)
    source.write_text("await ApiClient.get('/agent/not-a-contract');")
    result = run_checker(tmp_path)
    assert result.returncode == 1
    assert "unknown_literal_route" in result.stderr


def test_checker_accepts_known_enabled_contract_literal(tmp_path: Path) -> None:
    # `/commercial/marketing-context` GET là entry enabled thật trong manifest —
    # dùng để verify checker không false-positive trên route hợp lệ.
    source = tmp_path / "frontend/lib/y.dart"
    source.parent.mkdir(parents=True)
    source.write_text("await ApiClient.get('/commercial/marketing-context');")
    result = run_checker(tmp_path)
    assert result.returncode == 0


def test_checker_flags_disabled_contract_literal_separately(tmp_path: Path) -> None:
    # Task 5 đã disable 8 entry vault.* (enabled: false) — literal khớp path
    # nhưng contract bị tắt phải là 'disabled_contract', không phải
    # 'unknown_literal_route' (khác nguyên nhân, khác hành động sửa).
    source = tmp_path / "frontend/lib/z.dart"
    source.parent.mkdir(parents=True)
    source.write_text("await ApiClient.get('/agent/vault/documents');")
    result = run_checker(tmp_path)
    assert result.returncode == 1
    assert "disabled_contract" in result.stderr
    assert "unknown_literal_route" not in result.stderr


def test_checker_skips_dynamic_interpolated_literal(tmp_path: Path) -> None:
    # Chuỗi có nội suy `$var` không phải literal thuần — ngoài phạm vi checker
    # (phải refactor về MvpEndpoint hoặc allowlist riêng nếu thật sự cần).
    # Lưu ý: dùng đúng cú pháp nội suy Dart `$id` (không có backslash) — `\$id`
    # trong Dart là dollar đã escape, tức literal thuần, không phải nội suy.
    source = tmp_path / "frontend/lib/w.dart"
    source.parent.mkdir(parents=True)
    source.write_text("await ApiClient.get('/agent/vault/documents/$id');")
    result = run_checker(tmp_path)
    assert result.returncode == 0


def test_checker_skips_comments(tmp_path: Path) -> None:
    source = tmp_path / "frontend/lib/c.dart"
    source.parent.mkdir(parents=True)
    source.write_text("// await ApiClient.get('/agent/not-a-contract');")
    result = run_checker(tmp_path)
    assert result.returncode == 0


def test_all_allowlist_entries_have_expiry_and_owner() -> None:
    entries = json.loads(ALLOWLIST.read_text())["entries"]
    assert entries, "allowlist phải có ít nhất metadata rỗng hợp lệ để test có ý nghĩa"
    assert all({"path", "owner", "reason", "expires_on"} <= entry.keys() for entry in entries)
