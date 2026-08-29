from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from agent.governance.contracts import PinnedSpecIdentity
from agent.governance.hashing import definition_hash

__all__ = ["StepType", "WorkflowSpec", "WorkflowStepSpec"]


class StepType(enum.StrEnum):
    TOOL_CALL = "tool_call"
    AGENT = "agent"
    DETERMINISTIC = "deterministic"
    APPROVAL_GATE = "approval_gate"
    PARALLEL = "parallel"
    RETRY = "retry"
    COMPENSATING = "compensating"


class WorkflowStepSpec(BaseModel):
    id: str
    name: str | None = None
    type: StepType = StepType.TOOL_CALL
    tool: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    on_failure: str | None = None
    compensate_with: str | None = None
    output_key: str | None = None
    agent_key: str | None = None
    goal_key: str | None = None
    action: str | None = None
    subject_key: str | None = None
    permission_level: str | None = None
    autonomy_level: str | None = None
    capability_risk: str | None = None
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
    definition_hash: str | None = None

    @model_validator(mode="after")
    def _validate_dag(self) -> WorkflowSpec:
        """Reject spec sai cấu trúc trước khi execute — chặn engine rơi vào
        trạng thái COMPLETED giả khi DAG có cycle hoặc dependency treo
        (xem packages/agent/workflows/engine.py::_execute_dag, vòng lặp
        while không tìm được ready step nào sẽ break nhưng vẫn set COMPLETED
        nếu không có validation này chặn từ trước).
        """
        if len(self.steps) == 0:
            raise ValueError("WorkflowSpec has no steps")

        step_ids = [s.id for s in self.steps]
        step_id_set = set(step_ids)
        if len(step_ids) != len(step_id_set):
            duplicates = {sid for sid in step_ids if step_ids.count(sid) > 1}
            raise ValueError(f"duplicate step id(s) in WorkflowSpec: {sorted(duplicates)}")

        compensation_targets = {s.on_failure for s in self.steps if s.on_failure}
        forward_steps = [s for s in self.steps if s.id not in compensation_targets]
        if not forward_steps:
            raise ValueError(
                "WorkflowSpec has no forward steps: every step is a compensation target"
            )

        for step in self.steps:
            for dep in step.depends_on:
                if dep not in step_id_set:
                    raise ValueError(f"step '{step.id}' depends_on unknown step '{dep}'")
            if step.on_failure is not None and step.on_failure not in step_id_set:
                raise ValueError(
                    f"step '{step.id}' on_failure targets unknown step '{step.on_failure}'"
                )
            if step.compensate_with is not None and step.compensate_with not in step_id_set:
                raise ValueError(
                    f"step '{step.id}' compensate_with targets unknown step '{step.compensate_with}'"
                )

        # Cycle detection trên đồ thị depends_on (DFS + recursion stack).
        graph: dict[str, list[str]] = {s.id: s.depends_on for s in self.steps}
        visited: set[str] = set()
        in_stack: set[str] = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            in_stack.add(node)
            for dep in graph.get(node, []):
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in in_stack:
                    return True
            in_stack.remove(node)
            return False

        for step_id in step_id_set:
            if step_id not in visited and has_cycle(step_id):
                raise ValueError(
                    f"dependency cycle detected in WorkflowSpec involving step '{step_id}'"
                )

        # Compensation target (on_failure) bị engine loại khỏi forward_steps
        # (xem engine.py::_execute_dag) — nếu step forward khác lại depends_on
        # đúng step đó, dependency sẽ vĩnh viễn không bao giờ thoả mãn.
        for step in self.steps:
            if step.id in compensation_targets:
                continue
            for dep in step.depends_on:
                if dep in compensation_targets:
                    raise ValueError(
                        f"step '{step.id}' depends_on '{dep}', which is a compensation target and "
                        "never runs as a forward step"
                    )

        return self

    def get_step(self, step_id: str) -> WorkflowStepSpec | None:
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def compute_hash(self) -> str:
        """Tính SHA-256 hash chuẩn hoá cho toàn bộ nội dung của WorkflowSpec."""
        data = self.model_dump(exclude={"definition_hash"})
        return definition_hash(data)

    def with_hash(self) -> WorkflowSpec:
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
