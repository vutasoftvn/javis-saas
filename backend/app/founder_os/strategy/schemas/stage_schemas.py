from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ProjectStageEnum(str, Enum):
    # F1.md Standard Business Maturity Stages
    IDEA = "IDEA"
    VALIDATION = "VALIDATION"
    MVP = "MVP"
    EARLY_TRACTION = "EARLY_TRACTION"
    GROWTH = "GROWTH"
    SCALE = "SCALE"
    PAUSED = "PAUSED"
    SUNSET = "SUNSET"

    # Legacy stage codes for backward compatibility
    S0_EXPLORE = "S0_EXPLORE"
    S1_PROBLEM_VALIDATION = "S1_PROBLEM_VALIDATION"
    S2_SOLUTION_VALIDATION = "S2_SOLUTION_VALIDATION"
    S3_BUSINESS_VALIDATION = "S3_BUSINESS_VALIDATION"
    S4_GO_TO_MARKET = "S4_GO_TO_MARKET"
    S5_OPERATE_GROWTH = "S5_OPERATE_GROWTH"
    S6_SCALE_GOVERN = "S6_SCALE_GOVERN"


class StagePolicySpec(BaseModel):
    stage: ProjectStageEnum
    stage_name_vi: str
    code: str
    primary_goal: str
    primary_questions: List[str]
    required_entities: List[str]
    primary_metrics: List[str]
    deemphasized_tools: List[str]
    recommended_methods: List[str]
    optional_lenses: List[str]
    priority_agents: List[str]
    review_cadence: str


class StageContextResponse(BaseModel):
    workspace_id: int
    company_stage: str
    company_vision: Optional[str] = None
    company_mission: Optional[str] = None
    company_values: List[str] = []
    
    project_id: Optional[int] = None
    project_title: Optional[str] = None
    project_type: Optional[str] = None
    project_stage: ProjectStageEnum
    stage_started_at: Optional[datetime] = None
    stage_goal: Optional[str] = None
    critical_constraints: List[str] = []
    exit_criteria: Dict[str, Any] = {}
    stage_metadata: Dict[str, Any] = {}
    
    policy: StagePolicySpec


class ProjectStageUpdateRequest(BaseModel):
    project_stage: Optional[ProjectStageEnum] = None
    stage_goal: Optional[str] = None
    critical_constraints: Optional[List[str]] = None
    exit_criteria: Optional[Dict[str, Any]] = None
    stage_metadata: Optional[Dict[str, Any]] = None


class StageSummaryResponse(BaseModel):
    stage: ProjectStageEnum
    code: str
    name_vi: str
    primary_goal: str
    recommended_methods: List[str]
    priority_agents: List[str]
