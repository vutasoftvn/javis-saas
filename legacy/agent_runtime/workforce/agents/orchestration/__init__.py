from typing import Any

from workforce.agents.orchestration.mission_control_bus import mission_control_bus
from workforce.agents.orchestration.result import ChiefOfStaffResult, DelegatedTaskResult

__all__ = [
    "ChiefOfStaffResult",
    "DelegatedTaskResult",
    "mission_control_bus",
    "orchestrate_mission",
    "confirm_mission",
    "resume_mission",
]


def __getattr__(name: str) -> Any:
    if name in ("orchestrate_mission", "confirm_mission", "resume_mission"):
        from workforce.agents.orchestration import service
        return getattr(service, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")



