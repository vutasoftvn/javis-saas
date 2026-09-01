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

def test_claude_requires_encore_guardrails() -> None:
    claude = (ROOT / "CLAUDE.md").read_text()
    assert "## Encore Guardrails (BẮT BUỘC)" in claude
    assert "handler không truy cập DB/Drizzle/schema trực tiếp" in claude
    assert "migration release chỉ Expand" in claude
