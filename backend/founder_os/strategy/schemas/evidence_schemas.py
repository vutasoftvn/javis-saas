from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class HypothesisCategoryEnum(str, Enum):
    CUSTOMER = "customer"
    PROBLEM = "problem"
    SOLUTION = "solution"
    PRICING = "pricing"
    CHANNEL = "channel"
    REVENUE = "revenue"
    COST = "cost"
    TECHNOLOGY = "technology"
    LEGAL = "legal"
    OPERATIONAL = "operational"


class HypothesisStatusEnum(str, Enum):
    UNTESTED = "UNTESTED"
    TESTING = "TESTING"
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INVALIDATED = "INVALIDATED"


class EvidenceLadderLevelEnum(str, Enum):
    E0_OPINION = "E0_OPINION"
    E1_STATED_INTEREST = "E1_STATED_INTEREST"
    E2_OBSERVED_PROBLEM = "E2_OBSERVED_PROBLEM"
    E3_BEHAVIORAL_COMMITMENT = "E3_BEHAVIORAL_COMMITMENT"
    E4_ECONOMIC_COMMITMENT = "E4_ECONOMIC_COMMITMENT"
    E5_REPEAT_BEHAVIOR = "E5_REPEAT_BEHAVIOR"
    E6_SCALABLE_EVIDENCE = "E6_SCALABLE_EVIDENCE"


class EvidenceTypeEnum(str, Enum):
    INTERVIEW = "interview"
    OBSERVATION = "observation"
    BEHAVIORAL = "behavioral"
    TRANSACTION = "transaction"
    USAGE = "usage"
    CAMPAIGN = "campaign"
    FINANCIAL = "financial"
    LEGAL = "legal"
    MARKET_SIGNAL = "market_signal"


class EvidenceStrengthEnum(str, Enum):
    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"


class EvidenceDirectionEnum(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    NEUTRAL = "neutral"


# --- Hypothesis Schemas ---
class HypothesisCreate(BaseModel):
    project_id: int
    category: HypothesisCategoryEnum
    statement: str
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    uncertainty: float = Field(default=0.5, ge=0.0, le=1.0)
    next_action: Optional[str] = None


class HypothesisUpdate(BaseModel):
    category: Optional[HypothesisCategoryEnum] = None
    statement: Optional[str] = None
    importance: Optional[float] = Field(None, ge=0.0, le=1.0)
    uncertainty: Optional[float] = Field(None, ge=0.0, le=1.0)
    status: Optional[HypothesisStatusEnum] = None
    next_action: Optional[str] = None


class HypothesisResponse(BaseModel):
    id: int
    workspace_id: int
    project_id: int
    category: str
    statement: str
    importance: float
    uncertainty: float
    risk_score: float
    evidence_score: float
    confidence: float
    status: str
    stage_created: str
    evidence_refs: List[int] = []
    experiment_refs: List[int] = []
    next_action: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# --- Evidence Schemas ---
class EvidenceCreate(BaseModel):
    project_id: int
    type: EvidenceTypeEnum
    ladder_level: EvidenceLadderLevelEnum = EvidenceLadderLevelEnum.E1_STATED_INTEREST
    source: str
    claim_supported: str
    strength: EvidenceStrengthEnum = EvidenceStrengthEnum.MEDIUM
    direction: EvidenceDirectionEnum = EvidenceDirectionEnum.SUPPORTS
    hypothesis_refs: List[int] = []
    artifact_refs: List[int] = []
    raw_payload: Dict[str, Any] = {}


class EvidenceUpdate(BaseModel):
    type: Optional[EvidenceTypeEnum] = None
    ladder_level: Optional[EvidenceLadderLevelEnum] = None
    source: Optional[str] = None
    claim_supported: Optional[str] = None
    strength: Optional[EvidenceStrengthEnum] = None
    direction: Optional[EvidenceDirectionEnum] = None
    hypothesis_refs: Optional[List[int]] = None
    artifact_refs: Optional[List[int]] = None
    raw_payload: Optional[Dict[str, Any]] = None


class EvidenceResponse(BaseModel):
    id: int
    workspace_id: int
    project_id: int
    type: str
    ladder_level: str
    ladder_weight: float
    source: str
    claim_supported: str
    strength: str
    direction: str
    hypothesis_refs: List[int] = []
    artifact_refs: List[int] = []
    raw_payload: Dict[str, Any] = {}
    captured_at: datetime
    created_at: datetime


# --- Strategic Decision Schemas ---
class StrategicDecisionCreate(BaseModel):
    project_id: Optional[int] = None
    question: str
    selected_option: str
    alternatives: List[str] = []
    rationale: Optional[str] = None
    evidence_refs: List[int] = []
    stage: str = "S1_PROBLEM_VALIDATION"
    expected_result: Optional[str] = None
    review_date: Optional[datetime] = None


class StrategicDecisionResponse(BaseModel):
    id: int
    workspace_id: int
    project_id: Optional[int] = None
    question: Optional[str] = None
    decision: str
    selected_option: Optional[str] = None
    alternatives: List[str] = []
    rationale: Optional[str] = None
    evidence_refs: List[int] = []
    stage: str
    expected_result: Optional[str] = None
    review_date: Optional[datetime] = None
    status: str
    decided_by: Optional[int] = None
    created_at: datetime


# --- Matrix & Summary Schemas ---
class AssumptionMatrixQuadrant(BaseModel):
    critical_test_first: List[HypothesisResponse] = []  # High Importance (>=0.7), High Uncertainty (>=0.6)
    monitor: List[HypothesisResponse] = []              # Low Importance (<0.7), High Uncertainty (>=0.6)
    important_low_risk: List[HypothesisResponse] = []   # High Importance (>=0.7), Low Uncertainty (<0.6)
    low_priority: List[HypothesisResponse] = []         # Low Importance (<0.7), Low Uncertainty (<0.6)


class AssumptionMatrixResponse(BaseModel):
    project_id: int
    total_hypotheses: int
    critical_count: int
    quadrants: AssumptionMatrixQuadrant
