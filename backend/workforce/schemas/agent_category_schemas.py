"""Agent Category & Workforce Classification Schemas (F4 Specification)

Phân loại 4 nhóm Agent:
- ORCHESTRATOR: COSA Co-Founder duy nhất ở cấp hệ thống
- DOMAIN: 5 Core Domain Agents (Sales, Marketing, Finance, Legal, Build)
- OPTIONAL_DOMAIN: Domain mở rộng theo gói (Operations, People, Support)
- LEGACY: Agent đơn nhiệm cũ chuyển hóa thành Specialist / Capability
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class AgentCategoryEnum(str, Enum):
    ORCHESTRATOR = "ORCHESTRATOR"
    DOMAIN = "DOMAIN"
    OPTIONAL_DOMAIN = "OPTIONAL_DOMAIN"
    LEGACY = "LEGACY"


class AgentAliasTargetTypeEnum(str, Enum):
    ORCHESTRATOR = "ORCHESTRATOR"
    DOMAIN = "DOMAIN"
    SPECIALIST = "SPECIALIST"
    CAPABILITY = "CAPABILITY"
    TOOL = "TOOL"


class AgentAliasBase(BaseModel):
    alias_key: str = Field(..., description="Tên alias cũ (vd: founder_agent, research_agent)")
    target_type: AgentAliasTargetTypeEnum = Field(..., description="Loại đối tượng đích")
    target_key: str = Field(..., description="Key đích mới (vd: cosa, investigate, marketing.seo)")
    is_active: bool = True
    notes: Optional[str] = None


class AgentAliasCreate(AgentAliasBase):
    workspace_id: Optional[int] = None


class AgentAliasResponse(AgentAliasBase):
    id: int
    workspace_id: Optional[int] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

