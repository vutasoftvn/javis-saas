TRANSITIONS = {
    "OPEN": {"REVIEW"},
    "REVIEW": {"OPEN", "CLOSED"},
    "CLOSED": {"OPEN", "LOCKED"},
    "LOCKED": set(),
}


def transition_period(period, target_status: str, *, can_reopen_locked: bool = False):
    target = target_status.upper()
    if period.status == "LOCKED" and target == "OPEN" and can_reopen_locked:
        period.status = target
        return period
    if target not in TRANSITIONS.get(period.status, set()):
        if period.status == "LOCKED":
            raise PermissionError("LOCKED period requires explicit reopen authorization")
        raise ValueError(f"Invalid period transition: {period.status} -> {target}")
    period.status = target
    return period
