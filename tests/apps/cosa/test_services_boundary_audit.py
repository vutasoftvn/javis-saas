from __future__ import annotations

import os
from pathlib import Path


def test_packages_agent_core_has_zero_imports_from_services_or_apps():
    """Boundary Audit: Đảm bảo packages/agent_core hoàn toàn độc lập,
    0 import từ services/* và 0 import từ apps/*.
    """
    agent_core_dir = Path(__file__).parents[3] / "packages" / "agent_core"
    assert agent_core_dir.exists(), f"Directory not found: {agent_core_dir}"

    forbidden_patterns = [
        "services.company",
        "services/",
        "apps.cosa",
        "apps/",
    ]

    violations = []
    for py_file in agent_core_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        for line_no, line in enumerate(content.splitlines(), start=1):
            line_str = line.strip()
            # Bỏ qua comment
            if line_str.startswith("#"):
                continue
            for pattern in forbidden_patterns:
                if f"import {pattern}" in line_str or f"from {pattern}" in line_str:
                    violations.append(f"{py_file.name}:{line_no} -> {line_str}")

    assert not violations, f"Architectural boundary violated! Found forbidden imports:\n" + "\n".join(violations)


def test_canonical_dirs_have_zero_imports_from_legacy_or_agentos():
    """Boundary Audit: packages/*, apps/*, services/* không được import từ
    `legacy` hoặc `agentos` (agentos đã archive vào legacy/agent_runtime_archive/).
    """
    repo_root = Path(__file__).parents[3]
    canonical_dirs = [repo_root / "packages", repo_root / "apps", repo_root / "services"]

    forbidden_patterns = ["legacy.", "legacy/", "agentos.", "agentos/"]

    violations = []
    for base_dir in canonical_dirs:
        if not base_dir.exists():
            continue
        for py_file in base_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for line_no, line in enumerate(content.splitlines(), start=1):
                line_str = line.strip()
                if line_str.startswith("#"):
                    continue
                for pattern in forbidden_patterns:
                    if f"import {pattern}" in line_str or f"from {pattern}" in line_str:
                        violations.append(f"{py_file}:{line_no} -> {line_str}")

    assert not violations, f"Canonical code imports from legacy/agentos:\n" + "\n".join(violations)


# Theo COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md §19.3: boundary
# check trước đây CHỈ scan Python import (2 test trên), không scan deployment
# config — docker-compose.yml mount `legacy/backend` thật cho 4 service
# (migrate/migrate-control-plane/brain-api/agent-worker), gated `--profile
# legacy`, nhưng không bị 2 test trên bắt được. Đây KHÔNG phải "0 legacy
# reference" (chưa cutover xong — xem Phase 8 trong tài liệu trên) mà là
# allowlist tường minh: catch reference MỚI/không ghi nhận, không catch những
# gì đã biết và đang chờ cutover có kiểm soát.
_DEPLOYMENT_LEGACY_ALLOWLIST: dict[str, int] = {
    "Makefile": 2,  # comment ghi chú agentos đã archive — không phải dependency thật
    "docker-compose.yml": 22,  # 4 service --profile legacy + 1 khối comment giải thích (ADR-012) — chờ Phase 8
}


def test_deployment_configs_legacy_references_are_allowlisted():
    """Boundary Audit mở rộng — quét docker-compose*.yml/Dockerfile*/Makefile
    (không chỉ *.py) cho path `legacy/` — theo §19.3. FAIL nếu:
    (a) 1 file KHÔNG nằm trong allowlist có reference `legacy/`, hoặc
    (b) 1 file trong allowlist có SỐ reference khác con số đã ghi nhận (tăng
    lên = ai đó thêm dependency mới chưa qua review; giảm xuống = tài liệu
    này cần cập nhật lại con số, không phải lỗi thật — nhưng vẫn phải sửa
    tường minh, không âm thầm bỏ qua).

    Không dùng pattern `! rg ... path-có-thể-không-tồn-tại` (§19.4 anti-false-
    green) — glob rõ ràng, nếu 0 file khớp thì loop rỗng và mọi allowlist
    entry sẽ fail ở bước so khớp count (không âm thầm pass).
    """
    repo_root = Path(__file__).parents[3]
    candidate_globs = ["docker-compose*.yml", "Dockerfile*", "Makefile"]
    excluded_dir_parts = {"node_modules", "legacy", ".git", "agent_runtime_archive"}

    found_counts: dict[str, int] = {}
    for pattern in candidate_globs:
        for path in repo_root.rglob(pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(repo_root)
            if excluded_dir_parts & set(rel.parts[:-1]):
                continue
            content = path.read_text(encoding="utf-8")
            count = content.count("legacy/")
            if count > 0:
                found_counts[rel.as_posix()] = count

    violations = []
    for rel, count in found_counts.items():
        expected = _DEPLOYMENT_LEGACY_ALLOWLIST.get(rel)
        if expected is None:
            violations.append(f"{rel}: {count} reference(s) tới legacy/ — file KHÔNG có trong allowlist")
        elif expected != count:
            violations.append(
                f"{rel}: có {count} reference(s) tới legacy/, allowlist ghi nhận {expected} — "
                f"cập nhật _DEPLOYMENT_LEGACY_ALLOWLIST nếu thay đổi có chủ đích, không âm thầm bỏ qua"
            )
    for rel in _DEPLOYMENT_LEGACY_ALLOWLIST:
        if rel not in found_counts and (repo_root / rel).exists():
            violations.append(f"{rel}: allowlist ghi nhận có reference nhưng file hiện không còn — cập nhật allowlist")

    assert not violations, "Deployment config legacy reference drift:\n" + "\n".join(violations)
