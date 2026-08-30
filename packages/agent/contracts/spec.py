from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

from agent.contracts.capability import CapabilityImplementationIdentity
from agent.contracts.identity import PinnedSkillRef
from agent.governance.contracts import AutonomyLevel, PinnedSpecIdentity
from agent.governance.hashing import definition_hash

__all__ = ["AgentSpec"]


class AgentSpec(BaseModel):
    """Đặc tả Agent có thể thực thi theo Master Guide §6.1.

    Yêu cầu tính bất biến và định danh nội dung: `definition_hash` là bắt buộc
    để chống silent drift khi spec được publish hoặc nạp vào Run.

    `prompt_ref`/`model_policy_ref` pin Prompt/ModelPolicy đã publish (nếu có)
    — khi None, `instructions`/`model_policy` (dạng string/dict thô) vẫn là
    fallback (Wave M2, ADR-ARTIFACT-IDENTITY-001 §3). `tool_contract_refs`
    dùng CapabilityImplementationIdentity (không phải PinnedSpecIdentity) vì
    CapabilitySpec chưa có publish/version lifecycle qua SpecRegistryRepository
    — đây là quyết định phạm vi có chủ đích, không phải thiếu sót.
    `knowledge_snapshot_ref` pin 1 KnowledgeSnapshot đã publish (Wave M6) — khi
    None, `knowledge_policy` (dict thô) vẫn là fallback. Không tự "latest"
    resolve trong Run nếu reproducibility là yêu cầu (§11.3 tài liệu gốc).
    """

    id: str
    version: str = "1.0.0"
    instructions: str = ""
    model_policy: dict[str, Any] = Field(default_factory=dict)
    autonomy_level: AutonomyLevel = AutonomyLevel.L1
    capability_refs: list[str] = Field(default_factory=list)
    model_input_capability_ref: str
    pinned_skills: list[PinnedSkillRef] = Field(default_factory=list)
    prompt_ref: PinnedSpecIdentity | None = None
    model_policy_ref: PinnedSpecIdentity | None = None
    tool_contract_refs: list[CapabilityImplementationIdentity] = Field(default_factory=list)
    knowledge_snapshot_ref: PinnedSpecIdentity | None = None
    memory_policy: dict[str, Any] = Field(default_factory=dict)
    knowledge_policy: dict[str, Any] = Field(default_factory=dict)
    coordination_policy: dict[str, Any] = Field(default_factory=dict)
    limits: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    definition_hash: str | None = None

    @model_validator(mode="after")
    def keep_model_input_out_of_executable_tools(self) -> AgentSpec:
        if self.model_input_capability_ref in self.capability_refs:
            raise ValueError("model_input_capability_ref must not appear in capability_refs")
        return self

    def compute_hash(self) -> str:
        """Tính SHA-256 hash chuẩn hoá cho toàn bộ nội dung của spec."""
        data = self.model_dump(exclude={"definition_hash"})
        return definition_hash(data)

    def with_hash(self) -> AgentSpec:
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
