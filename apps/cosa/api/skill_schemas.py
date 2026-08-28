from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

__all__ = [
    "CreateCandidateRequest",
    "DeprecateSkillRequest",
    "EvaluateSkillRequest",
    "EvaluateSkillResponse",
    "PromoteSkillRequest",
    "SkillFeedbackRequest",
    "SkillListItem",
    "SyncBuiltInResponse",
    "SyncSkillItem",
]


class SkillListItem(BaseModel):
    id: str
    version: str
    name: str = ""
    description: str = ""
    domain: str = "general"
    status: str = "PUBLISHED"
    definition_hash: str
    required_capabilities: list[str] = Field(default_factory=list)
    origin: str | None = None
    adapted_from_sha: str | None = None
    eval_score: float | None = None
    runtime_state: str = "unpinned"
    instructions: str | None = None
    references: dict[str, Any] = Field(default_factory=dict)
    candidate_id: str | None = None
    created_at: str | None = None


class SyncSkillItem(BaseModel):
    skill_id: str
    version: str
    definition_hash: str
    published: bool = True
    domain: str = "general"


class SyncBuiltInResponse(BaseModel):
    synced_count: int
    skills: list[SyncSkillItem] = Field(default_factory=list)


class CreateCandidateRequest(BaseModel):
    name: str
    domain: str
    instructions: str
    description: str = ""
    scope: list[str] = Field(default_factory=list)
    tool_permissions: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    required_context: list[str] = Field(default_factory=list)
    created_by_agent: str | None = None
    workspace_id: str | None = None


class EvaluateSkillRequest(BaseModel):
    eval_score: float = 0.0
    eval_details: dict[str, Any] = Field(default_factory=dict)


class EvaluateSkillResponse(BaseModel):
    skill_id: str
    eval_score: float
    status: str
    details: dict[str, Any] = Field(default_factory=dict)


class PromoteSkillRequest(BaseModel):
    approved_by: str = Field(..., description="Tên hoặc user_id của người phê duyệt (bắt buộc)")
    approval_reason: str = Field(..., description="Lý do phê duyệt đưa vào sản xuất (bắt buộc)")
    version: str | None = None


class DeprecateSkillRequest(BaseModel):
    reason: str | None = None


class SkillFeedbackRequest(BaseModel):
    success: bool
    rating: int | None = None
    notes: str | None = None
