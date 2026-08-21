"""Generate an evidence-only import-consumer report for the Agent(#1)/AgentRelation
identity fragmentation retired in COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md Quyết định 4.

Mirrors scripts/report_harness_ownership.py's AST-based, evidence-only philosophy,
extended to match specific imported NAMES (not just module paths) since Agent/Task/
TaskDependency/TaskSchedule all live in the same app.founder_os.tasks.models module,
and to flag raw ForeignKey("agents.id")/("agent_relations.id") string references that
a pure import-AST scan would miss (e.g. Chatbot.agent_id in
backend/app/integrations/channels/models.py never imports the Agent class).
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

# label -> list of (module, imported name) pairs that all count as evidence for
# that label. Multiple pairs cover known re-export paths (e.g. Agent is both
# defined in app.founder_os.tasks.models and re-exported via app.db.base's
# `from app.founder_os.tasks.models import Agent` into app.db.models's `import *`).
NAMED_IMPORT_CANDIDATES: dict[str, tuple[tuple[str, str], ...]] = {
    "Agent (backend/app/founder_os/tasks/models.py, table agents)": (
        ("app.founder_os.tasks.models", "Agent"),
        ("app.db.models", "Agent"),
        ("app.db.base", "Agent"),
    ),
    "AgentRelation (backend/app/platform/organization/models.py)": (
        ("app.platform.organization.models", "AgentRelation"),
    ),
}

# Raw FK-string needles: catches consumers that reference the table by name in a
# ForeignKey() literal without importing the ORM class at all.
RAW_FK_STRING_NEEDLES: dict[str, tuple[str, ...]] = {
    "agents.id (raw ForeignKey string)": ('ForeignKey("agents.id")', "ForeignKey('agents.id')"),
    "agent_relations.id (raw ForeignKey string)": (
        'ForeignKey("agent_relations.id")',
        "ForeignKey('agent_relations.id')",
    ),
}

_EXCLUDED_DIR_PARTS = {".git", ".worktrees", "__pycache__", ".venv", "node_modules", ".dart_tool"}


def _iter_python_files(repository_root: Path):
    for path in repository_root.rglob("*.py"):
        relative_path = path.relative_to(repository_root)
        if any(part in _EXCLUDED_DIR_PARTS for part in relative_path.parts):
            continue
        yield path


def _imported_names(source: str) -> list[tuple[str, str, int]]:
    """Return (module, imported_name, lineno) for every `from module import name`."""
    entries: list[tuple[str, str, int]] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                entries.append((node.module, alias.name, node.lineno))
    return entries


def collect_named_import_consumers(
    repository_root: Path,
) -> dict[str, list[tuple[Path, tuple[str, str, int]]]]:
    repository_root = repository_root.resolve()
    consumers: dict[str, list[tuple[Path, tuple[str, str, int]]]] = {
        label: [] for label in NAMED_IMPORT_CANDIDATES
    }
    for path in _iter_python_files(repository_root):
        relative_path = path.relative_to(repository_root)
        if relative_path.as_posix().startswith("scripts/"):
            continue
        try:
            imports = _imported_names(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for label, pairs in NAMED_IMPORT_CANDIDATES.items():
            for module, name, lineno in imports:
                if (module, name) in pairs:
                    consumers[label].append((relative_path, (module, name, lineno)))
    return consumers


def collect_raw_fk_string_consumers(repository_root: Path) -> dict[str, list[tuple[Path, int]]]:
    repository_root = repository_root.resolve()
    consumers: dict[str, list[tuple[Path, int]]] = {label: [] for label in RAW_FK_STRING_NEEDLES}
    for path in _iter_python_files(repository_root):
        relative_path = path.relative_to(repository_root)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for label, needles in RAW_FK_STRING_NEEDLES.items():
            for lineno, line in enumerate(lines, start=1):
                if any(needle in line for needle in needles):
                    consumers[label].append((relative_path, lineno))
    return consumers


def build_identity_consumer_report(repository_root: Path, output_path: Path) -> Path:
    named = collect_named_import_consumers(repository_root)
    raw = collect_raw_fk_string_consumers(repository_root)

    lines = [
        "# Identity Consumer Report (Agent / AgentRelation)",
        "",
        "This report is evidence for migration ordering. It does not authorize deletion.",
        "It resolves static Python imports with AST plus a literal ForeignKey() string",
        "scan for consumers that never import the ORM class. Dynamic imports, raw SQL,",
        "and Alembic migration text require separate manual review; an empty section",
        "is not deletion authority.",
        "",
    ]
    for label, entries in named.items():
        lines.extend([f"## {label} - named imports", "", "### Consumers", ""])
        if not entries:
            lines.extend(["- No direct Python import consumers found.", ""])
            continue
        for relative_path, (module, name, lineno) in sorted(
            entries, key=lambda item: (item[0], item[1][2])
        ):
            lines.append(f"- {relative_path.as_posix()}:{lineno} imports {name} from {module}")
        lines.append("")

    for label, entries in raw.items():
        lines.extend([f"## {label}", "", "### Occurrences", ""])
        if not entries:
            lines.extend(["- No raw ForeignKey string occurrences found.", ""])
            continue
        for relative_path, lineno in sorted(entries, key=lambda item: (item[0], item[1])):
            lines.append(f"- {relative_path.as_posix()}:{lineno}")
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_identity_consumer_report(Path(__file__).resolve().parents[1], args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
