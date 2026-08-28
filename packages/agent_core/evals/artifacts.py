from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from agent_core.governance.contracts import PinnedSpecIdentity
from agent_core.governance.hashing import definition_hash

__all__ = ["EvalCaseResult", "EvalRun", "EvalSuite"]


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
    definition_hash: str | None = None

    def compute_hash(self) -> str:
        """Tính SHA-256 hash chuẩn hoá — case_ids được sort để đảm bảo thứ tự
        không ảnh hưởng fingerprint (unordered set semantics)."""
        data = self.model_dump(exclude={"definition_hash"})
        data["case_ids"] = sorted(data["case_ids"])
        return definition_hash(data)

    def with_hash(self) -> EvalSuite:
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


class EvalRun(BaseModel):
    """Một lần thực thi eval — khác `EvalSuite` (định nghĩa tái dùng được) ở
    chỗ EvalRun là execution instance. `suite_ref` là Optional vì Skill
    Optimization Lab (Wave M3 Task 6) chạy eval ad-hoc theo case list truyền
    trực tiếp vào `optimize()`, không phải lúc nào cũng gắn với 1 EvalSuite
    đã publish — chỉ suite thật (dùng cho promotion evidence, Wave M4) mới
    có suite_ref khác None."""

    run_id: str = Field(default_factory=lambda: f"evalrun_{uuid.uuid4().hex[:12]}")
    target_ref: PinnedSpecIdentity
    suite_ref: PinnedSpecIdentity | None = None
    status: str = "running"  # running | completed | failed
    pass_rate: float | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


class EvalCaseResult(BaseModel):
    """Kết quả 1 case trong 1 EvalRun — đặt tên khác `EvalResult`
    (agent_core.evals.models, domain platform-conformance khác) để tránh
    trùng khi cùng export qua `agent_core.evals`."""

    result_id: str = Field(default_factory=lambda: f"evalresult_{uuid.uuid4().hex[:12]}")
    eval_run_id: str
    case_id: str
    passed: bool
    score: float = 0.0
    details: str = ""
    error: str | None = None
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
