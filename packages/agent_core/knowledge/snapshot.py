from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from agent_core.governance.contracts import PinnedSpecIdentity
from agent_core.governance.hashing import definition_hash

__all__ = ["KnowledgeSnapshot"]


class KnowledgeSnapshot(BaseModel):
    """Đặc tả knowledge snapshot có thể publish/pin độc lập — theo
    ADR-ARTIFACT-IDENTITY-001 (spec_kind="knowledge_snapshot", Wave M6).
    `source_refs` chỉ THAM CHIẾU (source_id, version, content_hash) đã có
    trong `knowledge.source_versions` (migration 010), KHÔNG publish lại nội
    dung document/chunk — Memory Item (mutable, `knowledge/store.py`) và
    Knowledge Snapshot (bất biến, ở đây) là 2 khái niệm tách biệt (§11.2
    COSA_MARIN_PATTERNS_INTEGRATION_AND_ADJUSTMENT_PLAN_2026-08-26.md).
    `chunking_recipe_version`/`embedding_model`/`embedding_version`/
    `index_recipe_version` là string đơn giản — các recipe này chưa có
    publish/version lifecycle riêng qua registry (giống quyết định
    `tool_contract_refs` ở Wave M2), không cần registry-backed ref khi
    chưa có nhu cầu thật."""

    id: str
    version: str = "1.0.0"
    workspace_id: str
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    chunking_recipe_version: str = "1.0"
    embedding_model: str
    embedding_version: str
    index_recipe_version: str = "1.0"
    retrieval_eval_run_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    definition_hash: Optional[str] = None

    def compute_hash(self) -> str:
        """Tính SHA-256 hash chuẩn hoá — source_refs được sort theo
        (source_id, version) để đảm bảo thứ tự không ảnh hưởng fingerprint."""
        data = self.model_dump(exclude={"definition_hash"})
        data["source_refs"] = sorted(
            data["source_refs"], key=lambda r: (r.get("source_id", ""), r.get("version", 0))
        )
        return definition_hash(data)

    def with_hash(self) -> "KnowledgeSnapshot":
        """Trả về bản sao của KnowledgeSnapshot đã được gắn definition_hash xác thực."""
        return self.model_copy(update={"definition_hash": self.compute_hash()})

    def to_pinned_identity(self) -> PinnedSpecIdentity:
        """Chuyển đổi sang PinnedSpecIdentity để pin vào AgentSpec.knowledge_snapshot_ref."""
        h = self.definition_hash or self.compute_hash()
        return PinnedSpecIdentity(
            spec_kind="knowledge_snapshot",
            spec_id=self.id,
            spec_version=self.version,
            definition_hash=h,
        )
