from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

__all__ = [
    "EvalCategory",
    "EvalResult",
    "EvalSuiteSummary",
    "EvalTestCase",
    "EventFixture",
    "EventTriggerEvalSuite",
    "InjectionScenario",
]


class EvalCategory(enum.StrEnum):
    KERNEL_CAPABILITY = "kernel_capability"  # Group 1: Model & Kernel capability
    BUSINESS_CORRECTNESS = "business_correctness"  # Group 2: Business correctness & DAG execution
    DURABILITY_RECOVERY = (
        "durability_recovery"  # Group 3: Durability, checkpoints & idempotent replay
    )
    SECURITY_GOVERNANCE = "security_governance"  # Group 4: Security invariants & governance drift


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
    error: str | None = None
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvalSuiteSummary(BaseModel):
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    category_scores: dict[str, float] = Field(default_factory=dict)
    results: list[EvalResult] = Field(default_factory=list)


class EventFixture(BaseModel):
    """Một event mẫu cho eval suite của trigger rule."""

    fixture_id: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class InjectionScenario(BaseModel):
    """Kịch bản bơm lỗi bắt buộc phải cover (duplicate delivery, policy denied, ...)."""

    name: str
    description: str = ""


class EventTriggerEvalSuite(BaseModel):
    """Ngữ cảnh bất biến của một lần eval trigger rule — event schema version,
    fixtures, policy version, action boundary kỳ vọng, failure injection.
    Evidence sinh từ suite này gắn vào EventTriggerRule.eval_evidence_ref (P1 Task 8)."""

    event_schema_version: int
    input_fixtures: tuple[EventFixture, ...]
    policy_version: str
    expected_action_boundary: str  # "artifact_only" | "proposal" | "write"
    failure_injection: tuple[InjectionScenario, ...]

    @staticmethod
    def eval_category() -> EvalCategory:
        return EvalCategory.SECURITY_GOVERNANCE
