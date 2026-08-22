from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    phase: Optional[str] = None
    project_stage: Optional[str] = None
    stage_goal: Optional[str] = None
    status: Optional[str] = "active"
    budget: Optional[float] = 0.0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    phase: Optional[str] = None
    status: Optional[str] = None
    budget: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ProjectClassifyRequest(BaseModel):
    title_override: Optional[str] = None
    description_override: Optional[str] = None
    project_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    project_type: Optional[str] = "core"
    strategic_fit: Optional[int] = Field(3, ge=1, le=5)
    financial_return: Optional[int] = Field(3, ge=1, le=5)
    risk_level: Optional[int] = Field(3, ge=1, le=5)
    resource_intensity: Optional[int] = Field(3, ge=1, le=5)
    market_urgency: Optional[int] = Field(3, ge=1, le=5)
    context_note: Optional[str] = None


class MethodologyRouteRequest(BaseModel):
    custom_methodologies: Optional[List[str]] = None
    custom_rules: Optional[dict] = None
    rationale_override: Optional[str] = None
    project_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    classification_category: Optional[str] = "growth"
    team_experience: Optional[str] = "medium"
    complexity: Optional[str] = "medium"
    time_pressure: Optional[str] = "medium"
    uncertainty: Optional[str] = "medium"
    context_note: Optional[str] = None


class InitiativeCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = "proposed"


class InitiativeUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
