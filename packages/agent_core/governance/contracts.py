from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PinnedSpecIdentity(BaseModel):
    """Định danh bất biến của 1 executable spec (AgentSpec/WorkflowSpec) mà
    1 Run đã resolve tới. `definition_hash` (không phải chỉ `spec_version`)
    là thứ chống silent drift — xem PHẦN I §1 của
    COSA_AGENT_CORE_GOVERNANCE_TEMPORAL_MODEL_2026-08-23.md."""

    spec_kind: Literal["agent", "workflow"]
    spec_id: str
    spec_version: str
    definition_hash: str


class SpecResolutionManifest(BaseModel):
    """Tập PinnedSpecIdentity mà 1 Run/checkpoint đã resolve tới thời điểm
    đó. Chỉ tăng dần (agent-as-tool delegate thêm 1 AgentSpec giữa chừng
    Run là ví dụ điển hình) — không bao giờ xoá entry đã có."""

    entries: tuple[PinnedSpecIdentity, ...] = Field(default_factory=tuple)

    def with_entry(self, entry: PinnedSpecIdentity) -> "SpecResolutionManifest":
        if entry in self.entries:
            return self
        return SpecResolutionManifest(entries=(*self.entries, entry))
