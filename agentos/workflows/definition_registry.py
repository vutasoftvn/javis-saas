from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Callable

from pydantic import BaseModel, Field

from agentos.workflows.steps import WorkflowStep


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
    """1 phiên bản bất biến của định nghĩa workflow theo tên (port từ
    `WorkflowVersion` trong `legacy/backend/integrations/workflows/models.py`,
    theo ADR-015 — đó là tính năng duy nhất bên workflow engine cũ có mà
    `agentos/workflows/` chưa có). Chỉ chứa metadata version; danh sách
    `WorkflowStep` thật (Python object/callable, không phải data khai báo
    kiểu `graph_jsonb` như bên legacy) được `WorkflowDefinitionRegistry` giữ
    riêng qua 1 factory function — không serialize step như dữ liệu tĩnh.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    version_no: int
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
        self._step_factories: dict[str, Callable[[], list[WorkflowStep]]] = {}

    def register_version(self, name: str, steps_factory: Callable[[], list[WorkflowStep]]) -> WorkflowDefinition:
        history = self._versions.setdefault(name, [])
        definition = WorkflowDefinition(name=name, version_no=len(history) + 1)
        history.append(definition)
        self._step_factories[definition.id] = steps_factory
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

    def build_steps(self, definition: WorkflowDefinition) -> list[WorkflowStep]:
        return self._step_factories[definition.id]()
