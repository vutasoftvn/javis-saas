"""Đánh giá tiêu chí tất định (predicate) của DoneCriteria v1."""

from __future__ import annotations

from typing import Any

from agent.verification.models import CriterionResult, CriterionVerdict, RunFacts

__all__ = ["evaluate_deterministic"]

_ARTIFACT_KINDS = ("assistant_output", "report", "table", "file_export")


def _result(criterion: Any, verdict: CriterionVerdict, reason: str) -> CriterionResult:
    c: dict[str, Any] = criterion if isinstance(criterion, dict) else {}
    cid = c.get("id")
    return CriterionResult(
        id=cid if isinstance(cid, str) else "",
        required=bool(c.get("required", True)),
        check="deterministic",
        verdict=verdict,
        reason=reason,
    )


def _artifact_exists(
    criterion: dict[str, Any], args: dict[str, Any], facts: RunFacts
) -> CriterionResult:
    """Có artifact do công cụ của chính agent tạo ra (artifact output tự động của nền tảng
    không bao giờ được tính; việc loại trừ do `collect_run_facts` đảm nhiệm)."""
    kind = args.get("kind")
    needle = args.get("display_name_contains")
    if (kind is not None and (not isinstance(kind, str) or kind not in _ARTIFACT_KINDS)) or (
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
    # Chỉ đi qua dict; chỉ số list không được duyệt và khóa dict chứa dấu chấm không với tới được.
    for part in path.split("."):
        if isinstance(node, list):
            return _result(criterion, CriterionVerdict.UNCLEAR, "path_through_list_unsupported")
        if not isinstance(node, dict) or part not in node:
            return _result(criterion, CriterionVerdict.FAIL, "field_missing")
        node = node[part]
    if node is None or (isinstance(node, (str, list, dict)) and len(node) == 0):
        return _result(criterion, CriterionVerdict.FAIL, "field_empty")
    return _result(criterion, CriterionVerdict.PASS, "field_present")


def evaluate_deterministic(criterion: Any, facts: RunFacts) -> CriterionResult:
    """Không bao giờ ném lỗi: đầu vào sai dạng trả về UNCLEAR."""
    if not isinstance(criterion, dict):
        return _result(criterion, CriterionVerdict.UNCLEAR, "invalid_args")
    predicate = criterion.get("predicate")
    if not isinstance(predicate, dict):
        return _result(criterion, CriterionVerdict.UNCLEAR, "invalid_args")
    kind = predicate.get("kind")
    args = predicate.get("args")
    if not isinstance(kind, str):
        return _result(criterion, CriterionVerdict.UNCLEAR, "unknown_predicate")
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
