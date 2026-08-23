from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from agent_core.governance.contracts import AutonomyLevel, PinnedSpecIdentity
from agent_core.governance.hashing import definition_hash

__all__ = ["AgentSpec"]


class AgentSpec(BaseModel):
    """Đặc tả Agent có thể thực thi theo Master Guide §6.1.
    
    Yêu cầu tính bất biến và định danh nội dung: `definition_hash` là bắt buộc
    để chống silent drift khi spec được publish hoặc nạp vào Run.
    """

    id: str
    version: str = "1.0.0"
    instructions: str = ""
    model_policy: dict[str, Any] = Field(default_factory=dict)
    autonomy_level: AutonomyLevel = AutonomyLevel.L1
    capability_refs: list[str] = Field(default_factory=list)
    memory_policy: dict[str, Any] = Field(default_factory=dict)
    knowledge_policy: dict[str, Any] = Field(default_factory=dict)
    coordination_policy: dict[str, Any] = Field(default_factory=dict)
    limits: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    definition_hash: Optional[str] = None

    def compute_hash(self) -> str:
        """Tính SHA-256 hash chuẩn hoá cho toàn bộ nội dung của spec."""
        data = self.model_dump(exclude={"definition_hash"})
        return definition_hash(data)

    def with_hash(self) -> "AgentSpec":
        """Trả về bản sao của AgentSpec đã được gắn definition_hash xác thực."""
        return self.model_copy(update={"definition_hash": self.compute_hash()})

    def to_pinned_identity(self) -> PinnedSpecIdentity:
        """Chuyển đổi sang PinnedSpecIdentity để ghi vào SpecResolutionManifest."""
        h = self.definition_hash or self.compute_hash()
        return PinnedSpecIdentity(
            spec_kind="agent",
            spec_id=self.id,
            spec_version=self.version,
            definition_hash=h,
        )
