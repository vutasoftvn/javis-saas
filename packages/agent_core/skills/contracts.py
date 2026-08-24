"""Skill Contracts and Specifications (Track 9D).

Theo Hermes/LangGraph Integration Plan §3 (Track 9D, HL-04, HL-05):
Định nghĩa SkillSpec bất biến, SkillStatus, SkillCandidate, và Progressive Disclosure (L0/L1/L2).
Lưu ý: Runtime consumption qua floating ref bị CẤM cho đến khi có ADR-SKILL-IDENTITY (Phase 10).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field

from agent_core.contracts.identity import PinnedSkillRef

__all__ = [
    "SkillStatus",
    "SkillIndexEntry",
    "SkillSpec",
    "SkillCandidate",
    "PinnedSkillRef",
]


class SkillStatus(str, Enum):
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
    applicability: dict[str, Any] = Field(default_factory=dict)
    required_capabilities: list[str] = Field(default_factory=list)
    required_knowledge: list[str] = Field(default_factory=list)
    references: dict[str, Any] = Field(default_factory=dict)  # L2 reference templates/examples
    status: SkillStatus = SkillStatus.PUBLISHED
    publisher: str = "cosa_platform"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    definition_hash: Optional[str] = None

    def compute_hash(self) -> str:
        data = {
            "id": self.id,
            "version": self.version,
            "instructions": self.instructions,
            "required_capabilities": sorted(self.required_capabilities),
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
