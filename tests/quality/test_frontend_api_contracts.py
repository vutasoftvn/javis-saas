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


def test_checker_matches_dynamic_path_segment_against_enabled_template(tmp_path: Path) -> None:
    # Fix-round 1 (review "Needs fixes"): nội suy trong PATH (`$id`) không còn
    # nghĩa là "bỏ qua hoàn toàn" — phải quy về template `:id` rồi so khớp với
    # manifest, giống hệt cách manifest tự khai báo `:id`. `/operations/objectives/:id/progress`
    # GET là entry enabled thật — một call site dynamic khớp đúng shape này
    # phải PASS, không bị lờ đi và cũng không bị false-positive.
    source = tmp_path / "frontend/lib/dyn_ok.dart"
    source.parent.mkdir(parents=True)
    source.write_text("await ApiClient.get('/operations/objectives/$objId/progress');")
    result = run_checker(tmp_path)
    assert result.returncode == 0


def test_checker_catches_reintroduced_dynamic_vault_route(tmp_path: Path) -> None:
    # Ca cụ thể reviewer yêu cầu: nếu route đã bị Task 5 disable (vault.*)
    # quay lại dưới dạng call site DYNAMIC (`$id`) — style cực kỳ phổ biến
    # thực tế (workspace_id/id luôn là biến, hiếm khi hard-code) — checker vẫn
    # phải bắt được, không được báo "pass" vì lệnh gọi có nội suy.
    source = tmp_path / "frontend/lib/dyn_vault.dart"
    source.parent.mkdir(parents=True)
    source.write_text("await ApiClient.get('/agent/vault/documents/$id');")
    result = run_checker(tmp_path)
    assert result.returncode == 1
    assert "disabled_contract" in result.stderr


def test_checker_strips_query_before_deciding_dynamism(tmp_path: Path) -> None:
    # Brief Step 2: "query string bị bỏ trước match". Một call như
    # `/commercial/marketing-context?workspace_id=$id` có PATH hoàn toàn tĩnh
    # (khớp entry enabled thật) — nội suy chỉ nằm trong query, không được kéo
    # cả path vào diện "dynamic" rồi bỏ qua kiểm tra.
    source = tmp_path / "frontend/lib/query_dyn.dart"
    source.parent.mkdir(parents=True)
    source.write_text("await ApiClient.get('/commercial/marketing-context?workspace_id=$wsId');")
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


def _is_fully_wildcard_template(path: str) -> bool:
    return all(seg.startswith(":") for seg in path.split("/"))


def test_fully_wildcard_allowlist_entries_are_scoped_to_a_file() -> None:
    # Fix round 2 (review "Needs fixes"): một entry allowlist mà TOÀN BỘ
    # segment đều là wildcard (vd. `:path`, không có segment literal nào neo
    # path lại) không mang thông tin gì để phân biệt call site dự định với
    # BẤT KỲ lệnh gọi ApiClient.<method>('$bienBatKy') fully-dynamic một-segment
    # nào khác trong toàn bộ frontend/lib — `pathMatchesTemplate` chỉ so khớp
    # cấu trúc. Guard cấu trúc: mọi entry dạng này bắt buộc phải có `file` để
    # giới hạn phạm vi miễn trừ, nếu không checker sẽ fail-closed (bỏ qua
    # entry, không miễn trừ được gì) — nhưng để không ai vô tình thêm lại một
    # entry `:something` mới thiếu `file` (tưởng nó vẫn hoạt động), test này
    # chặn ngay ở allowlist thay vì chờ phát hiện qua hành vi runtime.
    entries = json.loads(ALLOWLIST.read_text())["entries"]
    fully_wildcard = [e for e in entries if _is_fully_wildcard_template(e["path"])]
    assert fully_wildcard, "cần ít nhất 1 entry toàn-wildcard thật (:path) để test có ý nghĩa"
    assert all("file" in e and e["file"] for e in fully_wildcard)


def test_wildcard_allowlist_entry_does_not_leak_to_an_unrelated_file(tmp_path: Path) -> None:
    # Ca cụ thể review round 2 yêu cầu: allowlist thật có entry `:path` (GET)
    # scoped cho frontend/lib/modules/organization/services/workspace_service.dart.
    # Một lệnh gọi fully-dynamic một-segment HOÀN TOÀN KHÔNG LIÊN QUAN, ở một
    # file khác, với một tên biến khác, KHÔNG được lọt qua chỉ vì nó khớp cấu
    # trúc (:path) — phải bị coi là unknown_literal_route như bất kỳ dynamic
    # route không xác định được nào khác.
    source = tmp_path / "frontend/lib/modules/unrelated/services/unrelated_service.dart"
    source.parent.mkdir(parents=True)
    source.write_text("await ApiClient.get('$totallyUnrelatedFullyDynamicRoute');")
    result = run_checker(tmp_path)
    assert result.returncode == 1
    assert "unknown_literal_route" in result.stderr


def test_wildcard_allowlist_entry_still_covers_its_real_scoped_file(tmp_path: Path) -> None:
    # Đối chứng: cùng shape (:path, GET) nhưng ĐÚNG file được scope trong
    # allowlist thật vẫn phải PASS — fix round 2 không được làm hỏng use case
    # hợp lệ ban đầu (WorkspaceService.getJson forward path caller-supplied).
    source = tmp_path / "frontend/lib/modules/organization/services/workspace_service.dart"
    source.parent.mkdir(parents=True)
    source.write_text("await ApiClient.get('$path${separator}workspace_id=$id');")
    result = run_checker(tmp_path)
    assert result.returncode == 0
