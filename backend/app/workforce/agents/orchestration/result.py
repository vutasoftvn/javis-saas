# backend/app/workforce/agents/orchestration/result.py
"""Response shape cho mission orchestration — tách khỏi chief_of_staff.py
(đã xoá) để orchestration/service.py và router.py không phụ thuộc vào file đã
retire. Field/kiểu dữ liệu giữ NGUYÊN so với ChiefOfStaffResult gốc — API
response contract không đổi."""
from typing import Any
from pydantic import BaseModel, Field


class DelegatedTaskResult(BaseModel):
    agent_key: str
    domain: str
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    status: str = "completed"


class ChiefOfStaffResult(BaseModel):
    mission_id: str
    workspace_id: str
    goal: str
    diagnosis: str
    specialist_reports: dict[str, Any] = Field(default_factory=dict)
    priorities: list[str] = Field(default_factory=list)
    action_plan: list[dict[str, Any]] = Field(default_factory=list)
    required_approvals: list[dict[str, Any]] = Field(default_factory=list)
    proposals: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "completed"
