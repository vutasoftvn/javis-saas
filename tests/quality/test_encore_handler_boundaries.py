from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/check_encore_handler_boundaries.mjs"

def test_checker_rejects_a_new_handler_db_import(tmp_path: Path) -> None:
    handler = tmp_path / "services/company/operations/handlers/new.handler.ts"
    handler.parent.mkdir(parents=True)
    handler.write_text('import { db } from "../models/db";\n')
    baseline = tmp_path / "baseline.json"
    baseline.write_text('{"version": 1, "entries": []}')
    result = subprocess.run(
        ["node", str(SCRIPT), "--root", str(tmp_path), "--baseline", str(baseline)],
        text=True, capture_output=True,
    )
    assert result.returncode == 1
    assert "HANDLER_DIRECT_DB" in result.stderr


def test_checker_rejects_a_multiline_handler_db_import(tmp_path: Path) -> None:
    handler = tmp_path / "services/company/operations/handlers/new.handler.ts"
    handler.parent.mkdir(parents=True)
    handler.write_text('import {\n  db,\n} from "../models/db";\n')
    baseline = tmp_path / "baseline.json"
    baseline.write_text('{"version": 1, "entries": []}')

    result = subprocess.run(
        ["node", str(SCRIPT), "--root", str(tmp_path), "--baseline", str(baseline)],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "HANDLER_DIRECT_DB" in result.stderr
    assert "../models/db" in result.stderr


def test_checker_rejects_a_dynamic_handler_db_import(tmp_path: Path) -> None:
    handler = tmp_path / "services/cosa/handlers/new.handler.ts"
    handler.parent.mkdir(parents=True)
    handler.write_text('export const loadDb = () => import("../models/db");\n')
    baseline = tmp_path / "baseline.json"
    baseline.write_text('{"version": 1, "entries": []}')

    result = subprocess.run(
        ["node", str(SCRIPT), "--root", str(tmp_path), "--baseline", str(baseline)],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "HANDLER_DIRECT_DB" in result.stderr
    assert "../models/db" in result.stderr


def test_checker_rejects_a_template_literal_require_db_import(tmp_path: Path) -> None:
    handler = tmp_path / "services/cosa/handlers/new.handler.ts"
    handler.parent.mkdir(parents=True)
    handler.write_text('export const loadDb = () => require(`../models/db`);\n')
    baseline = tmp_path / "baseline.json"
    baseline.write_text('{"version": 1, "entries": []}')

    result = subprocess.run(
        ["node", str(SCRIPT), "--root", str(tmp_path), "--baseline", str(baseline)],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "HANDLER_DIRECT_DB" in result.stderr
    assert "../models/db" in result.stderr


def test_checker_rejects_a_stale_or_mislocated_baseline_entry(tmp_path: Path) -> None:
    handler = tmp_path / "services/company/operations/handlers/new.handler.ts"
    handler.parent.mkdir(parents=True)
    handler.write_text('import { db } from "../models/db";\n')
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        '{"version": 1, "entries": ['
        '"services/company/operations/handlers/new.handler.ts:2:HANDLER_DIRECT_DB:../models/db"'
        ']}'
    )

    result = subprocess.run(
        ["node", str(SCRIPT), "--root", str(tmp_path), "--baseline", str(baseline)],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "New Encore Handler DB Boundary Violations" in result.stderr
    assert "Stale baseline entries" in result.stderr


def test_boundaries_ci_installs_checker_runtimes() -> None:
    workflow = (ROOT / ".github/workflows/quality.yml").read_text()
    boundaries = workflow.split("  boundaries:\n", 1)[1].split("\n  e2e-golden-path:", 1)[0]

    assert "- run: npm ci\n        working-directory: services/company" in boundaries
    assert "- run: pip install pytest" in boundaries


def test_claude_requires_encore_guardrails() -> None:
    claude = (ROOT / "CLAUDE.md").read_text()
    assert "## Encore Guardrails (BẮT BUỘC)" in claude
    assert "handler không truy cập DB/Drizzle/schema trực tiếp" in claude
    assert "migration release chỉ Expand" in claude
