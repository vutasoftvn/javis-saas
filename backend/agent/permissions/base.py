"""
COSA Deterministic Permission & Risk Engine Contracts
Quyền hạn được kiểm soát 100% bằng code tất định, không dựa vào phán đoán của LLM (CLAUDE.md Mục 11 & Structure.md Mục 26, 27, 28).
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from tools.base import BaseTool, RiskLevel


class PermissionDecision(str, Enum):
    """Quyết định phân quyền"""
    ALLOW = "ALLOW"                           # Cho phép thực thi ngay
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"     # Chờ Founder / Admin phê duyệt
    DENY = "DENY"                             # Từ chối thực thi do không đủ quyền


class PermissionEvaluationResult(BaseModel):
    """Kết quả đánh giá quyền hạn"""
    decision: PermissionDecision
    risk_level: RiskLevel
    reason: str
    required_approver_role: Optional[str] = None
    approval_payload_summary: Optional[Dict[str, Any]] = None


class PermissionEvaluatorInterface(ABC):
    """Giao diện bộ kiểm tra quyền hạn tất định"""

    @abstractmethod
    def evaluate(
        self, 
        tool: BaseTool, 
        user_roles: List[str], 
        agent_permissions: List[str],
        execution_context: Dict[str, Any]
    ) -> PermissionEvaluationResult:
        """Đánh giá quyền thực thi Tool dựa trên Risk Level và Roles"""
        pass
