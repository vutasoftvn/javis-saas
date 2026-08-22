from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class TacticalItemCreate(BaseModel):
    project_id: int
    cycle_id: Optional[int] = None
    week_number: int = Field(..., ge=1, le=12)
    title: str
    description: Optional[str] = ""
    tows_option_id: Optional[int] = None
    hypothesis_id: Optional[int] = None
    lead_indicator_name: str
    target_count: int = Field(default=1, ge=1)
    actual_count: int = Field(default=0, ge=0)
    status: Optional[str] = "PLANNED" # PLANNED | IN_PROGRESS | DONE | BLOCKED
    owner_role: Optional[str] = "Founder"


class TacticalItemUpdate(BaseModel):
    actual_count: Optional[int] = None
    status: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


class TacticalItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    project_id: int
    cycle_id: int
    week_number: int
    title: str
    description: str
    tows_option_id: Optional[int] = None
    hypothesis_id: Optional[int] = None
    lead_indicator_name: str
    target_count: int
    actual_count: int
    status: str
    owner_role: str
    completed_at: Optional[datetime] = None
    created_at: datetime


class TwelveWeekCycleCreate(BaseModel):
    project_id: int
    title: str
    vision_statement: Optional[str] = ""
    stage_at_start: Optional[str] = "S1_PROBLEM_VALIDATION"
    total_weeks: Optional[int] = 12


class TwelveWeekCycleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    workspace_id: int
    project_id: Optional[int] = None
    title: Optional[str] = Field(None, validation_alias="theme")
    vision_statement: Optional[str] = ""
    stage_at_start: Optional[str] = "S1_PROBLEM_VALIDATION"
    current_week: int = 1
    total_weeks: int = Field(12, validation_alias="duration_weeks")
    status: str = "ACTIVE"
    overall_execution_score: float = 0.0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime


class WeeklyReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    project_id: int
    cycle_id: int
    week_number: int
    execution_score: float
    total_planned: int
    total_completed: int
    key_breakthroughs: List[str] = []
    root_cause_blocks: List[str] = []
    ai_recommendations: List[str] = []
    created_at: datetime


class TwelveWyDashboardResponse(BaseModel):
    cycle: TwelveWeekCycleResponse
    current_week: int
    current_week_execution_score: float
    tactics_by_week: Dict[int, List[TacticalItemResponse]] = {}
    weekly_scores: Dict[int, float] = {}
    latest_review: Optional[WeeklyReviewResponse] = None
