from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field

__all__ = ["EvalCase", "SkillCandidateRecord", "SkillMutationRecord"]


class EvalCase(BaseModel):
    """1 test case cho Skill Optimization Lab — theo bảng agent_evals.cases
    (migration 008). `is_holdout=True` nghĩa là case CHỈ dùng ở full regression
    cuối cùng, không dùng để chấm điểm từng round mutation (chống overfit vào
    chính bộ case dùng để tối ưu — Blueprint V2 §69.3)."""

    case_id: str = Field(default_factory=lambda: f"case_{uuid.uuid4().hex[:8]}")
    input_payload: dict[str, Any] = Field(default_factory=dict)
    expected_outcome: dict[str, Any] = Field(default_factory=dict)
    is_holdout: bool = False


class SkillCandidateRecord(BaseModel):
    """Tương ứng agent_evals.skill_candidates (migration 008)."""

    candidate_id: str = Field(default_factory=lambda: f"cand_{uuid.uuid4().hex[:12]}")
    base_skill_id: str
    base_skill_version: str
    base_definition_hash: str
    proposed_content: dict[str, Any]
    status: str = "candidate"  # candidate | evaluated | approved | rejected | published
    baseline_score: Optional[float] = None
    latest_score: Optional[float] = None
    round_no: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SkillMutationRecord(BaseModel):
    """Tương ứng agent_evals.skill_mutations (migration 008)."""

    mutation_id: str = Field(default_factory=lambda: f"mut_{uuid.uuid4().hex[:12]}")
    candidate_id: str
    round_no: int
    diff_summary: str
    rationale: str = ""
    pre_score: Optional[float] = None
    post_score: Optional[float] = None
    accepted: bool = False
    eval_run_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
