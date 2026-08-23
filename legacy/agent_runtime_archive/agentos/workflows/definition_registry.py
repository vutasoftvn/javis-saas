from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

from agent_core.governance.hashing import definition_hash
from agentos.workflows.schema import WorkflowSpec, WorkflowStepSpec
from agentos.workflows.steps import WorkflowStep

if TYPE_CHECKING:
    from typing import Callable

    from agentos.workflows.engine import WorkflowEngine


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
    """1 phiên bản bất biến của định nghĩa workflow theo tên. Version hoá
    trực tiếp `WorkflowSpec` khai báo (không phải 1 Python callable tách
    biệt như trước) — `definition_hash` pin đúng nội dung thật, phát hiện
    được silent drift nếu 2 lần đăng ký cùng version_no nhưng nội dung
    khác nhau. Xem COSA_AGENT_CORE_GOVERNANCE_TEMPORAL_MODEL_2026-08-23.md
    PHẦN I §1 cho lý do đổi thiết kế này."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    version_no: int
    definition_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkflowDefinitionRegistry:
    """Theo dõi version history cho workflow definition theo tên — không
    bao giờ sửa 1 version đã đăng ký (blueprint §12.1 "Never update an
    active skill/workflow in place", áp dụng tương tự cho workflow). Đăng
    ký version mới không xóa version cũ, chỉ đổi "current" sang version mới
    nhất — cho phép truy vấn lại lịch sử hoặc chạy lại 1 version cũ nếu cần
    rollback.
    """

    def __init__(self) -> None:
        self._versions: dict[str, list[WorkflowDefinition]] = {}
        self._specs: dict[str, WorkflowSpec] = {}

    def register_version(self, spec: WorkflowSpec) -> WorkflowDefinition:
        name = spec.id
        history = self._versions.setdefault(name, [])
        definition = WorkflowDefinition(
            name=name,
            version_no=len(history) + 1,
            definition_hash=definition_hash(spec),
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
        engine: "WorkflowEngine",
        custom_step_builders: Optional[dict[str, "Callable[[WorkflowStepSpec], WorkflowStep]"]] = None,
    ) -> list[WorkflowStep]:
        return engine.build_steps_from_spec(self._specs[definition.id], custom_step_builders)
