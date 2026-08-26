from __future__ import annotations

from agent_core.evals.artifacts import EvalCaseResult, EvalRun
from agent_core.governance.contracts import PinnedSpecIdentity


def _target_ref() -> PinnedSpecIdentity:
    return PinnedSpecIdentity(spec_kind="agent", spec_id="cofounder", spec_version="17", definition_hash="a" * 64)


def test_eval_run_defaults_to_running_status_and_no_suite_ref():
    run = EvalRun(target_ref=_target_ref())

    assert run.status == "running"
    assert run.suite_ref is None
    assert run.pass_rate is None
    assert run.run_id.startswith("evalrun_")


def test_eval_run_accepts_optional_suite_ref():
    suite_ref = PinnedSpecIdentity(
        spec_kind="eval_suite", spec_id="cofounder-core", spec_version="24", definition_hash="b" * 64
    )

    run = EvalRun(target_ref=_target_ref(), suite_ref=suite_ref)

    assert run.suite_ref == suite_ref


def test_eval_run_two_instances_get_distinct_run_ids():
    a = EvalRun(target_ref=_target_ref())
    b = EvalRun(target_ref=_target_ref())

    assert a.run_id != b.run_id


def test_eval_case_result_holds_run_and_case_reference():
    result = EvalCaseResult(eval_run_id="evalrun_abc123", case_id="case_1", passed=True, score=1.0)

    assert result.eval_run_id == "evalrun_abc123"
    assert result.case_id == "case_1"
    assert result.passed is True
    assert result.result_id.startswith("evalresult_")


def test_eval_case_result_defaults_error_to_none():
    result = EvalCaseResult(eval_run_id="evalrun_abc123", case_id="case_1", passed=False, score=0.0)

    assert result.error is None
