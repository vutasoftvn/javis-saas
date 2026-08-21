from typing import Any

from app.workforce.agents.orchestration.mission_control_bus import mission_control_bus

__all__ = [
    "ChiefOfStaffOrchestrator",
    "ChiefOfStaffResult",
    "DelegatedTaskResult",
    "mission_control_bus",
]


def __getattr__(name: str) -> Any:
    if name in ("ChiefOfStaffOrchestrator", "ChiefOfStaffResult", "DelegatedTaskResult"):
        from app.workforce.agents.orchestration import chief_of_staff
        return getattr(chief_of_staff, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

