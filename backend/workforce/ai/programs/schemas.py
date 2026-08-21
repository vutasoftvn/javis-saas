"""Pydantic schemas and contracts for COSA AI Programs."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class AIProgramRequest(BaseModel):
    """Neutral contract for executing an AI bounded reasoning program."""

    workspace_id: str = Field(..., description="Workspace ID for multi-tenant isolation")
    brain_id: Optional[str] = Field(None, description="Brain / Tenant scope identifier")
    user_id: Optional[str] = Field(None, description="User requesting the program execution")
    program_key: str = Field(..., description="Unique program identifier (e.g. 'ceo.brief', 'sales.lead_qualification')")
    program_version: Optional[str] = Field(None, description="Target version, defaults to active production version")

    input: Dict[str, Any] = Field(default_factory=dict, description="Structured input payload for the program")
    context_refs: List[str] = Field(default_factory=list, description="References to business documents/records")

    model_policy: Optional[str] = Field(None, description="COSA model policy profile to resolve")
    correlation_id: Optional[str] = Field(None, description="Distributed correlation / trace ID")
    parent_agent_run_id: Optional[str] = Field(None, description="Parent agent execution run ID if invoked from Harness")


class AIProgramResult(BaseModel):
    """Standardized result returned by AIProgramRuntime implementations."""

    program_key: str
    program_version: str
    status: Literal["completed", "failed", "validation_failed", "skipped"]

    output: Optional[Dict[str, Any]] = None
    user_visible_rationale: Optional[str] = None
    error_message: Optional[str] = None

    model_profile: str = "default"
    latency_ms: Optional[int] = None
    usage: Dict[str, Any] = Field(default_factory=dict)

    metric_snapshot: Optional[Dict[str, Any]] = None
    artifact_hash: Optional[str] = None
    engine: str = "dspy"


# --- Specific Program Schemas ---

class CEOBriefInput(BaseModel):
    """Input contract for ceo.brief program."""

    company_cycle: Dict[str, Any] = Field(default_factory=dict, description="Active cycle objectives & target")
    okr_deltas: List[Dict[str, Any]] = Field(default_factory=list, description="Key Result updates and gap metrics")
    weekly_mission: Dict[str, Any] = Field(default_factory=dict, description="Current weekly mission & work items")
    sales_signals: List[Dict[str, Any]] = Field(default_factory=list, description="Sales pipeline & conversion signals")
    finance_signals: List[Dict[str, Any]] = Field(default_factory=list, description="Cashflow & budget variance alerts")
    legal_tech_signals: List[Dict[str, Any]] = Field(default_factory=list, description="Legal risks & Tech blockers")
    pending_approvals: List[Dict[str, Any]] = Field(default_factory=list, description="Consequential actions awaiting founder review")


class CEOBriefOutput(BaseModel):
    """Output contract for ceo.brief program."""

    headline: str = Field(..., description="Crisp 1-line headline of the company current status")
    wins: List[str] = Field(default_factory=list, description="Key validated accomplishments")
    risks: List[str] = Field(default_factory=list, description="Active risks requiring attention")
    exceptions: List[str] = Field(default_factory=list, description="Out-of-norm operational anomalies")
    decisions_required: List[str] = Field(default_factory=list, description="Pending decisions awaiting founder judgment")
    today_top_3: List[str] = Field(default_factory=list, description="Top 3 high-leverage focus items")
    watch_next: List[str] = Field(default_factory=list, description="Items to monitor in upcoming days")


class LeadQualificationInput(BaseModel):
    """Input contract for sales.lead_qualification program."""

    lead: Dict[str, Any] = Field(..., description="Lead contact and company information")
    company_context: Dict[str, Any] = Field(default_factory=dict, description="Offering context and value proposition")
    interaction_history: List[Dict[str, Any]] = Field(default_factory=list, description="Past messages and touchpoints")
    icp_profile: Dict[str, Any] = Field(default_factory=dict, description="Ideal Customer Profile criteria")


class LeadQualificationOutput(BaseModel):
    """Output contract for sales.lead_qualification program."""

    fit_score: float = Field(..., ge=0.0, le=1.0, description="ICP fit score from 0.0 to 1.0")
    need_score: float = Field(..., ge=0.0, le=1.0, description="Urgency / need clarity score")
    timing_score: float = Field(..., ge=0.0, le=1.0, description="Buying timing score")
    authority_signal: str = Field("unknown", description="Decision maker level (decision_maker, influencer, gatekeeper, unknown)")
    budget_signal: str = Field("unknown", description="Budget capability indicator (verified, probable, constrained, unknown)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the evaluation")
    evidence: List[str] = Field(default_factory=list, description="Grounding facts from interaction history")
    disqualifiers: List[str] = Field(default_factory=list, description="Any disqualifying factors found")
    recommended_stage: str = Field(..., description="Suggested CRM stage (e.g. 'discovery', 'qualified', 'nurture', 'disqualified')")
    recommended_next_action: str = Field(..., description="Concrete actionable next step")
