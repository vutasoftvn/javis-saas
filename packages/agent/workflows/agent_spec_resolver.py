from __future__ import annotations

from agent.contracts.spec import AgentSpec
from agent.registry.repository import SpecRegistryRepository

__all__ = ["AgentSpecResolutionError", "RegistryAgentSpecResolver"]


class AgentSpecResolutionError(RuntimeError):
    """AgentSpec đúng id+version+hash không resolve được từ registry."""


class RegistryAgentSpecResolver:
    """Resolve AgentSpec đầy đủ theo exact identity — không có "latest" và không dựng
    spec từ `PinnedSpecIdentity` (chỉ chứa id/version/hash, thiếu instructions/skills)."""

    def __init__(self, repository: SpecRegistryRepository) -> None:
        self._repository = repository

    async def resolve_agent_spec(
        self, *, spec_id: str, version: str, definition_hash: str
    ) -> AgentSpec:
        record = await self._repository.get(spec_kind="agent", spec_id=spec_id, version=version)
        if record is None:
            raise AgentSpecResolutionError(f"AgentSpec '{spec_id}@{version}' is not published")
        if record.definition_hash != definition_hash:
            raise AgentSpecResolutionError(
                f"AgentSpec '{spec_id}@{version}' hash differs from the pinned definition_hash"
            )
        spec = AgentSpec(**record.content)
        if spec.compute_hash() != definition_hash:
            raise AgentSpecResolutionError(
                f"Registry content of '{spec_id}@{version}' does not hash to the pinned value"
            )
        return spec
