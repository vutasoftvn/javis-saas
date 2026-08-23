from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from agentos.evals.runner import EvalSuiteResult

DEFAULT_REGRESSION_THRESHOLD = 0.05


class CategoryRegression(BaseModel):
    category: str
    baseline_score: float
    current_score: float
    delta: float


class RegressionReport(BaseModel):
    has_regression: bool
    regressions: list[CategoryRegression]
    missing_in_current: list[str]
    new_in_current: list[str]


def save_baseline(results: list[EvalSuiteResult], path: str | Path) -> None:
    """Ghi kết quả eval hiện tại thành baseline (blueprint §20.4-20.5, Phase 10c-2).

    Baseline lấy điểm trung bình theo category (1 category có thể có nhiều
    `EvalSuiteResult` — ví dụ nhiều test case skill khác nhau).
    """
    by_category: dict[str, list[float]] = {}
    for res in results:
        by_category.setdefault(res.category, []).append(res.score)

    baseline = {
        category: sum(scores) / len(scores)
        for category, scores in by_category.items()
    }

    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(baseline, indent=2, sort_keys=True), encoding="utf-8")


def load_baseline(path: str | Path) -> dict[str, float]:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def compare_to_baseline(
    results: list[EvalSuiteResult],
    path: str | Path,
    *,
    threshold: float = DEFAULT_REGRESSION_THRESHOLD,
) -> RegressionReport:
    """So sánh kết quả eval hiện tại với baseline đã lưu trước đó (Phase 10c-2).

    1 category bị coi là regression nếu điểm trung bình giảm nhiều hơn
    `threshold` so với baseline. Không tự động alert — caller (script/CI)
    tự quyết định làm gì với `RegressionReport` (raise, log, exit code, v.v.).
    """
    baseline = load_baseline(path)

    by_category: dict[str, list[float]] = {}
    for res in results:
        by_category.setdefault(res.category, []).append(res.score)
    current = {category: sum(scores) / len(scores) for category, scores in by_category.items()}

    regressions: list[CategoryRegression] = []
    for category, baseline_score in baseline.items():
        current_score = current.get(category)
        if current_score is None:
            continue
        delta = current_score - baseline_score
        if delta < -threshold:
            regressions.append(
                CategoryRegression(
                    category=category,
                    baseline_score=baseline_score,
                    current_score=current_score,
                    delta=delta,
                )
            )

    missing_in_current = sorted(set(baseline) - set(current))
    new_in_current = sorted(set(current) - set(baseline))

    return RegressionReport(
        has_regression=len(regressions) > 0,
        regressions=regressions,
        missing_in_current=missing_in_current,
        new_in_current=new_in_current,
    )
