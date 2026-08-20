"""Generate an evidence-only import-consumer report for frozen Harness candidates."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

FROZEN_CANDIDATES: dict[str, tuple[str, ...]] = {
    "backend/agent_runtime/runtime": ("agent_runtime.runtime",),
    "backend/agent_runtime/models": ("agent_runtime.models",),
    "backend/agent_runtime/context": ("agent_runtime.context",),
    "backend/agent_runtime/routing": ("agent_runtime.routing",),
    "backend/agent_runtime/trajectory": ("agent_runtime.trajectory",),
    "backend/tools": ("tools.",),
    "backend/skills": ("skills.",),
    "backend/workflows": ("workflows.",),
    "backend/executors": ("executors.",),
}

IMPORT_PATTERN = re.compile(
    r"^\s*(?:from\s+(?P<from>[A-Za-z_][\w.]*)\s+import|import\s+(?P<imports>[^#]+))"
)


def _iter_python_files(repository_root: Path):
    excluded = {".git", ".worktrees", "__pycache__", ".venv", "node_modules", ".dart_tool"}
    for path in repository_root.rglob("*.py"):
        relative_path = path.relative_to(repository_root)
        if any(part in excluded for part in relative_path.parts):
            continue
        yield path


def _imported_modules(source: str) -> list[str]:
    modules: list[str] = []
    for line in source.splitlines():
        match = IMPORT_PATTERN.match(line)
        if not match:
            continue
        if match.group("from"):
            modules.append(match.group("from"))
            continue
        modules.extend(item.strip().split(" as ", 1)[0].strip() for item in match.group("imports").split(","))
    return modules


def _classification(relative_path: Path) -> str:
    normalized = relative_path.as_posix()
    if normalized.startswith("backend/app/tests/"):
        return "test-only consumer"
    if normalized.startswith("backend/app/"):
        return "production consumer"
    return "non-production consumer"


def _matches(candidate_imports: tuple[str, ...], imported_module: str) -> bool:
    return any(
        imported_module == prefix.rstrip(".") or imported_module.startswith(prefix)
        for prefix in candidate_imports
    )


def collect_consumers(repository_root: Path) -> dict[str, list[tuple[Path, str]]]:
    """Scan repository_root for imports of each frozen candidate. Returns
    {candidate: [(relative_path, imported_module), ...]}. No file I/O beyond
    reading source files -- callers decide what to do with the result."""
    repository_root = repository_root.resolve()
    consumers: dict[str, list[tuple[Path, str]]] = {candidate: [] for candidate in FROZEN_CANDIDATES}

    for path in _iter_python_files(repository_root):
        relative_path = path.relative_to(repository_root)
        if relative_path.as_posix().startswith("scripts/"):
            continue
        imports = _imported_modules(path.read_text(encoding="utf-8"))
        for candidate, prefixes in FROZEN_CANDIDATES.items():
            for imported_module in imports:
                if _matches(prefixes, imported_module):
                    consumers[candidate].append((relative_path, imported_module))

    return consumers


def build_harness_ownership_report(repository_root: Path, output_path: Path) -> Path:
    consumers = collect_consumers(repository_root)

    lines = [
        "# Harness Ownership Consumer Report",
        "",
        "This report is evidence for migration ordering. It does not authorize deletion.",
        "",
    ]
    for candidate, entries in consumers.items():
        lines.extend([f"## {candidate}", "", "### Consumers", ""])
        if not entries:
            lines.extend(["- No direct Python import consumers found.", ""])
            continue
        for relative_path, imported_module in sorted(entries):
            lines.append(f"- {_classification(relative_path)}: {relative_path.as_posix()} imports {imported_module}")
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_harness_ownership_report(Path(__file__).resolve().parents[1], args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
