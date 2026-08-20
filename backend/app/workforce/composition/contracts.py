from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from app.workforce.agents.profiles.schemas import AgentProfile

class ProfileExplanation(BaseModel):
    item_id: str
    item_type: str # 'tool', 'skill', 'workflow', etc.
    reason_code: str # 'SCOPE', 'PERMISSION', 'EXTENSION_DISABLED', 'SECRET_UNAVAILABLE'
    message: str

class ResolvedProfile(BaseModel):
    """
    Profile đã được phân giải các quyền hạn, tool/skill khả dụng đối với một ExecutionScope cụ thể.
    """
    base_profile: AgentProfile
    visible_tool_ids: List[str] = Field(default_factory=list)
    active_skill_versions: Dict[str, str] = Field(default_factory=dict)
    workflow_permissions: List[str] = Field(default_factory=list)
    effective_model_policy: Dict[str, str] = Field(default_factory=dict)
    scope_ceiling: Dict[str, Any] = Field(default_factory=dict)
    approval_baseline: Dict[str, Any] = Field(default_factory=dict)
    explanations: List[ProfileExplanation] = Field(default_factory=list)

class SessionOverride(BaseModel):
    """
    Khai báo ghi đè (override) cho một phiên/session.
    Các ghi đè này chỉ có thể là cắt giảm (subtractive), không bao giờ mở rộng quyền.
    """
    remove_tool_ids: List[str] = Field(default_factory=list)
    disable_skill_ids: List[str] = Field(default_factory=list)
    restrict_scope: Optional[Dict[str, Any]] = None
    # Có thể thêm allowlist cho bounded context references
