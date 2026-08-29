from __future__ import annotations

import time
from collections.abc import Callable, Coroutine
from typing import Any

from agent.evals.models import (
    EvalResult,
    EvalSuiteSummary,
    EvalTestCase,
)

__all__ = ["CanonicalEvalRunner"]


class CanonicalEvalRunner:
    """Runner thực thi 4 nhóm Evals chuẩn hoá theo Master Guide §33 & §43.11."""

    def __init__(self) -> None:
        self._test_cases: list[tuple[EvalTestCase, Callable[[], Coroutine[Any, Any, bool]]]] = []

    def register_case(
        self,
        case: EvalTestCase,
        test_fn: Callable[[], Coroutine[Any, Any, bool]],
    ) -> None:
        self._test_cases.append((case, test_fn))

    async def run_all(self) -> EvalSuiteSummary:
        results: list[EvalResult] = []
        category_totals: dict[str, int] = {}
        category_passed: dict[str, int] = {}

        for case, test_fn in self._test_cases:
            cat_name = case.category.value
            category_totals[cat_name] = category_totals.get(cat_name, 0) + 1

            start_t = time.perf_counter()
            passed = False
            err_msg = None
            try:
                passed = await test_fn()
            except Exception as exc:
                passed = False
                err_msg = str(exc)

            duration = (time.perf_counter() - start_t) * 1000.0

            if passed:
                category_passed[cat_name] = category_passed.get(cat_name, 0) + 1

            results.append(
                EvalResult(
                    case_id=case.id,
                    category=case.category,
                    passed=passed,
                    score=1.0 if passed else 0.0,
                    duration_ms=duration,
                    details=f"Test '{case.name}' completed with result: {'PASSED' if passed else 'FAILED'}",
                    error=err_msg,
                )
            )

        total = len(results)
        passed_count = sum(1 for r in results if r.passed)
        failed_count = total - passed_count
        pass_rate = (passed_count / total) if total > 0 else 1.0

        cat_scores = {}
        for cat, t in category_totals.items():
            p = category_passed.get(cat, 0)
            cat_scores[cat] = (p / t) if t > 0 else 1.0

        return EvalSuiteSummary(
            total_cases=total,
            passed_cases=passed_count,
            failed_cases=failed_count,
            pass_rate=pass_rate,
            category_scores=cat_scores,
            results=results,
        )
