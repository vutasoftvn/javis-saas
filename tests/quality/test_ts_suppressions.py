from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/check_ts_suppressions.mjs"


def test_checker_rejects_new_ts_ignore(tmp_path: Path) -> None:
    f = tmp_path / "services/company/x/y.ts"
    f.parent.mkdir(parents=True)
    f.write_text("// @ts-ignore\nconst x: number = 'oops';\n")
    baseline = tmp_path / "baseline.json"
    baseline.write_text('{"version": 1, "entries": []}')
    result = subprocess.run(
        ["node", str(SCRIPT), "--root", str(tmp_path), "--baseline", str(baseline)],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert "TS_SUPPRESSION" in result.stderr
    assert "@ts-ignore" in result.stderr


def test_checker_rejects_new_ts_expect_error(tmp_path: Path) -> None:
    f = tmp_path / "services/cosa/x/y.ts"
    f.parent.mkdir(parents=True)
    f.write_text("  // @ts-expect-error - temporary\nconst x: number = 'oops';\n")
    baseline = tmp_path / "baseline.json"
    baseline.write_text('{"version": 1, "entries": []}')
    result = subprocess.run(
        ["node", str(SCRIPT), "--root", str(tmp_path), "--baseline", str(baseline)],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert "TS_SUPPRESSION" in result.stderr
    assert "@ts-expect-error" in result.stderr


def test_checker_ignores_explanatory_comments(tmp_path: Path) -> None:
    f = tmp_path / "services/company/x/y.ts"
    f.parent.mkdir(parents=True)
    f.write_text("// This function was refactored to not use @ts-ignore anymore.\nconst x: number = 42;\n")
    baseline = tmp_path / "baseline.json"
    baseline.write_text('{"version": 1, "entries": []}')
    result = subprocess.run(
        ["node", str(SCRIPT), "--root", str(tmp_path), "--baseline", str(baseline)],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr


def test_checker_rejects_stale_baseline_entry(tmp_path: Path) -> None:
    f = tmp_path / "services/company/x/y.ts"
    f.parent.mkdir(parents=True)
    f.write_text("const x: number = 42;\n")
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        '{"version": 1, "entries": ["services/company/x/y.ts:1:TS_SUPPRESSION:@ts-ignore"]}'
    )
    result = subprocess.run(
        ["node", str(SCRIPT), "--root", str(tmp_path), "--baseline", str(baseline)],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert "Stale baseline entries" in result.stderr


def test_no_ts_suppressions_in_repo_after_task1() -> None:
    result = subprocess.run(
        [
            "node",
            str(SCRIPT),
            "--root",
            ".",
            "--baseline",
            "scripts/ts-suppression-baseline.json",
        ],
        text=True,
        capture_output=True,
        cwd=str(ROOT),
    )
    assert result.returncode == 0, result.stderr
