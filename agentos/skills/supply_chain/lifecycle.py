from __future__ import annotations

from agentos.skills.manifest import SkillLifecycleStatus

_ALLOWED_TRANSITIONS: dict[SkillLifecycleStatus, frozenset[SkillLifecycleStatus]] = {
    SkillLifecycleStatus.DISCOVERED: frozenset({SkillLifecycleStatus.IMPORTED, SkillLifecycleStatus.REJECTED}),
    SkillLifecycleStatus.IMPORTED: frozenset({SkillLifecycleStatus.SCANNED, SkillLifecycleStatus.REJECTED}),
    SkillLifecycleStatus.SCANNED: frozenset(
        {SkillLifecycleStatus.VERIFIED, SkillLifecycleStatus.QUARANTINED, SkillLifecycleStatus.REJECTED}
    ),
    SkillLifecycleStatus.VERIFIED: frozenset({SkillLifecycleStatus.STAGED, SkillLifecycleStatus.REJECTED}),
    SkillLifecycleStatus.STAGED: frozenset({SkillLifecycleStatus.ACTIVE, SkillLifecycleStatus.REJECTED}),
    SkillLifecycleStatus.ACTIVE: frozenset({SkillLifecycleStatus.DEPRECATED, SkillLifecycleStatus.QUARANTINED}),
    SkillLifecycleStatus.DEPRECATED: frozenset(),
    SkillLifecycleStatus.QUARANTINED: frozenset({SkillLifecycleStatus.REJECTED}),
    SkillLifecycleStatus.REJECTED: frozenset(),
}


class InvalidSkillLifecycleTransition(Exception):
    def __init__(self, current: SkillLifecycleStatus, target: SkillLifecycleStatus) -> None:
        super().__init__(f"Cannot transition skill lifecycle from {current.value} to {target.value}")
        self.current = current
        self.target = target


def validate_transition(current: SkillLifecycleStatus, target: SkillLifecycleStatus) -> None:
    if target not in _ALLOWED_TRANSITIONS[current]:
        raise InvalidSkillLifecycleTransition(current, target)
