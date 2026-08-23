"""CI/manual eval regression check (Phase 10c-2, roadmap phase-10 acceptance).

Chạy lại eval suite hiện có (bắt đầu với 7 case skill routing thật của Strategy,
`agentos/evals/strategy/eval_cases.py` — case đầu tiên có sẵn theo đúng gợi ý
roadmap 10c "dùng lại eval case đã viết ở Phase 5b"), rồi so sánh với baseline
đã lưu. Không tự động alert — chỉ exit code khác 0 khi có regression, để CI
quyết định fail build hay không.

Usage:
    python -m agentos.evals.run_regression_check --save              # ghi baseline mới
    python -m agentos.evals.run_regression_check --check             # so sánh, exit 1 nếu regression
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agentos.evals.regression import compare_to_baseline, save_baseline
from agentos.evals.runner import EvalRunner
from agentos.evals.strategy.eval_cases import STRATEGY_EVAL_CASES, run_strategy_skill_eval
from agentos.skills.registry import SkillRegistry

DEFAULT_BASELINE_PATH = Path(__file__).resolve().parent / "baselines" / "latest.json"
_SKILLPACKS_ROOT = Path(__file__).resolve().parents[2] / "skillpacks"


def run_eval_suite() -> EvalRunner:
    runner = EvalRunner()

    skills = SkillRegistry()
    skills.discover(_SKILLPACKS_ROOT)
    for case in STRATEGY_EVAL_CASES:
        result = run_strategy_skill_eval(skills, case)
        runner.run_skill_eval(case.expected_skill_id, success=result.success)

    return runner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--save", action="store_true", help="Save current eval results as the new baseline.")
    group.add_argument("--check", action="store_true", help="Compare current eval results against the saved baseline.")
    parser.add_argument("--baseline-path", type=Path, default=DEFAULT_BASELINE_PATH)
    args = parser.parse_args(argv)

    runner = run_eval_suite()

    if args.save:
        save_baseline(runner.results, args.baseline_path)
        print(f"Baseline saved to {args.baseline_path} ({len(runner.results)} eval results).")
        return 0

    report = compare_to_baseline(runner.results, args.baseline_path)
    if report.has_regression:
        print("EVAL REGRESSION DETECTED:")
        for reg in report.regressions:
            print(f"  - {reg.category}: {reg.baseline_score:.3f} -> {reg.current_score:.3f} (delta {reg.delta:.3f})")
        return 1

    print(f"No regression. Categories checked: {[r.category for r in runner.results]}")
    if report.missing_in_current:
        print(f"  (note: categories in baseline but not run this time: {report.missing_in_current})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
