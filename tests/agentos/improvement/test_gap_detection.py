from agentos.improvement.gap_detection import CapabilityOutcome, GapDetector


def _outcomes(capability: str, *, successes: int, failures: int, eval_score: float) -> list[CapabilityOutcome]:
    return [
        CapabilityOutcome(capability=capability, succeeded=True, eval_score=eval_score) for _ in range(successes)
    ] + [
        CapabilityOutcome(capability=capability, succeeded=False, eval_score=eval_score) for _ in range(failures)
    ]


def test_detect_flags_capability_with_enough_failures_and_low_average_eval():
    detector = GapDetector(min_failures=3, eval_threshold=0.6)
    outcomes = _outcomes("marketing.keyword-clustering", successes=2, failures=8, eval_score=0.54)

    gaps = detector.detect(outcomes)

    assert len(gaps) == 1
    assert gaps[0].capability == "marketing.keyword-clustering"
    assert gaps[0].evidence.failed_tasks == 8
    assert gaps[0].evidence.average_eval == 0.54


def test_detect_ignores_capability_below_failure_threshold():
    detector = GapDetector(min_failures=3, eval_threshold=0.6)
    outcomes = _outcomes("sales.qualify-lead", successes=8, failures=2, eval_score=0.3)

    gaps = detector.detect(outcomes)

    assert gaps == []


def test_detect_ignores_capability_with_good_average_eval_despite_failures():
    detector = GapDetector(min_failures=3, eval_threshold=0.6)
    outcomes = _outcomes("sales.qualify-lead", successes=1, failures=5, eval_score=0.9)

    gaps = detector.detect(outcomes)

    assert gaps == []


def test_detect_handles_multiple_capabilities_independently():
    detector = GapDetector(min_failures=3, eval_threshold=0.6)
    outcomes = _outcomes("a", successes=0, failures=5, eval_score=0.2) + _outcomes(
        "b", successes=5, failures=0, eval_score=0.9
    )

    gaps = detector.detect(outcomes)

    assert [g.capability for g in gaps] == ["a"]
