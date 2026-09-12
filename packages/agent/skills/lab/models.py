from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

__all__ = ["EvalCase", "OptimizationResult", "SkillCandidateRecord", "SkillMutationRecord"]


class EvalCase(BaseModel):
    """1 test case cho Skill Optimization Lab.
    `is_holdout=True` nghĩa là case CHỈ dùng ở full regression
    cuối cùng, không dùng để chấm điểm từng round mutation."""

    case_id: str = Field(default_factory=lambda: f"case_{uuid.uuid4().hex[:8]}")
    input_payload: dict[str, Any] = Field(default_factory=dict)
    expected_outcome: dict[str, Any] = Field(default_factory=dict)
    is_holdout: bool = False


class SkillCandidateRecord(BaseModel):
    """In-memory candidate record dùng trong quá trình lab optimize."""

    candidate_id: str = Field(default_factory=lambda: f"cand_{uuid.uuid4().hex[:12]}")
    base_skill_id: str
    base_skill_version: str
    base_definition_hash: str
    proposed_content: dict[str, Any]
    status: str = "candidate"  # candidate | evaluated | approved | rejected | published
    baseline_score: float | None = None
    latest_score: float | None = None
    round_no: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SkillMutationRecord(BaseModel):
    """In-memory mutation record của từng round tối ưu trong lab."""

    mutation_id: str = Field(default_factory=lambda: f"mut_{uuid.uuid4().hex[:12]}")
    candidate_id: str
    round_no: int
    diff_summary: str
    rationale: str = ""
    pre_score: float | None = None
    post_score: float | None = None
    accepted: bool = False
    eval_run_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class OptimizationResult(BaseModel):
    """Kết quả hoàn chỉnh, bất biến trả về từ SkillOptimizationLab."""

    candidate_id: str
    base_skill_id: str
    base_skill_version: str
    base_definition_hash: str
    proposed_content: dict[str, Any]
    status: str = "evaluated"
    baseline_score: float = 0.0
    latest_score: float = 0.0
    final_score: float = 0.0
    round_no: int = 0
    improved: bool = False
    mutations: list[SkillMutationRecord] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
