from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class PestelDimensionEnum(str, Enum):
    POLITICAL = "political"
    ECONOMIC = "economic"
    SOCIAL = "social"
    TECHNOLOGICAL = "technological"
    ENVIRONMENTAL = "environmental"
    LEGAL = "legal"


class SwotTypeEnum(str, Enum):
    STRENGTH = "STRENGTH"
    WEAKNESS = "WEAKNESS"
    OPPORTUNITY = "OPPORTUNITY"
    THREAT = "THREAT"


class TowsTypeEnum(str, Enum):
    SO = "SO"  # Strengths-Opportunities (Maxi-Maxi)
    WO = "WO"  # Weaknesses-Opportunities (Mini-Maxi)
    ST = "ST"  # Strengths-Threats (Maxi-Mini)
    WT = "WT"  # Weaknesses-Threats (Mini-Mini)


class BscPerspectiveEnum(str, Enum):
    FINANCIAL = "FINANCIAL"
    CUSTOMER = "CUSTOMER"
    INTERNAL_OPERATIONS = "INTERNAL_OPERATIONS"
    LEARNING_GROWTH = "LEARNING_GROWTH"


# --- PESTEL Schemas ---
class PestelSignalCreate(BaseModel):
    project_id: int
    dimension: PestelDimensionEnum
    signal_title: str
    description: str
    impact_level: str = "medium" # high | medium | low
    time_horizon: str = "medium_term" # short_term | medium_term | long_term


class PestelSignalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    project_id: int
    dimension: str
    signal_title: str
    description: str
    impact_level: str
    time_horizon: str
    resulting_hypothesis_id: Optional[int] = None
    stage_captured: str
    created_at: datetime


# --- SWOT Schemas ---
class SwotItemCreate(BaseModel):
    project_id: int
    category: SwotTypeEnum
    statement: str
    importance: float = 0.5
    evidence_refs: List[int] = [] # Bắt buộc với STRENGTH & WEAKNESS
    pestel_signal_ref: Optional[int] = None


class SwotItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    project_id: Optional[int] = None
    category: str
    statement: str
    importance: float
    evidence_status: str
    evidence_refs: List[int] = []
    pestel_signal_ref: Optional[int] = None
    created_at: datetime


# --- TOWS Schemas ---
class TowsOptionCreate(BaseModel):
    project_id: int
    quadrant: TowsTypeEnum
    title: str
    strategy_description: str
    linked_strength_ids: List[int] = []
    linked_weakness_ids: List[int] = []
    linked_opportunity_ids: List[int] = []
    linked_threat_ids: List[int] = []


class TowsOptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    project_id: Optional[int] = None
    quadrant: str
    title: str
    tradeoffs: Optional[str] = None
    expected_impact: str
    confidence: str
    status: str
    linked_strength_ids: List[int] = []
    linked_weakness_ids: List[int] = []
    linked_opportunity_ids: List[int] = []
    linked_threat_ids: List[int] = []
    resulting_hypothesis_id: Optional[int] = None
    tactics_12wy: List[Dict[str, Any]] = []
    created_at: datetime


class TowsToTacticConvertRequest(BaseModel):
    tactic_title: str
    week_number: int = Field(default=1, ge=1, le=12)
    lead_indicator: str
    owner_agent: Optional[str] = "Strategy Agent"


# --- BSC Schemas ---
class BscGoalCreate(BaseModel):
    project_id: int
    perspective: BscPerspectiveEnum
    objective: str
    kpi_name: str
    target_value: str
    current_value: str = "0"
    initiatives: List[str] = []


class BscGoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    project_id: int
    perspective: str
    objective: str
    kpi_name: str
    target_value: str
    current_value: str
    initiatives: List[str] = []
    status: str
    created_at: datetime


# --- Stage Lens Summary ---
class StageLensSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: int
    project_stage: str
    is_bsc_unlocked: bool
    pestel_signals: List[PestelSignalResponse] = []
    swot_items: List[SwotItemResponse] = []
    tows_options: List[TowsOptionResponse] = []
    bsc_goals: List[BscGoalResponse] = []
