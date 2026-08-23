from __future__ import annotations

import enum

from agentos.core.model_provider import ModelResponse


class PlanAction(str, enum.Enum):
    CALL_TOOL = "CALL_TOOL"
    FINISH = "FINISH"


class Planner:
    """MVP planner: reactive, one decision per model turn (ReAct-style).
    Multi-step upfront planning (blueprint §3.1) is out of scope until a
    later phase.
    """

    def decide(self, response: ModelResponse) -> PlanAction:
        if response.tool_call is not None:
            return PlanAction.CALL_TOOL
        return PlanAction.FINISH
