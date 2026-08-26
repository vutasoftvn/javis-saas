from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from agent_core.governance.contracts import PinnedSpecIdentity
from agent_core.governance.hashing import definition_hash

__all__ = ["EvalSuite"]


class EvalSuite(BaseModel):
    """Đặc tả eval suite có thể publish/pin độc lập — theo
    ADR-ARTIFACT-IDENTITY-001 (spec_kind="eval_suite", Wave M3). `case_ids`
    chỉ tham chiếu ID case đã có trong `agent_evals.cases` (migration 008),
    KHÔNG persist nội dung case ở đây — publish case là việc ngoài phạm vi
    Wave M3 này. Fingerprint bao gồm case_ids (không phân biệt thứ tự —
    một suite là 1 TẬP case, đổi thứ tự không đổi ý nghĩa) + scorer_version +
    pass_thresholds — loại trừ runtime execution context (worker/region/...)."""

    id: str
    version: str = "1.0.0"
    target_kind: str  # "agent" | "skill" | "workflow" — khớp agent_evals.suites.target_kind
    target_id: str
    name: str = ""
    case_ids: list[str] = Field(default_factory=list)
    scorer_version: str = "1.0"
    pass_thresholds: dict[str, float] = Field(default_factory=dict)
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    definition_hash: Optional[str] = None

    def compute_hash(self) -> str:
        """Tính SHA-256 hash chuẩn hoá — case_ids được sort để đảm bảo thứ tự
        không ảnh hưởng fingerprint (unordered set semantics)."""
        data = self.model_dump(exclude={"definition_hash"})
        data["case_ids"] = sorted(data["case_ids"])
        return definition_hash(data)

    def with_hash(self) -> "EvalSuite":
        """Trả về bản sao của EvalSuite đã được gắn definition_hash xác thực."""
        return self.model_copy(update={"definition_hash": self.compute_hash()})

    def to_pinned_identity(self) -> PinnedSpecIdentity:
        """Chuyển đổi sang PinnedSpecIdentity để pin vào EvalRun.suite_ref."""
        h = self.definition_hash or self.compute_hash()
        return PinnedSpecIdentity(
            spec_kind="eval_suite",
            spec_id=self.id,
            spec_version=self.version,
            definition_hash=h,
        )
