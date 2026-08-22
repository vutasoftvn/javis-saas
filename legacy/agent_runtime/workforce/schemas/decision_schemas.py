"""Founder Decision Schemas (F4 Specification)

Phục vụ hàng đợi ra quyết định của Founder (Waiting for You),
phân biệt rõ với Approval Request và tích hợp với Evidence Engine (F1/F3).
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class DecisionStatusEnum(str, Enum):
    PENDING = "PENDING"
    DECIDED = "DECIDED"
    DISMISSED = "DISMISSED"
    DEFERRED = "DEFERRED"


class DecisionDomainEnum(str, Enum):
    SALES = "SALES"
    MARKETING = "MARKETING"
    FINANCE = "FINANCE"
    LEGAL = "LEGAL"
    TECH = "TECH"
    CROSS_DOMAIN = "CROSS_DOMAIN"


class DecisionOption(BaseModel):
    id: str = Field(..., description="Mã phương án (A, B, C, ...)")
    title: str = Field(..., description="Tiêu đề phương án")
    description: Optional[str] = None
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)
    estimated_impact: Optional[Dict[str, Any]] = None


class DecisionRecommendation(BaseModel):
    recommended_option_id: str
    confidence: float = 0.8
    rationale: str
    challenge_notes: Optional[str] = None  # Ghi chú phản biện giả định của Founder


class FounderDecisionBase(BaseModel):
    domain: DecisionDomainEnum = DecisionDomainEnum.CROSS_DOMAIN
    question: str = Field(..., description="Câu hỏi hoặc vấn đề kinh doanh cần Founder quyết định")
    context_summary: Optional[str] = Field(None, description="Bối cảnh dẫn tới câu hỏi")
    options_jsonb: List[DecisionOption] = Field(default_factory=list)
    ai_recommendation_jsonb: Optional[Dict[str, Any]] = None
    evidence_ids: List[str] = Field(default_factory=list, description="IDs của bằng chứng thực tế từ F1/F3")
    risk_analysis_jsonb: Optional[Dict[str, Any]] = None


class FounderDecisionCreate(FounderDecisionBase):
    workspace_id: Optional[int] = None
    project_id: Optional[int] = None


class FounderDecisionResolveRequest(BaseModel):
    decision_made: str = Field(..., description="Lựa chọn phương án hoặc quyết định của Founder")
    founder_notes: Optional[str] = Field(None, description="Ghi chú bổ sung từ Founder")
    status: DecisionStatusEnum = DecisionStatusEnum.DECIDED


class FounderDecisionResponse(FounderDecisionBase):
    id: int
    workspace_id: Optional[int] = None
    project_id: Optional[int] = None
    status: DecisionStatusEnum
    decision_made: Optional[str] = None
    founder_notes: Optional[str] = None
    decided_by_user_id: Optional[int] = None
    decided_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

