from __future__ import annotations

import enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class StepType(str, enum.Enum):
    TOOL_CALL = "tool_call"
    AGENT = "agent"
    DETERMINISTIC = "deterministic"
    APPROVAL_GATE = "approval_gate"


class WorkflowStepSpec(BaseModel):
    id: str
    name: Optional[str] = None
    type: StepType = StepType.TOOL_CALL
    tool: Optional[str] = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    on_failure: Optional[str] = None
    compensate_with: Optional[str] = None
    output_key: Optional[str] = None
    agent_key: Optional[str] = None
    goal_key: Optional[str] = None
    action: Optional[str] = None
    subject_key: Optional[str] = None
    permission_level: Optional[str] = None


class WorkflowSpec(BaseModel):
    id: str
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    steps: list[WorkflowStepSpec] = Field(default_factory=list)

    def get_step(self, step_id: str) -> Optional[WorkflowStepSpec]:
        for step in self.steps:
            if step.id == step_id:
                return step
        return None
