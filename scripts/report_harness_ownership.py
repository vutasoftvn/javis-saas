"""Generate an evidence-only import-consumer report for frozen Harness candidates."""

from __future__ import annotations

import argparse
import ast
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

def _iter_python_files(repository_root: Path):
    excluded = {".git", ".worktrees", "__pycache__", ".venv", "node_modules", ".dart_tool"}
    for path in repository_root.rglob("*.py"):
        relative_path = path.relative_to(repository_root)
        if any(part in excluded for part in relative_path.parts):
            continue
        yield path


def _imported_modules(source: str) -> list[tuple[str, int]]:
    modules: list[tuple[str, int]] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.append((node.module, node.lineno))
        elif isinstance(node, ast.Import):
            modules.extend((alias.name, node.lineno) for alias in node.names)
    return modules


def _classification(relative_path: Path) -> str:
    normalized = relative_path.as_posix()
    if "/tests/" in f"/{normalized}" or normalized.startswith("backend/app/tests/"):
        return "test-only consumer"
    if normalized.startswith(("backend/app/", "services/")):
        return "production consumer"
    if normalized.startswith(("backend/agent_runtime/", "backend/tools/", "backend/skills/", "backend/workflows/", "backend/executors/")):
        return "internal scaffold consumer"
    return "unresolved consumer"


def _matches(candidate_imports: tuple[str, ...], imported_module: str) -> bool:
    return any(
        imported_module == prefix.rstrip(".") or imported_module.startswith(prefix)
        for prefix in candidate_imports
    )


def _is_shadowed_by_local_module(path: Path, imported_module: str) -> bool:
    """Return true when a top-level import resolves to a sibling module first."""
    top_level = imported_module.split(".", 1)[0]
    return (path.parent / f"{top_level}.py").is_file() or (path.parent / top_level / "__init__.py").is_file()


def collect_consumers(repository_root: Path) -> dict[str, list[tuple[Path, tuple[str, int]]]]:
    """Scan repository_root for imports of each frozen candidate. Returns
    {candidate: [(relative_path, (module, line)), ...]}. No file I/O beyond
    reading source files -- callers decide what to do with the result."""
    repository_root = repository_root.resolve()
    consumers: dict[str, list[tuple[Path, tuple[str, int]]]] = {
        candidate: [] for candidate in FROZEN_CANDIDATES
    }

    for path in _iter_python_files(repository_root):
        relative_path = path.relative_to(repository_root)
        if relative_path.as_posix().startswith("scripts/"):
            continue
        imports = _imported_modules(path.read_text(encoding="utf-8"))
        for candidate, prefixes in FROZEN_CANDIDATES.items():
            for imported_module, line in imports:
                if _matches(prefixes, imported_module) and not _is_shadowed_by_local_module(path, imported_module):
                    consumers[candidate].append((relative_path, (imported_module, line)))

    return consumers


def build_harness_ownership_report(repository_root: Path, output_path: Path) -> Path:
    consumers = collect_consumers(repository_root)

    lines = [
        "# Harness Ownership Consumer Report",
        "",
        "This report is evidence for migration ordering. It does not authorize deletion.",
        "It resolves static Python imports with AST and ignores imports shadowed by a sibling module.",
        "Dynamic imports and unresolved runtime paths require separate manual review; an empty section is not deletion authority.",
        "",
    ]
    for candidate, entries in consumers.items():
        lines.extend([f"## {candidate}", "", "### Consumers", ""])
        if not entries:
            lines.extend(["- No direct Python import consumers found.", ""])
            continue
        for relative_path, (imported_module, line) in sorted(entries, key=lambda item: (item[0], item[1][1], item[1][0])):
            lines.append(
                f"- {_classification(relative_path)}: {relative_path.as_posix()}:{line} imports {imported_module}"
            )
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
