"""Skill Contracts and Specifications (Track 9D / Tranche A).

Định nghĩa SkillSpec bất biến, SkillStatus, SkillCandidate, LifecycleApplicability,
AutonomyPolicy, EvidenceRequirement, SkillQualitySpec và Progressive Disclosure (L0/L1/L2).
Lưu ý: Runtime consumption qua floating ref bị CẤM (ADR-SKILL-IDENTITY).
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

from agent.contracts.identity import PinnedSkillRef

__all__ = [
    "AutonomyPolicy",
    "EvidenceRequirement",
    "LifecycleApplicability",
    "PinnedSkillRef",
    "ProjectLifecycleStage",
    "SkillCandidate",
    "SkillIndexEntry",
    "SkillQualitySpec",
    "SkillSpec",
    "SkillStatus",
]


class ProjectLifecycleStage(StrEnum):
    P0_DISCOVERY = "P0_DISCOVERY"
    P1_PROBLEM_VALIDATION = "P1_PROBLEM_VALIDATION"
    P2_SOLUTION_VALIDATION = "P2_SOLUTION_VALIDATION"
    P3_BUILD_VALIDATE = "P3_BUILD_VALIDATE"
    P4_GO_TO_MARKET = "P4_GO_TO_MARKET"
    P5_OPERATE_GROWTH = "P5_OPERATE_GROWTH"
    P6_SCALE_GOVERN = "P6_SCALE_GOVERN"


class LifecycleApplicability(BaseModel):
    project_stages: list[ProjectLifecycleStage] = Field(
        default_factory=lambda: [ProjectLifecycleStage.P0_DISCOVERY]
    )
    gates: list[str] = Field(default_factory=list)
    required_context: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)


class AutonomyPolicy(BaseModel):
    ceiling: Literal["L0_OBSERVE", "L1_PROPOSE", "L2_BOUNDED"] = "L0_OBSERVE"
    side_effect_class: Literal["R", "A", "B", "X", "M", "D"] = "R"


class EvidenceRequirement(BaseModel):
    min_source_refs: int = Field(default=0, ge=0)
    freshness_days: int | None = Field(default=None, ge=1)
    self_validation_forbidden: bool = True


class SkillQualitySpec(BaseModel):
    eval_suite: str = Field(..., min_length=1)
    required_negative_cases: list[str] = Field(default_factory=list, min_length=1)


class SkillStatus(StrEnum):
    DRAFT = "DRAFT"
    CANDIDATE = "CANDIDATE"
    EVALUATED = "EVALUATED"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    RETIRED = "RETIRED"


class SkillIndexEntry(BaseModel):
    """L0 Skill Index: Chỉ nạp metadata định danh và mô tả ngắn gọn."""

    id: str
    version: str
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    definition_hash: str


class SkillSpec(BaseModel):
    """L1 Skill Specification: Định nghĩa đầy đủ chỉ dẫn chuyên môn bất biến."""

    id: str
    version: str = "1.0.0"
    name: str = ""
    description: str = ""
    instructions: str = ""
    applicability: LifecycleApplicability = Field(default_factory=LifecycleApplicability)
    autonomy: AutonomyPolicy = Field(default_factory=AutonomyPolicy)
    evidence_requirement: EvidenceRequirement = Field(default_factory=EvidenceRequirement)
    quality: SkillQualitySpec | None = None
    required_capabilities: list[str] = Field(default_factory=list)
    required_knowledge: list[str] = Field(default_factory=list)
    references: dict[str, Any] = Field(default_factory=dict)  # L2 reference templates/examples
    status: SkillStatus = SkillStatus.PUBLISHED
    publisher: str = "cosa_platform"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    definition_hash: str | None = None

    def compute_hash(self) -> str:
        data = {
            "id": self.id,
            "version": self.version,
            "instructions": self.instructions,
            "applicability": self.applicability.model_dump(mode="json"),
            "autonomy": self.autonomy.model_dump(mode="json"),
            "evidence_requirement": self.evidence_requirement.model_dump(mode="json"),
            "quality": self.quality.model_dump(mode="json") if self.quality else None,
            "required_capabilities": sorted(self.required_capabilities),
            "required_knowledge": sorted(self.required_knowledge),
            "references": self.references,
        }
        raw = json.dumps(data, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def to_index_entry(self) -> SkillIndexEntry:
        return SkillIndexEntry(
            id=self.id,
            version=self.version,
            name=self.name or self.id,
            description=self.description,
            definition_hash=self.definition_hash or self.compute_hash(),
        )


class SkillCandidate(BaseModel):
    candidate_id: str
    parent_run_id: str
    proposed_skill: SkillSpec
    evidence_refs: list[str] = Field(default_factory=list)
    eval_score: float = 0.0
    status: SkillStatus = SkillStatus.CANDIDATE
