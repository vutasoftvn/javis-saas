from __future__ import annotations

import hashlib
from typing import Any, Literal

from pydantic import BaseModel, Field


class ExecutiveBoardInputError(Exception):
    """Raised when an executive board input violation occurs."""

    pass


def _sha256_lines(parts: list[str]) -> str:
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


class ProjectDeploymentPin(BaseModel):
    """Quyền dùng profile trong đúng Project (Company là chủ) — không suy từ role key."""

    project_agent_deployment_id: str
    profile_key: str
    spec_id: str
    spec_version: str
    spec_hash: str

    def identity_hash(self) -> str:
        # Định dạng phải khớp services/company/operations/services/executive-pin-hash.ts.
        return _sha256_lines(
            [
                self.project_agent_deployment_id,
                self.profile_key,
                self.spec_id,
                self.spec_version,
                self.spec_hash,
            ]
        )


class PinnedSkillIdentity(BaseModel):
    skill_id: str
    version: str
    definition_hash: str


class AdvisorOverlayPin(BaseModel):
    """AgentSpec overlay advisory bất biến — không có quyền Project độc lập."""

    role_key: str
    overlay_spec_id: str
    overlay_spec_version: str
    overlay_spec_hash: str
    skill_pins: tuple[PinnedSkillIdentity, ...] = Field(default_factory=tuple)

    def identity_hash(self) -> str:
        return _sha256_lines(
            [
                self.role_key,
                self.overlay_spec_id,
                self.overlay_spec_version,
                self.overlay_spec_hash,
                *(f"{p.skill_id}@{p.version}#{p.definition_hash}" for p in self.skill_pins),
            ]
        )


class SelectedAdvisorExecutionPin(BaseModel):
    role_key: str
    deployment: ProjectDeploymentPin
    overlay: AdvisorOverlayPin


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
    execution_pin: SelectedAdvisorExecutionPin
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)
    peer_drafts: list[dict[str, Any]] | None = None
    mock_model_output: dict[str, Any] | None = None
    context_snapshot_age_weeks: int = 0


class DissentRecord(BaseModel):
    role_key: str
    advisor_name: str
    unresolved_concern: str
    recommended_alternative: str | None = None
    preserved_at_week: int | None = None


class BindingCriteria(BaseModel):
    success_criteria: list[str] = Field(default_factory=list)
    kill_criteria: list[str] = Field(default_factory=list)
    review_checkpoint_week: int | None = None


class BoardroomMemo(BaseModel):
    deliberation_id: str
    question: str
    recommended_option: str
    vote_tally: dict[str, str] = Field(default_factory=dict)  # role_key -> option_title
    preserved_dissent: list[DissentRecord] = Field(default_factory=list)
    devils_advocate_concerns: list[str] = Field(default_factory=list)
    binding_criteria: BindingCriteria = Field(default_factory=BindingCriteria)
    status: Literal["AWAITING_FOUNDER_DECISION", "APPROVED", "REJECTED"] = (
        "AWAITING_FOUNDER_DECISION"
    )
    context_snapshot_id: str | None = None
    context_snapshot_age_weeks: int = 0
    evidence_tag: str | None = None


class ExecutiveAnalysisOutcome(BaseModel):
    kind: Literal["executive.analysis.completed.v1", "executive.analysis.failed.v1"]
    deliberation_id: str
    frame_version: int
    role_key: str
    descriptor: dict[str, Any] | None = None
    error_detail: str | None = None
    context_snapshot_age_weeks: int | None = None
    evidence_tag: str | None = None
    # Hash pin đã thực thi — Company chỉ nhận callback khi bằng đúng pin của frame.
    deployment_pin_hash: str | None = None
    overlay_pin_hash: str | None = None


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
