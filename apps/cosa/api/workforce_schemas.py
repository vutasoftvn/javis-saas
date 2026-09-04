"""Workforce API Pydantic Schemas."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CreateAssignmentRequest(BaseModel):
    functional_key: str
    reports_to_assignment_id: UUID | None = None


class WorkforceAssignmentOut(BaseModel):
    assignment_id: str
    workspace_id: str
    functional_key: str
    spec_id: str
    spec_version: str
    definition_hash: str
    reports_to_assignment_id: str | None = None
    configured_by: str
    status: str
    created_at: str
    retired_at: str | None = None


class WorkforceCompositionEntry(BaseModel):
    functional_key: str
    title: str
    description: str
    spec_id: str
    spec_version: str
    definition_hash: str
    allowed_capability_prefixes: list[str]
    assigned: bool
    assignment_id: str | None = None
    status: str | None = None
    eligibility_reasons: list[str] = Field(default_factory=list)


class WorkforceRosterEntryOut(BaseModel):
    id: int
    key: str
    name: str
    role_title: str
    department: str
    agent_type: str
    default_model_profile: str
    risk_level: int
    status: str
    enabled: bool


_ARTIFACT_STATUS_MAP = {"available": "READY", "failed": "FAILED", "archived": "ARCHIVED"}


class WorkforceWorkProductOut(BaseModel):
    id: str
    title: str
    product_type: str
    status: str
    author_agent_key: str
    object_ref: str
    created_at: str


class WorkforceExceptionOut(BaseModel):
    id: str
    exception_type: str
    tier: str
    status: str
    agent_key: str
    created_at: str


class WorkforceExceptionListOut(BaseModel):
    total: int
    founder_gate_count: int
    lead_notify_count: int
    has_critical: bool
    escalations: list[WorkforceExceptionOut]


class WorkforceOrgChartNode(BaseModel):
    assignment_id: str
    functional_key: str
    spec_id: str
    status: str
    reports_to_assignment_id: str | None = None
    direct_reports: list[WorkforceOrgChartNode] = Field(default_factory=list)


class WorkforceOrgChartOut(BaseModel):
    roots: list[WorkforceOrgChartNode] = Field(default_factory=list)
    total_assignments: int = 0


class WorkforceCapabilityOut(BaseModel):
    capability_ref: str
    functional_key: str
    spec_id: str
    spec_version: str
    status: str


class WorkforceCostObservationOut(BaseModel):
    observation_id: str
    workspace_id: str
    run_id: str
    provider_key: str
    model_key: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_amount: float | None = None
    currency: str | None = None
    observed_at: str


class WorkforceHealthOut(BaseModel):
    assignment_id: str
    functional_key: str
    status: Literal["healthy", "degraded", "failed", "not_observed"]
    observed_at: str | None = None
    source_ref: str | None = None
    last_run_id: str | None = None
    message: str | None = None


class WorkforceRunSummaryOut(BaseModel):
    run_id: str
    workspace_id: str
    agent_spec_id: str
    agent_spec_version: str
    definition_hash: str
    status: str
    created_at: str
    completed_at: str | None = None
    total_tokens: int | None = None
    error_message: str | None = None


class WorkforceRunDetailOut(BaseModel):
    run_id: str
    workspace_id: str
    agent_spec_id: str
    agent_spec_version: str
    definition_hash: str
    status: str
    created_at: str
    completed_at: str | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_payload: dict[str, Any] | None = None
    error_message: str | None = None


class WorkforceRunEventOut(BaseModel):
    event_id: str
    run_id: str
    sequence: int
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class WorkforceRunArtifactOut(BaseModel):
    artifact_id: str
    run_id: str
    artifact_type: str
    uri: str
    created_at: str


class CreateScheduleRequest(BaseModel):
    name: str
    functional_key: str
    cron_expression: str
    input_payload: dict[str, Any] = Field(default_factory=dict)


class ScheduleOut(BaseModel):
    schedule_id: str
    workspace_id: str
    name: str
    functional_key: str
    cron_expression: str
    status: str
    next_run_at: str | None = None
    created_at: str


class RunScheduleNowOut(BaseModel):
    schedule_id: str
    triggered_run_id: str
    status: str


class ApprovalOut(BaseModel):
    approval_id: str
    workspace_id: str
    run_id: str
    capability_ref: str
    action_class: str
    status: str
    requested_at: str
    decided_at: str | None = None
    decision: str | None = None
    reason: str | None = None


class ApprovalDecisionRequest(BaseModel):
    decision: Literal["APPROVED", "REJECTED"] | None = None
    approved: bool | None = None
    reason: str | None = None


class ApprovalDecisionOut(BaseModel):
    approval_id: str
    status: str
    decided_at: str
    reason: str | None = None
