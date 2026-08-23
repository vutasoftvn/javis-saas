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
