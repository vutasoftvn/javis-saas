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


EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["conclusion", "options", "evidence_claims"],
    "properties": {
        "conclusion": {"type": "string", "minLength": 1},
        "options": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["title", "trade_off"],
                "properties": {
                    "title": {"type": "string"},
                    "trade_off": {"type": "string"},
                },
            },
        },
        "evidence_claims": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["claim", "source_ref"],
                "properties": {
                    "claim": {"type": "string"},
                    "source_ref": {"type": "string"},
                },
            },
        },
        "assumptions": {"type": "array", "items": {"type": "string"}},
        "risks_and_unknowns": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "human_review_required": {"type": "boolean"},
    },
}
