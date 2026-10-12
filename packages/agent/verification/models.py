"""Mô hình kết quả kiểm tra tiêu chí hoàn thành (Dự án B)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

__all__ = ["ArtifactFact", "CriterionResult", "CriterionVerdict", "RunFacts", "Verdict"]


class Verdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"


class CriterionVerdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    UNCLEAR = "unclear"


@dataclass(frozen=True)
class CriterionResult:
    id: str
    required: bool
    check: str  # "deterministic" | "rubric"
    verdict: CriterionVerdict
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "required": self.required,
            "check": self.check,
            "verdict": self.verdict.value,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ArtifactFact:
    kind: str
    display_name: str


@dataclass(frozen=True)
class RunFacts:
    """Dữ kiện có thật về một run đã xong, dùng cho đánh giá tất định."""

    output_text: str
    structured_output: dict[str, Any] | None
    artifacts: tuple[ArtifactFact, ...]
    # Giá trị KR hiện tại / trước khi chạy, khóa = key_result_id (chuỗi); None = không đọc được.
    metrics: Mapping[str, float | None] = field(default_factory=dict)
    metrics_before: Mapping[str, float | None] = field(default_factory=dict)
