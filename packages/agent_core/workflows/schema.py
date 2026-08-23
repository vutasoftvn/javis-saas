from __future__ import annotations

import enum
from typing import Any, Optional
from pydantic import BaseModel, Field

from agent_core.governance.contracts import PinnedSpecIdentity
from agent_core.governance.hashing import definition_hash

__all__ = ["StepType", "WorkflowStepSpec", "WorkflowSpec"]


class StepType(str, enum.Enum):
    TOOL_CALL = "tool_call"
    AGENT = "agent"
    DETERMINISTIC = "deterministic"
    APPROVAL_GATE = "approval_gate"
    PARALLEL = "parallel"
    RETRY = "retry"
    COMPENSATING = "compensating"


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
    autonomy_level: Optional[str] = None
    capability_risk: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowSpec(BaseModel):
    """Khai báo cấu trúc DAG Workflow bất biến theo Master Guide §6.2.
    
    Bổ sung các trường bắt buộc:
    - failure_policy & compensation_policy
    - input_schema & output_schema
    - definition_hash content-addressed
    """

    id: str
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    steps: list[WorkflowStepSpec] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    failure_policy: dict[str, Any] = Field(default_factory=dict)
    compensation_policy: dict[str, Any] = Field(default_factory=dict)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    definition_hash: Optional[str] = None

    def get_step(self, step_id: str) -> Optional[WorkflowStepSpec]:
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def compute_hash(self) -> str:
        """Tính SHA-256 hash chuẩn hoá cho toàn bộ nội dung của WorkflowSpec."""
        data = self.model_dump(exclude={"definition_hash"})
        return definition_hash(data)

    def with_hash(self) -> "WorkflowSpec":
        """Trả về bản sao WorkflowSpec đã được gắn definition_hash xác thực."""
        return self.model_copy(update={"definition_hash": self.compute_hash()})

    def to_pinned_identity(self) -> PinnedSpecIdentity:
        """Chuyển đổi sang PinnedSpecIdentity để gắn kết bất biến vào Run."""
        h = self.definition_hash or self.compute_hash()
        return PinnedSpecIdentity(
            spec_kind="workflow",
            spec_id=self.id,
            spec_version=self.version,
            definition_hash=h,
        )
