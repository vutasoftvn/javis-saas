from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class AuditStatusEnum(str, Enum):
    APPROVED = "APPROVED"
    CONDITIONALLY_APPROVED = "CONDITIONALLY_APPROVED"
    REJECTED = "REJECTED"


class AlertSeverityEnum(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


class StageGateCriteriaItem(BaseModel):
    criterion_id: str
    title: str
    description: str
    is_met: bool
    current_value: str
    required_value: str
    evidence_level_met: Optional[str] = None


class StageGateAuditRequest(BaseModel):
    project_id: int
    target_stage: Optional[str] = None # Nếu None, tự động xác định stage tiếp theo (S_{k+1})


class StageGateAuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    project_id: int
    from_stage: str
    to_stage: str
    readiness_score: float
    audit_status: str
    passed_criteria: List[Dict[str, Any]] = []
    missing_criteria: List[Dict[str, Any]] = []
    detected_risks: List[Dict[str, Any]] = []
    audited_by_agent: str
    recommendation_note: str
    created_at: datetime

    # Diễn giải bổ sung (mục 8.2 tài liệu COSA Stage-Aware): strong/weak/blockers + khuyến nghị 5 giá trị
    strong_areas: List[str] = []
    weak_areas: List[str] = []
    blockers: List[str] = []
    recommended_action: str = "CONTINUE"  # ADVANCE | CONTINUE | PIVOT | PAUSE | STOP


class PrematureScalingAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    project_id: int
    current_stage: str
    rule_code: str
    severity: str
    title: str
    message: str
    is_dismissed: bool
    created_at: datetime


class ApplyStageTransitionRequest(BaseModel):
    rationale: Optional[str] = "Phê duyệt nâng cấp giai đoạn theo kết quả thẩm định Stage Gate."
