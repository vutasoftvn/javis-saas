"""Workforce persistence models and typed records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class WorkforceAssignmentRecord:
    assignment_id: UUID
    workspace_id: str
    functional_key: str
    spec_id: str
    spec_version: str
    definition_hash: str
    reports_to_assignment_id: UUID | None
    configured_by: str
    status: Literal["ACTIVE", "RETIRED"]
    created_at: datetime
    retired_at: datetime | None = None


@dataclass(frozen=True)
class RuntimeSignalOutboxRecord:
    outbox_id: UUID
    workspace_id: str
    source_kind: str
    source_id: str
    sequence: int
    state: str
    observed_at: datetime
    correlation_id: str
    payload_hash: str
    state_delivery: Literal["PENDING", "DELIVERED", "FAILED"]
    attempt_count: int
    next_attempt_at: datetime
    delivered_at: datetime | None = None


@dataclass(frozen=True)
class RunCostObservationRecord:
    observation_id: UUID
    workspace_id: str
    run_id: str
    provider_key: str
    model_key: str
    input_tokens: int | None
    output_tokens: int | None
    cost_amount: Decimal | float | None
    currency: str | None
    observed_at: datetime
