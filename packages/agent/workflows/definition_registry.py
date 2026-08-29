from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from agent.governance.hashing import definition_hash
from agent.workflows.schema import WorkflowSpec, WorkflowStepSpec
from agent.workflows.steps import WorkflowStep

if TYPE_CHECKING:
    from agent.workflows.engine import WorkflowEngine

__all__ = [
    "WorkflowDefinition",
    "WorkflowDefinitionNotFoundError",
    "WorkflowDefinitionRegistry",
    "WorkflowVersionNotFoundError",
]


class WorkflowDefinitionNotFoundError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"No workflow definition registered under name: {name}")
        self.name = name


class WorkflowVersionNotFoundError(Exception):
    def __init__(self, name: str, version_no: int) -> None:
        super().__init__(f"Workflow {name!r} has no version {version_no}")
        self.name = name
        self.version_no = version_no


class WorkflowDefinition(BaseModel):
    """1 phiên bản bất biến của định nghĩa workflow theo tên.

    Version hoá trực tiếp WorkflowSpec — `definition_hash` pin đúng nội dung thật,
    phát hiện silent drift nếu 2 lần đăng ký cùng version_no nhưng nội dung khác nhau.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    version_no: int
    definition_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WorkflowDefinitionRegistry:
    """Theo dõi version history cho workflow definition theo tên — không bao giờ sửa
    1 version đã đăng ký. Đăng ký version mới không xóa version cũ, chỉ chuyển 'current'
    sang version mới nhất.
    """

    def __init__(self) -> None:
        self._versions: dict[str, list[WorkflowDefinition]] = {}
        self._specs: dict[str, WorkflowSpec] = {}

    def register_version(self, spec: WorkflowSpec) -> WorkflowDefinition:
        name = spec.id
        history = self._versions.setdefault(name, [])
        h = spec.definition_hash or definition_hash(spec.model_dump(exclude={"definition_hash"}))
        definition = WorkflowDefinition(
            name=name,
            version_no=len(history) + 1,
            definition_hash=h,
        )
        history.append(definition)
        self._specs[definition.id] = spec
        return definition

    def current_version(self, name: str) -> WorkflowDefinition:
        history = self._versions.get(name)
        if not history:
            raise WorkflowDefinitionNotFoundError(name)
        return history[-1]

    def get_version(self, name: str, version_no: int) -> WorkflowDefinition:
        for definition in self._versions.get(name, []):
            if definition.version_no == version_no:
                return definition
        raise WorkflowVersionNotFoundError(name, version_no)

    def history(self, name: str) -> list[WorkflowDefinition]:
        return list(self._versions.get(name, []))

    def get_spec(self, definition: WorkflowDefinition) -> WorkflowSpec:
        return self._specs[definition.id]

    def build_steps(
        self,
        definition: WorkflowDefinition,
        engine: WorkflowEngine,
        custom_step_builders: dict[str, Callable[[WorkflowStepSpec], WorkflowStep]] | None = None,
    ) -> list[WorkflowStep]:
        return engine.build_steps_from_spec(self._specs[definition.id], custom_step_builders)
