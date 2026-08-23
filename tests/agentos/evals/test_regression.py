from __future__ import annotations

from agentos.evals.regression import compare_to_baseline, save_baseline
from agentos.evals.runner import EvalSuiteResult


def test_compare_to_baseline_detects_no_regression_when_scores_match(tmp_path):
    path = tmp_path / "baseline.json"
    results = [EvalSuiteResult(category="skill", passed=True, score=0.9, details={})]
    save_baseline(results, path)

    report = compare_to_baseline(results, path)

    assert report.has_regression is False
    assert report.regressions == []


def test_compare_to_baseline_detects_regression_when_score_drops(tmp_path):
    path = tmp_path / "baseline.json"
    baseline_results = [EvalSuiteResult(category="tool", passed=True, score=0.9, details={})]
    save_baseline(baseline_results, path)

    worse_results = [EvalSuiteResult(category="tool", passed=False, score=0.5, details={})]
    report = compare_to_baseline(worse_results, path)

    assert report.has_regression is True
    assert len(report.regressions) == 1
    assert report.regressions[0].category == "tool"
    assert report.regressions[0].baseline_score == 0.9
    assert report.regressions[0].current_score == 0.5


def test_compare_to_baseline_ignores_drop_within_threshold(tmp_path):
    path = tmp_path / "baseline.json"
    save_baseline([EvalSuiteResult(category="agent", passed=True, score=0.90, details={})], path)

    report = compare_to_baseline(
        [EvalSuiteResult(category="agent", passed=True, score=0.87, details={})],
        path,
        threshold=0.05,
    )

    assert report.has_regression is False


def test_compare_to_baseline_reports_categories_missing_from_current_run(tmp_path):
    path = tmp_path / "baseline.json"
    save_baseline(
        [
            EvalSuiteResult(category="skill", passed=True, score=0.9, details={}),
            EvalSuiteResult(category="retrieval", passed=True, score=0.8, details={}),
        ],
        path,
    )

    report = compare_to_baseline([EvalSuiteResult(category="skill", passed=True, score=0.9, details={})], path)

    assert report.missing_in_current == ["retrieval"]
