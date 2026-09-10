"""Test that all removed startup core legacy framework surfaces are completely eradicated."""

from __future__ import annotations

from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Forbidden tokens representing removed legacy frameworks, academy, realtime agent, etc.
FORBIDDEN_TOKENS = (
    "pestel",
    "swot",
    "tows",
    "pmf-scoreboard",
    "maturity-assessment",
    "realtime_agent",
)

EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "node_modules",
    ".encore",
    "build",
    "dist",
    "docs",
    "tests/quality/test_removed_startup_core_surfaces.py",
    "scripts",
}


def _should_check(p: Path) -> bool:
    rel_str = str(p.relative_to(REPO_ROOT))
    for exc in EXCLUDED_PARTS:
        if exc in rel_str:
            return False
    if p.suffix not in {".ts", ".py", ".dart", ".yaml", ".yml", ".json"}:
        return False
    # Only check active code trees
    if not (
        rel_str.startswith("services/")
        or rel_str.startswith("apps/")
        or rel_str.startswith("packages/")
        or rel_str.startswith("frontend/lib/")
    ):
        return False
    return True


def test_no_forbidden_legacy_surfaces_in_active_source():
    violations = []
    for path in REPO_ROOT.rglob("*"):
        if path.is_file() and _should_check(path):
            try:
                content = path.read_text(encoding="utf-8", errors="ignore").lower()
            except Exception:
                continue
            for token in FORBIDDEN_TOKENS:
                if token in content:
                    violations.append((str(path.relative_to(REPO_ROOT)), token))

    assert not violations, f"Found {len(violations)} forbidden legacy surface references: {violations[:10]}"
