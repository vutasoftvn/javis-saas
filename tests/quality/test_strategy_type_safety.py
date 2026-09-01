from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
STRATEGY_SERVICES = (
    "assumption.service.ts",
    "decision-recording.service.ts",
    "discovery-signal.service.ts",
    "evidence-lifecycle.service.ts",
    "experiment-proposal.service.ts",
    "gate-evaluation.service.ts",
    "interview.service.ts",
    "pmf-scoreboard.service.ts",
    "stage-policy.service.ts",
)
EXPLICIT_ANY = re.compile(r"(?::\s*|\bas\s+|,\s*)\bany\b")


def test_refactored_strategy_services_do_not_use_explicit_any() -> None:
    service_dir = ROOT / "services/company/operations/strategy/services"
    violations = []

    for filename in STRATEGY_SERVICES:
        for line_number, line in enumerate((service_dir / filename).read_text().splitlines(), start=1):
            if EXPLICIT_ANY.search(line):
                violations.append(f"{filename}:{line_number}: {line.strip()}")

    assert not violations, "Explicit `any` is not allowed in refactored Strategy services:\n" + "\n".join(violations)
