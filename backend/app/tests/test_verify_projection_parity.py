import subprocess
import sys
from pathlib import Path


def test_verify_projection_parity_fails_loudly_instead_of_faking_success():
    """
    Regression test: verify_projection_parity.py used to print hardcoded
    "Legacy run count: 1000 | Canonical run count: 1000" / "MATCHED" /
    "Parity verification passed" without ever touching a database, and
    exited 0. docs/architecture/COSA_PHASE8_RETIREMENT_COMPLETION.md cited
    this fabricated output as evidence of "100% projection parity".
    """
    repository_root = Path(__file__).resolve().parents[3]
    script_path = repository_root / "scripts" / "verify_projection_parity.py"

    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "NOT IMPLEMENTED" in result.stderr
    assert "passed" not in result.stdout.lower()
    assert "matched" not in result.stdout.lower()
