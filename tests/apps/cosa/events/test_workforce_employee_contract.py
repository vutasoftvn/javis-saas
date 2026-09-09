from __future__ import annotations

from apps.cosa.events.workforce_employee_contract import (
    WORK_PACKAGE_QUEUED_EVENT,
    WORK_PACKAGE_REASSIGN_EVENT,
    WorkPackageDispatch,
    adapt_work_package_dispatch,
    is_workforce_dispatch_event,
)


def _valid_payload() -> dict[str, object]:
    return {
        "workspace_id": "ws_1",
        "work_package_id": "wp_1",
        "work_attempt_id": "wa_1",
        "agent_instance_id": "emp_1",
        "assignment_id": "as_1",
        "effective_priority": "P1",
        "correlation_id": "corr_1",
        "expected_capability_refs": ["operations.task.read"],
    }


def test_rejects_missing_or_mismatched_workforce_attribution() -> None:
    dispatch, error = adapt_work_package_dispatch({"work_package_id": "wp_1"})
    assert dispatch is None
    assert error == "missing_workforce_attribution"

    for key in (
        "workspace_id",
        "work_attempt_id",
        "agent_instance_id",
        "assignment_id",
    ):
        payload = _valid_payload()
        payload.pop(key)
        d, e = adapt_work_package_dispatch(payload)
        assert d is None
        assert e == "missing_workforce_attribution"


def test_rejects_invalid_priority_and_missing_correlation() -> None:
    bad_prio = _valid_payload()
    bad_prio["effective_priority"] = "URGENT"
    d, e = adapt_work_package_dispatch(bad_prio)
    assert d is None and e == "invalid_effective_priority"

    no_corr = _valid_payload()
    no_corr.pop("correlation_id")
    d, e = adapt_work_package_dispatch(no_corr)
    assert d is None and e == "missing_correlation_id"


def test_happy_path_returns_pinned_attribution() -> None:
    dispatch, error = adapt_work_package_dispatch(
        _valid_payload(), event_type=WORK_PACKAGE_QUEUED_EVENT
    )
    assert error is None
    assert isinstance(dispatch, WorkPackageDispatch)
    assert dispatch.work_package_id == "wp_1"
    assert dispatch.work_attempt_id == "wa_1"
    assert dispatch.agent_instance_id == "emp_1"
    assert dispatch.assignment_id == "as_1"
    assert dispatch.effective_priority == "P1"
    assert dispatch.expected_capability_refs == ("operations.task.read",)
    assert dispatch.is_reassignment is False


def test_reassignment_event_is_flagged() -> None:
    dispatch, error = adapt_work_package_dispatch(
        _valid_payload(), event_type=WORK_PACKAGE_REASSIGN_EVENT
    )
    assert error is None
    assert dispatch is not None
    assert dispatch.is_reassignment is True


def test_event_type_recognition() -> None:
    assert is_workforce_dispatch_event(WORK_PACKAGE_QUEUED_EVENT)
    assert is_workforce_dispatch_event(WORK_PACKAGE_REASSIGN_EVENT)
    assert not is_workforce_dispatch_event("operations.task.created.v1")
