from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent.contracts.spec import AgentSpec
from agent.governance.contracts import PinnedSpecIdentity, SpecDependencyEdge
from agent.registry.repository import SpecDependencyMissingError, SpecRegistryRepository

__all__ = ["AgentSpecResolution", "SpecResolver"]


@dataclass(frozen=True)
class AgentSpecResolution:
    """Kết quả resolve đầy đủ 1 AgentSpec: content của chính spec + content
    của từng dependency đã pin + lineage edges tương ứng. `edges` chỉ tính
    in-memory (không persist) — theo Global Constraints của plan này, chưa
    có bảng lineage nào được quyết định tạo."""

    agent_content: dict[str, Any]
    prompt_content: dict[str, Any] | None
    model_policy_content: dict[str, Any] | None
    edges: tuple[SpecDependencyEdge, ...]


class SpecResolver:
    """Exact-resolution cho registry (§7.3 của
    COSA_MARIN_PATTERNS_INTEGRATION_AND_ADJUSTMENT_PLAN_2026-08-26.md):
    luôn yêu cầu definition_hash khớp tuyệt đối, không có floating "latest"
    resolution — production kernel chỉ dùng resolver này, không dùng registry
    repository trực tiếp."""

    def __init__(self, repository: SpecRegistryRepository) -> None:
        self._repository = repository

    async def resolve_exact(
        self,
        kind: str,
        spec_id: str,
        version: str,
        expected_definition_hash: str,
    ) -> dict[str, Any]:
        """Resolve đúng (kind, spec_id, version) và verify definition_hash khớp
        tuyệt đối. Raise SpecDependencyMissingError nếu không tìm thấy hoặc
        hash khác."""
        record = await self._repository.get(kind, spec_id, version)
        if record is None:
            raise SpecDependencyMissingError(kind, spec_id, version, "not_found")
        if record.definition_hash != expected_definition_hash:
            raise SpecDependencyMissingError(kind, spec_id, version, "hash_mismatch")
        return record.content

    async def resolve_agent_spec_dependencies(self, agent_spec: AgentSpec) -> AgentSpecResolution:
        """Resolve toàn bộ dependency đã pin (prompt_ref, model_policy_ref)
        của 1 AgentSpec bằng exact resolution, đồng thời tính lineage edges.
        Không resolve pinned_skills/tool_contract_refs ở đây — pinned_skills
        đã có SkillResolver riêng (packages/agent/skills/resolver.py),
        tool_contract_refs không đi qua registry (xem AgentSpec docstring)."""
        agent_hash = agent_spec.definition_hash or agent_spec.compute_hash()
        agent_record = await self.resolve_exact(
            "agent", agent_spec.id, agent_spec.version, agent_hash
        )
        owner_identity = PinnedSpecIdentity(
            spec_kind="agent",
            spec_id=agent_spec.id,
            spec_version=agent_spec.version,
            definition_hash=agent_hash,
        )

        prompt_content: dict[str, Any] | None = None
        model_policy_content: dict[str, Any] | None = None
        edges: list[SpecDependencyEdge] = []

        if agent_spec.prompt_ref is not None:
            ref = agent_spec.prompt_ref
            prompt_content = await self.resolve_exact(
                ref.spec_kind, ref.spec_id, ref.spec_version, ref.definition_hash
            )
            edges.append(
                SpecDependencyEdge(owner=owner_identity, dependency=ref, relation="uses_prompt")
            )

        if agent_spec.model_policy_ref is not None:
            ref = agent_spec.model_policy_ref
            model_policy_content = await self.resolve_exact(
                ref.spec_kind, ref.spec_id, ref.spec_version, ref.definition_hash
            )
            edges.append(
                SpecDependencyEdge(
                    owner=owner_identity, dependency=ref, relation="uses_model_policy"
                )
            )

        return AgentSpecResolution(
            agent_content=agent_record,
            prompt_content=prompt_content,
            model_policy_content=model_policy_content,
            edges=tuple(edges),
        )
