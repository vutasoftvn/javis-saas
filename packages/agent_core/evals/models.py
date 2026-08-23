from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from pydantic import BaseModel, Field

__all__ = ["EvalCategory", "EvalTestCase", "EvalResult", "EvalSuiteSummary"]


class EvalCategory(str, enum.Enum):
    KERNEL_CAPABILITY = "kernel_capability"          # Group 1: Model & Kernel capability
    BUSINESS_CORRECTNESS = "business_correctness"    # Group 2: Business correctness & DAG execution
    DURABILITY_RECOVERY = "durability_recovery"      # Group 3: Durability, checkpoints & idempotent replay
    SECURITY_GOVERNANCE = "security_governance"      # Group 4: Security invariants & governance drift


class EvalTestCase(BaseModel):
    id: str
    name: str
    category: EvalCategory
    description: str
    expected_outcome: str = "pass"
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvalResult(BaseModel):
    case_id: str
    category: EvalCategory
    passed: bool
    score: float = 1.0
    duration_ms: float = 0.0
    details: str = ""
    error: Optional[str] = None
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvalSuiteSummary(BaseModel):
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    category_scores: dict[str, float] = Field(default_factory=dict)
    results: list[EvalResult] = Field(default_factory=list)
