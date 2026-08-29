from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from agent.governance.contracts import PinnedSpecIdentity
from agent.governance.hashing import definition_hash

__all__ = ["PromptSpec"]


class PromptSpec(BaseModel):
    """Đặc tả prompt có thể publish/pin độc lập khỏi AgentSpec — theo
    ADR-ARTIFACT-IDENTITY-001 (dùng PinnedSpecIdentity, spec_kind="prompt",
    không tạo ArtifactRef riêng). `text` là nội dung instruction thật;
    `AgentSpec.instructions` (string thô) vẫn là fallback cho spec chưa pin
    prompt qua `AgentSpec.prompt_ref` — resolve ưu tiên prompt_ref khi có
    (việc resolve thật thuộc Wave M2b, runtime wiring, ngoài phạm vi module
    contracts/ thuần này)."""

    id: str
    version: str = "1.0.0"
    text: str = ""
    variables: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    definition_hash: str | None = None

    def compute_hash(self) -> str:
        """Tính SHA-256 hash chuẩn hoá cho toàn bộ nội dung của spec."""
        data = self.model_dump(exclude={"definition_hash"})
        return definition_hash(data)

    def with_hash(self) -> PromptSpec:
        """Trả về bản sao của PromptSpec đã được gắn definition_hash xác thực."""
        return self.model_copy(update={"definition_hash": self.compute_hash()})

    def to_pinned_identity(self) -> PinnedSpecIdentity:
        """Chuyển đổi sang PinnedSpecIdentity để pin vào AgentSpec.prompt_ref
        hoặc ghi vào SpecResolutionManifest."""
        h = self.definition_hash or self.compute_hash()
        return PinnedSpecIdentity(
            spec_kind="prompt",
            spec_id=self.id,
            spec_version=self.version,
            definition_hash=h,
        )
