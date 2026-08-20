#!/usr/bin/env python3
"""Check retirement readiness for COSA's frozen Harness scaffolds.

Backend legacy-consumer detection is delegated to
scripts/report_harness_ownership.py, the only script proven (via
backend/app/tests/test_harness_ownership_report.py) to scan the actual
frozen-candidate import patterns defined in
docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md. Do not reintroduce a
second, independently-maintained pattern list here -- the previous version
of this script checked for AgentEventRecord/AgentToolCall, which are
canonical production models, not legacy ones.
"""
import os
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_ownership_reporter(scripts_dir: Path):
    path = scripts_dir / "report_harness_ownership.py"
    spec = spec_from_file_location("report_harness_ownership", path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def scan_legacy_frontend(target_dir: str, legacy_patterns: list[str]) -> list[str]:
    violations = []
    for root, _, files in os.walk(target_dir):
        for file in files:
            if not file.endswith('.dart'):
                continue
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                for pattern in legacy_patterns:
                    if pattern in content:
                        violations.append(f"{path} contains legacy pattern: {pattern}")
    return violations


def check_retirement_readiness(repository_root: Path) -> list[str]:
    reporter = _load_ownership_reporter(repository_root / "scripts")
    report_path = reporter.build_harness_ownership_report(
        repository_root,
        repository_root / "docs/architecture/reports/harness-ownership.md",
    )
    report_text = report_path.read_text(encoding="utf-8")

    violations = [
        line for line in report_text.splitlines()
        if line.startswith("- production consumer:")
    ]

    frontend_dir = repository_root / "frontend/lib"
    legacy_frontend_patterns = [
        "package:javis/legacy/",
        "AgentReasoningRawWidget",
    ]
    if frontend_dir.exists():
        violations.extend(scan_legacy_frontend(str(frontend_dir), legacy_frontend_patterns))

    return violations


def main() -> int:
    print("Checking retirement readiness...")
    repository_root = Path(__file__).resolve().parents[1]
    violations = check_retirement_readiness(repository_root)

    if violations:
        print("Retirement blocked by remaining legacy consumers:")
        for v in violations:
            print(" -", v)
        return 1

    print("All clear! Ready for retirement phase.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
