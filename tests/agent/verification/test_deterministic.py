import pytest
from agent.verification.deterministic import evaluate_deterministic
from agent.verification.models import ArtifactFact, CriterionVerdict, RunFacts


def _facts(*, text="ket qua", structured=None, artifacts=()):
    return RunFacts(output_text=text, structured_output=structured, artifacts=tuple(artifacts))


def _crit(kind, args, *, required=True, cid="c1"):
    return {
        "id": cid,
        "description": "d",
        "required": required,
        "check": "deterministic",
        "predicate": {"kind": kind, "args": args},
    }


def test_artifact_exists_passes_on_matching_kind():
    facts = _facts(artifacts=[ArtifactFact("report", "WGA task output")])
    r = evaluate_deterministic(_crit("artifact_exists", {"kind": "report"}), facts)
    assert (
        r.verdict is CriterionVerdict.PASS
        and r.id == "c1"
        and r.required
        and r.check == "deterministic"
    )


def test_artifact_exists_fails_when_kind_missing():
    facts = _facts(artifacts=[ArtifactFact("report", "WGA task output")])
    r = evaluate_deterministic(_crit("artifact_exists", {"kind": "file_export"}), facts)
    assert r.verdict is CriterionVerdict.FAIL


def test_artifact_exists_display_name_contains_is_case_insensitive():
    facts = _facts(artifacts=[ArtifactFact("report", "Weekly REPORT.pdf")])
    r = evaluate_deterministic(
        _crit("artifact_exists", {"display_name_contains": "weekly report"}), facts
    )
    assert r.verdict is CriterionVerdict.PASS


def test_artifact_exists_with_no_args_needs_any_artifact():
    assert (
        evaluate_deterministic(_crit("artifact_exists", {}), _facts()).verdict
        is CriterionVerdict.FAIL
    )
    facts = _facts(artifacts=[ArtifactFact("table", "t")])
    assert (
        evaluate_deterministic(_crit("artifact_exists", {}), facts).verdict is CriterionVerdict.PASS
    )


def test_artifact_exists_rejects_bad_args_as_unclear():
    r = evaluate_deterministic(_crit("artifact_exists", {"kind": 5}), _facts())
    assert r.verdict is CriterionVerdict.UNCLEAR and "invalid_args" in r.reason


def test_field_present_walks_nested_path():
    facts = _facts(structured={"a": {"b": {"c": "x"}}})
    assert (
        evaluate_deterministic(_crit("field_present", {"path": "a.b.c"}), facts).verdict
        is CriterionVerdict.PASS
    )
    assert (
        evaluate_deterministic(_crit("field_present", {"path": "a.b.z"}), facts).verdict
        is CriterionVerdict.FAIL
    )


def test_field_present_empty_values_count_as_missing():
    facts = _facts(structured={"a": "", "b": [], "c": {}, "d": None, "e": 0, "f": False})
    for path in ("a", "b", "c", "d"):
        assert (
            evaluate_deterministic(_crit("field_present", {"path": path}), facts).verdict
            is CriterionVerdict.FAIL
        )
    for path in ("e", "f"):  # 0 và False là giá trị có thật
        assert (
            evaluate_deterministic(_crit("field_present", {"path": path}), facts).verdict
            is CriterionVerdict.PASS
        )


def test_field_present_needs_structured_output():
    r = evaluate_deterministic(_crit("field_present", {"path": "a"}), _facts(structured=None))
    assert r.verdict is CriterionVerdict.UNCLEAR and "output_not_structured" in r.reason


def test_field_present_invalid_path_is_unclear():
    r = evaluate_deterministic(_crit("field_present", {"path": ""}), _facts(structured={"a": 1}))
    assert r.verdict is CriterionVerdict.UNCLEAR and "invalid_args" in r.reason


def _mf(metrics, before=None):
    return RunFacts(
        output_text="x",
        structured_output=None,
        artifacts=(),
        metrics=metrics,
        metrics_before=before or {},
    )


def _metric(args, **kw):
    return _crit("metric_gte", args, **kw)


def test_metric_gte_passes_when_value_meets_threshold():
    r = evaluate_deterministic(_metric({"key_result_id": "7", "threshold": 3}), _mf({"7": 3.0}))
    assert r.verdict is CriterionVerdict.PASS


def test_metric_gte_fails_below_threshold():
    r = evaluate_deterministic(_metric({"key_result_id": "7", "threshold": 3}), _mf({"7": 2.9}))
    assert r.verdict is CriterionVerdict.FAIL and "metric_below_threshold" in r.reason


def test_metric_gte_unavailable_value_is_unclear():
    for facts in (_mf({}), _mf({"7": None})):
        r = evaluate_deterministic(_metric({"key_result_id": "7", "threshold": 3}), facts)
        assert r.verdict is CriterionVerdict.UNCLEAR and "metric_unavailable" in r.reason


@pytest.mark.parametrize(
    "args",
    [
        {"key_result_id": 7, "threshold": 3},
        {"key_result_id": "", "threshold": 3},
        {"key_result_id": "7"},
        {"key_result_id": "7", "threshold": "3"},
        {"key_result_id": "7", "threshold": float("inf")},
        {"key_result_id": "7", "threshold": True},
        {"key_result_id": "7", "threshold": 3, "must_change": "yes"},
    ],
)
def test_metric_gte_invalid_args_are_unclear(args):
    r = evaluate_deterministic(_metric(args), _mf({"7": 5.0}))
    assert r.verdict is CriterionVerdict.UNCLEAR and "invalid_args" in r.reason


def test_must_change_requires_baseline_and_a_difference():
    args = {"key_result_id": "7", "threshold": 3, "must_change": True}
    assert evaluate_deterministic(_metric(args), _mf({"7": 5.0})).reason.endswith(
        "baseline_unavailable"
    )
    unchanged = evaluate_deterministic(_metric(args), _mf({"7": 5.0}, {"7": 5.0}))
    assert unchanged.verdict is CriterionVerdict.FAIL and "metric_unchanged" in unchanged.reason
    changed = evaluate_deterministic(_metric(args), _mf({"7": 5.0}, {"7": 1.0}))
    assert changed.verdict is CriterionVerdict.PASS


def test_result_keeps_required_flag():
    r = evaluate_deterministic(_crit("artifact_exists", {}, required=False), _facts())
    assert r.required is False


@pytest.mark.parametrize(
    "crit",
    [
        None,
        "x",
        [1],
        {},
        {"predicate": [1]},
        {"id": "c", "predicate": [1]},
        {"id": "c", "predicate": "artifact_exists"},
        {"id": "c", "predicate": None},
        {"id": "c", "predicate": {"kind": ["a"], "args": {}}},
        {"id": "c", "predicate": {"kind": {"a": 1}, "args": {}}},
        {"id": "c", "predicate": {"kind": "artifact_exists", "args": [1]}},
        {"id": "c", "predicate": {"kind": "artifact_exists", "args": None}},
        {"id": "c", "predicate": {"kind": "artifact_exists"}},
        {"id": "c", "predicate": {"kind": "artifact_exists", "args": {"kind": ["x"]}}},
        {"id": 5, "predicate": {"kind": "nope", "args": {}}},
    ],
)
def test_malformed_criteria_never_raise_and_are_unclear(crit):
    r = evaluate_deterministic(crit, _facts(structured={"a": 1}))
    assert r.verdict is CriterionVerdict.UNCLEAR
    assert r.reason in {"invalid_args", "unknown_predicate"}
    assert isinstance(r.id, str)


def test_field_present_does_not_traverse_lists():
    facts = _facts(structured={"items": [{"x": 1}], "a.b": 1})
    r = evaluate_deterministic(_crit("field_present", {"path": "items.0.x"}), facts)
    assert r.verdict is CriterionVerdict.UNCLEAR and "path_through_list_unsupported" in r.reason
    assert (
        evaluate_deterministic(_crit("field_present", {"path": "items"}), facts).verdict
        is CriterionVerdict.PASS
    )
    # khóa dict chứa dấu chấm không với tới được
    assert (
        evaluate_deterministic(_crit("field_present", {"path": "a.b"}), facts).verdict
        is CriterionVerdict.FAIL
    )
