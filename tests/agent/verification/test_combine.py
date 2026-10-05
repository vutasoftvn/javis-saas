from agent.verification.combine import combine
from agent.verification.models import CriterionResult, CriterionVerdict, Verdict


def _r(verdict, *, required=True, cid="c"):
    return CriterionResult(id=cid, required=required, check="rubric", verdict=verdict, reason="r")


def test_all_required_pass_is_pass():
    assert combine([_r(CriterionVerdict.PASS), _r(CriterionVerdict.PASS)]) is Verdict.PASS


def test_required_fail_is_fail_even_with_unclear():
    assert combine([_r(CriterionVerdict.FAIL), _r(CriterionVerdict.UNCLEAR)]) is Verdict.FAIL


def test_required_unclear_without_fail_is_inconclusive():
    assert (
        combine([_r(CriterionVerdict.PASS), _r(CriterionVerdict.UNCLEAR)]) is Verdict.INCONCLUSIVE
    )


def test_optional_criteria_never_block():
    results = [
        _r(CriterionVerdict.PASS),
        _r(CriterionVerdict.FAIL, required=False),
        _r(CriterionVerdict.UNCLEAR, required=False),
    ]
    assert combine(results) is Verdict.PASS


def test_only_optional_criteria_is_pass():
    assert combine([_r(CriterionVerdict.FAIL, required=False)]) is Verdict.PASS


def test_empty_results_is_inconclusive():
    # Không có kết quả nào (vd. tiêu chí không đọc được) không được coi là đạt.
    assert combine([]) is Verdict.INCONCLUSIVE
