from pathlib import Path
import subprocess


def test_frontend_coverage_make_target_generates_coverage_before_evaluating():
    repo_root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        ["make", "--dry-run", "frontend-coverage-check"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "cd frontend && flutter test --coverage" in result.stdout
    assert (
        "node scripts/check_frontend_coverage.mjs "
        "frontend/coverage/lcov.info --minimum=46"
    ) in result.stdout
