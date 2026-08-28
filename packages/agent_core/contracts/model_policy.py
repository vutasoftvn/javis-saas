from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from agent_core.governance.contracts import PinnedSpecIdentity
from agent_core.governance.hashing import definition_hash

__all__ = ["ModelPolicySpec"]


class ModelPolicySpec(BaseModel):
    """Đặc tả model/provider policy có thể publish/pin độc lập khỏi AgentSpec
    — theo ADR-ARTIFACT-IDENTITY-001 (spec_kind="model_policy"). Chỉ gồm
    `model`/`temperature` — 2 field duy nhất hiện có consumer thật
    (packages/agent_core/kernel/openai_agents_kernel.py). AgentSpec.model_policy
    (dict thô) vẫn là fallback cho spec chưa pin qua AgentSpec.model_policy_ref."""

    id: str
    version: str = "1.0.0"
    model: str = "deepseek-chat"
    temperature: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)
    definition_hash: str | None = None

    def compute_hash(self) -> str:
        """Tính SHA-256 hash chuẩn hoá cho toàn bộ nội dung của spec."""
        data = self.model_dump(exclude={"definition_hash"})
        return definition_hash(data)

    def with_hash(self) -> ModelPolicySpec:
        """Trả về bản sao của ModelPolicySpec đã được gắn definition_hash xác thực."""
        return self.model_copy(update={"definition_hash": self.compute_hash()})

    def to_pinned_identity(self) -> PinnedSpecIdentity:
        """Chuyển đổi sang PinnedSpecIdentity để pin vào AgentSpec.model_policy_ref
        hoặc ghi vào SpecResolutionManifest."""
        h = self.definition_hash or self.compute_hash()
        return PinnedSpecIdentity(
            spec_kind="model_policy",
            spec_id=self.id,
            spec_version=self.version,
            definition_hash=h,
        )
