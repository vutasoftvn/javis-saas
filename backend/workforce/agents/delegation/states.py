from workforce.agents.delegation.types import DelegationStatus


_DELEGATION_TERMINAL = {
    DelegationStatus.DENIED.value,
    DelegationStatus.SUCCEEDED.value,
    DelegationStatus.FAILED.value,
    DelegationStatus.CANCELLED.value,
}

_DELEGATION_TRANSITIONS = {
    DelegationStatus.QUEUED.value: {
        DelegationStatus.WAITING_APPROVAL.value,
        DelegationStatus.DENIED.value,
        DelegationStatus.CLAIMED.value,
        DelegationStatus.CANCEL_REQUESTED.value,
    },
    DelegationStatus.WAITING_APPROVAL.value: {
        DelegationStatus.QUEUED.value,
        DelegationStatus.DENIED.value,
        DelegationStatus.CANCEL_REQUESTED.value,
    },
    DelegationStatus.CLAIMED.value: {
        DelegationStatus.DISPATCHING.value,
        DelegationStatus.RETRY_SCHEDULED.value,
        DelegationStatus.FAILED.value,
        DelegationStatus.CANCEL_REQUESTED.value,
    },
    DelegationStatus.DISPATCHING.value: {
        DelegationStatus.RUNNING.value,
        DelegationStatus.SUCCEEDED.value,
        DelegationStatus.RETRY_SCHEDULED.value,
        DelegationStatus.FAILED.value,
        DelegationStatus.CANCEL_REQUESTED.value,
    },
    DelegationStatus.RUNNING.value: {
        DelegationStatus.SUCCEEDED.value,
        DelegationStatus.RETRY_SCHEDULED.value,
        DelegationStatus.FAILED.value,
        DelegationStatus.CANCEL_REQUESTED.value,
    },
    DelegationStatus.RETRY_SCHEDULED.value: {
        DelegationStatus.QUEUED.value,
        DelegationStatus.FAILED.value,
        DelegationStatus.CANCEL_REQUESTED.value,
    },
    DelegationStatus.CANCEL_REQUESTED.value: {
        DelegationStatus.CANCELLED.value,
        DelegationStatus.FAILED.value,
    },
}

_STEP_TERMINAL = {"completed", "failed", "cancelled", "skipped"}

_STEP_TRANSITIONS = {
    "pending": {"waiting_approval", "running", "failed", "cancelled", "skipped"},
    "waiting_approval": {"pending", "running", "failed", "cancelled"},
    "running": {"completed", "failed", "cancelled"},
}


def _transition(
    current: str,
    target: str,
    *,
    terminal: set[str],
    transitions: dict[str, set[str]],
    entity: str,
) -> str:
    if current == target:
        return target
    if current in terminal:
        raise ValueError(f"{entity} state '{current}' is terminal")
    if target not in transitions.get(current, set()):
        raise ValueError(f"Invalid {entity} transition: {current} -> {target}")
    return target


def transition_delegation(current: str, target: str) -> str:
    return _transition(
        current,
        target,
        terminal=_DELEGATION_TERMINAL,
        transitions=_DELEGATION_TRANSITIONS,
        entity="delegation",
    )


def transition_step(current: str, target: str) -> str:
    return _transition(
        current,
        target,
        terminal=_STEP_TERMINAL,
        transitions=_STEP_TRANSITIONS,
        entity="step",
    )
