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


def test_metric_gte_is_not_evaluable_in_v1():
    r = evaluate_deterministic(
        _crit("metric_gte", {"key_result_id": "1", "threshold": 3}), _facts()
    )
    assert r.verdict is CriterionVerdict.UNCLEAR and "metric_gte_not_evaluable" in r.reason


def test_result_keeps_required_flag():
    r = evaluate_deterministic(_crit("artifact_exists", {}, required=False), _facts())
    assert r.required is False
