"""Kiểm toàn vẹn đường báo cáo của workforce (Dự án C). Hàm thuần, dùng chung cho
InMemory và Postgres repository."""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

__all__ = [
    "MAX_REPORTING_DEPTH",
    "ReportingLineError",
    "ReportingNodes",
    "check_reporting_line",
    "direct_reports",
    "manager_chain",
]

MAX_REPORTING_DEPTH = 8

# id -> (reports_to_assignment_id, status)
ReportingNodes = Mapping[UUID, tuple[UUID | None, str]]


class ReportingLineError(ValueError):
    """Đường báo cáo không hợp lệ. `code` ổn định để API ánh xạ ra lỗi."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def check_reporting_line(
    *, assignment_id: UUID, parent_id: UUID | None, nodes: ReportingNodes
) -> None:
    if parent_id is None:
        return
    if parent_id == assignment_id:
        raise ReportingLineError("self_reference", "an assignment cannot report to itself")
    parent = nodes.get(parent_id)
    if parent is None:
        raise ReportingLineError("parent_not_found", f"manager {parent_id} not found")
    if parent[1] != "ACTIVE":
        raise ReportingLineError("parent_not_active", f"manager {parent_id} is not ACTIVE")

    seen = {assignment_id}
    current: UUID | None = parent_id
    depth = 1  # assignment -> parent
    while current is not None:
        if current in seen:
            raise ReportingLineError("cycle", "reporting line would create a cycle")
        seen.add(current)
        node = nodes.get(current)
        current = node[0] if node else None
        if current is not None:
            depth += 1
            if depth > MAX_REPORTING_DEPTH:
                raise ReportingLineError(
                    "depth_exceeded", f"reporting line deeper than {MAX_REPORTING_DEPTH}"
                )


def manager_chain(
    nodes: ReportingNodes, assignment_id: UUID, max_hops: int = MAX_REPORTING_DEPTH
) -> list[UUID]:
    """Tổ tiên ACTIVE liền kề, gần nhất trước. Dừng ở cha không ACTIVE/không tồn tại
    (leo thang khi đó đi thẳng tới operator), và an toàn trước vòng dữ liệu hỏng."""
    chain: list[UUID] = []
    seen = {assignment_id}
    node = nodes.get(assignment_id)
    current = node[0] if node else None
    while current is not None and len(chain) < max_hops:
        parent = nodes.get(current)
        if current in seen or parent is None or parent[1] != "ACTIVE":
            break
        chain.append(current)
        seen.add(current)
        current = parent[0]
    return chain


def direct_reports(nodes: ReportingNodes, manager_id: UUID) -> list[UUID]:
    return [
        aid
        for aid, (parent, status) in nodes.items()
        if parent == manager_id and status == "ACTIVE"
    ]
