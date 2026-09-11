from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class ExecutiveBoardInputError(Exception):
    """Raised when an executive board input violation occurs."""
    pass


class RolePin(BaseModel):
    role_key: str
    assignment_id: str
    spec_id: str
    spec_version: str
    spec_hash: str
    skill_pins: tuple[str, ...] = Field(default_factory=tuple)


class EvidenceRef(BaseModel):
    source_ref: str
    source_hash: str
    classification: str = "internal"
    project_id: str | None = None


class ExecutiveAnalysisRequest(BaseModel):
    workspace_id: str
    project_id: str
    deliberation_id: str
    frame_version: int
    role_key: str
    question: str
    role_pin: RolePin
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)
    peer_drafts: list[dict[str, Any]] | None = None
    mock_model_output: dict[str, Any] | None = None


class ExecutiveAnalysisOutcome(BaseModel):
    kind: Literal["executive.analysis.completed.v1", "executive.analysis.failed.v1"]
    deliberation_id: str
    frame_version: int
    role_key: str
    descriptor: dict[str, Any] | None = None
    error_detail: str | None = None
