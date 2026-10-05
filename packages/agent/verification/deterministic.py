"""Đánh giá tiêu chí tất định (predicate) của DoneCriteria v1."""

from __future__ import annotations

from typing import Any

from agent.verification.models import CriterionResult, CriterionVerdict, RunFacts

__all__ = ["evaluate_deterministic"]

_ARTIFACT_KINDS = ("assistant_output", "report", "table", "file_export")


def _result(criterion: dict[str, Any], verdict: CriterionVerdict, reason: str) -> CriterionResult:
    return CriterionResult(
        id=str(criterion["id"]),
        required=bool(criterion.get("required", True)),
        check="deterministic",
        verdict=verdict,
        reason=reason,
    )


def _artifact_exists(
    criterion: dict[str, Any], args: dict[str, Any], facts: RunFacts
) -> CriterionResult:
    kind = args.get("kind")
    needle = args.get("display_name_contains")
    if (kind is not None and kind not in _ARTIFACT_KINDS) or (
        needle is not None and not isinstance(needle, str)
    ):
        return _result(criterion, CriterionVerdict.UNCLEAR, "invalid_args")
    for artifact in facts.artifacts:
        if kind is not None and artifact.kind != kind:
            continue
        if needle is not None and needle.casefold() not in artifact.display_name.casefold():
            continue
        return _result(criterion, CriterionVerdict.PASS, "artifact_found")
    return _result(criterion, CriterionVerdict.FAIL, "artifact_not_found")


def _field_present(
    criterion: dict[str, Any], args: dict[str, Any], facts: RunFacts
) -> CriterionResult:
    path = args.get("path")
    if not isinstance(path, str) or not path.strip() or any(not p for p in path.split(".")):
        return _result(criterion, CriterionVerdict.UNCLEAR, "invalid_args")
    if facts.structured_output is None:
        return _result(criterion, CriterionVerdict.UNCLEAR, "output_not_structured")
    node: Any = facts.structured_output
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return _result(criterion, CriterionVerdict.FAIL, "field_missing")
        node = node[part]
    if node is None or (isinstance(node, (str, list, dict)) and len(node) == 0):
        return _result(criterion, CriterionVerdict.FAIL, "field_empty")
    return _result(criterion, CriterionVerdict.PASS, "field_present")


def evaluate_deterministic(criterion: dict[str, Any], facts: RunFacts) -> CriterionResult:
    predicate = criterion.get("predicate") or {}
    kind = predicate.get("kind")
    args = predicate.get("args")
    if not isinstance(args, dict):
        return _result(criterion, CriterionVerdict.UNCLEAR, "invalid_args")
    if kind == "artifact_exists":
        return _artifact_exists(criterion, args, facts)
    if kind == "field_present":
        return _field_present(criterion, args, facts)
    if kind == "metric_gte":
        # Giá trị KR chỉ đổi khi người check-in và worker chưa có capability đọc KR (v1).
        return _result(criterion, CriterionVerdict.UNCLEAR, "metric_gte_not_evaluable")
    return _result(criterion, CriterionVerdict.UNCLEAR, "unknown_predicate")
