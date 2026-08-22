from typing import Literal, Optional
from pydantic import BaseModel, Field

ExecutionMode = Literal["MANUAL", "AI_ASSISTED", "AUTONOMOUS"]
ServiceDisposition = Literal["REQUIRED", "RECOMMENDED", "OPTIONAL"]


class GenerateRoadmapRequest(BaseModel):
    instruction: Optional[str] = None


class RoadmapStageDraft(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    hypothesis: str = Field(default="", max_length=2000)
    scope: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)
    exit_criteria: list[str] = Field(default_factory=list)


class RoadmapDraft(BaseModel):
    stages: list[RoadmapStageDraft] = Field(min_length=1, max_length=10)


class StagePlanKeyResult(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    target_value: Optional[float] = None
    unit: Optional[str] = None


class StagePlanObjective(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    key_results: list[StagePlanKeyResult] = Field(default_factory=list, max_length=5)


class StagePlanDraft(BaseModel):
    objectives: list[StagePlanObjective] = Field(min_length=1, max_length=3)
    weekly_focus: list[str] = Field(min_length=1, max_length=52)


class ServiceAssessmentDecision(BaseModel):
    assessment_id: str
    approved: bool
    execution_mode: Optional[ExecutionMode] = None


class ServiceAssessmentConfirmRequest(BaseModel):
    decisions: list[ServiceAssessmentDecision] = Field(min_length=1)


class StageRevisionChange(BaseModel):
    hypothesis: Optional[str] = Field(default=None, min_length=20)
    scope: Optional[list[str]] = None
    non_goals: Optional[list[str]] = None
    exit_criteria: Optional[list[str]] = None


class ApplyStageRevisionRequest(BaseModel):
    revision_id: str


GateDecisionValue = Literal["GO", "ITERATE", "HOLD", "STOP", "PIVOT"]


class Week13ConfirmRequest(BaseModel):
    decision: GateDecisionValue
    rationale: str = Field(min_length=10)
