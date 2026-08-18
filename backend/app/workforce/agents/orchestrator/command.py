"""Typed command definitions and models for Shared Work Orchestrator."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

from app.core.snowflake import generate_snowflake_id


class CommandCategory(str, Enum):
    INQUIRY = "inquiry"
    PROGRESS_UPDATE = "progress_update"
    REPORT_REQUEST = "report_request"
    PLAN_CYCLE_COMMAND = "plan_cycle_command"
    WORK_COMMAND = "work_command"
    APPROVAL_COMMAND = "approval_command"


class CommandRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OrchestratorRequest(BaseModel):
    category: CommandCategory
    action: str
    target_resource_type: Optional[str] = None
    target_resource_id: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    client_context: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None


class PolicyEvaluation(BaseModel):
    allowed: bool
    requires_approval: bool
    risk_level: CommandRiskLevel
    reason: str


class OrchestratorResponse(BaseModel):
    command_id: str
    status: Literal["executed", "proposal_created", "rejected", "answered"]
    category: CommandCategory
    action: str
    result: Optional[dict[str, Any]] = None
    proposal_id: Optional[str] = None
    message: str
    executed_at: Optional[datetime] = None
