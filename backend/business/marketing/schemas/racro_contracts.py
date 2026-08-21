"""
COSA RACRO Domain Contracts & Schemas.
Định nghĩa các chuẩn giao tiếp dữ liệu (Data Contracts) cho:
- MarketingSignal
- MarketingMission
- RACROIntentDecision
- AttributionChainEvent
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from business.marketing.racro_registry import RACROMove


class MarketingSignal(BaseModel):
    """Data contract cho tín hiệu thị trường / nhu cầu (§3.3 Spec)."""
    id: str
    workspace_id: int
    project_id: Optional[int] = None
    source_type: str = Field(..., description="search, social, crm, competitor, review, website")
    source_url: Optional[str] = None
    title: str
    summary: str
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Mức độ tin cậy của AI/nguồn")
    related_segment: Optional[str] = None
    related_hypothesis: Optional[str] = None
    observed_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    evidence_id: Optional[int] = Field(default=None, description="Khóa ngoại liên kết sang EvidenceItem khi Founder duyệt")
    raw_payload: Optional[Dict[str, Any]] = Field(default_factory=dict)


class MarketingMission(BaseModel):
    """Data contract cho nhiệm vụ điều phối Marketing (§7.1 Spec)."""
    mission_id: str
    workspace_id: int
    project_id: Optional[int] = None
    move: RACROMove
    capability_id: str
    intent: str
    goal: str
    requested_by: str = Field(default="founder")
    approval_required: bool = False
    context_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RACROIntentDecision(BaseModel):
    """Kết quả phân loại Intent đa tầng theo RACRO model."""
    domain: str = Field(default="general", description="marketing, sales, general, etc.")
    move: Optional[RACROMove] = None
    capability_id: Optional[str] = None
    skill_name: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_tool_allowed: bool = Field(default=False, description="NO INTENT = NO TOOL (True chỉ khi có intent rõ ràng)")
    reason: str = Field(default="")
    extracted_entities: Dict[str, Any] = Field(default_factory=dict)


class AttributionChainEvent(BaseModel):
    """Data contract cho chuỗi truy xuất nguồn gốc doanh thu (§14 Spec)."""
    event_id: str
    workspace_id: int
    project_id: Optional[int] = None
    campaign_id: Optional[int] = None
    content_id: Optional[int] = None
    landing_page_id: Optional[int] = None
    lead_id: Optional[int] = None
    opportunity_id: Optional[int] = None
    customer_id: Optional[int] = None
    revenue_amount: Optional[float] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    event_type: str = Field(..., description="first_touch, lead_capture, qualified, sale_closed, repeat_sale")
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
