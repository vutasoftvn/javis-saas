from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

__all__ = ["RoleHierarchyTree", "WeightedApprover", "WeightedQuorumPolicy"]


class RoleHierarchyTree:
    """Cây phân cấp vai trò (Role Hierarchy) hỗ trợ thừa kế thẩm quyền phê duyệt."""

    def __init__(self) -> None:
        # child_role -> parent_role (e.g. "finance_officer" -> "finance_director" -> "cfo")
        self._hierarchy: dict[str, str] = {}

    def add_relation(self, sub_role: str, superior_role: str) -> None:
        self._hierarchy[sub_role] = superior_role

    def is_superior_or_equal(self, active_role: str, required_role: str) -> bool:
        if active_role == required_role or active_role in ("admin", "superadmin", "founder"):
            return True
        curr = required_role
        while curr in self._hierarchy:
            parent = self._hierarchy[curr]
            if parent == active_role:
                return True
            curr = parent
        return False



class WeightedApprover(BaseModel):
    principal_or_role: str
    weight: int = 1


class WeightedQuorumPolicy(BaseModel):
    """Chính sách Quorum có trọng số cho các quyết định quản trị cấp cao."""

    required_weight: int
    approvers: tuple[WeightedApprover, ...]

    def evaluate_decisions(self, approved_principals_or_roles: set[str]) -> bool:
        accumulated = 0
        for app in self.approvers:
            if app.principal_or_role in approved_principals_or_roles:
                accumulated += app.weight
        return accumulated >= self.required_weight
