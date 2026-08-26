from __future__ import annotations

from typing import Optional

from agent_core.contracts.model_policy import ModelPolicySpec
from agent_core.contracts.prompt import PromptSpec
from agent_core.contracts.spec import AgentSpec
from agent_core.registry.models import PublishedSpecRecord
from agent_core.registry.repository import SpecDependencyMissingError, SpecRegistryRepository
from agent_core.skills.contracts import SkillSpec

__all__ = ["publish_agent_spec", "publish_skill_spec", "publish_prompt_spec", "publish_model_policy_spec"]


async def publish_agent_spec(
    spec: AgentSpec,
    *,
    repository: SpecRegistryRepository,
    publisher: Optional[str] = None,
) -> PublishedSpecRecord:
    """Publish 1 AgentSpec vào registry — idempotent nếu nội dung không đổi
    (cùng definition_hash), raise SpecVersionHashConflictError nếu version đã
    publish với nội dung KHÁC (Blueprint V2 §25: "Published version immutable;
    thay đổi phải tạo version mới"). Nếu spec pin prompt_ref/model_policy_ref,
    validate dependency đã publish với đúng hash trước khi ghi (Wave M2,
    tránh floating/broken reference — INV-A3)."""
    for ref, kind in ((spec.prompt_ref, "prompt"), (spec.model_policy_ref, "model_policy")):
        if ref is None:
            continue
        existing = await repository.get(ref.spec_kind, ref.spec_id, ref.spec_version)
        if existing is None:
            raise SpecDependencyMissingError(kind, ref.spec_id, ref.spec_version, "not_found")
        if existing.definition_hash != ref.definition_hash:
            raise SpecDependencyMissingError(kind, ref.spec_id, ref.spec_version, "hash_mismatch")

    pinned = spec.with_hash() if spec.definition_hash is None else spec
    record = PublishedSpecRecord(
        spec_kind="agent",
        spec_id=pinned.id,
        version=pinned.version,
        definition_hash=pinned.definition_hash,
        content=pinned.model_dump(mode="json"),
        publisher=publisher,
    )
    return await repository.publish(record)


async def publish_skill_spec(
    spec: SkillSpec,
    *,
    repository: SpecRegistryRepository,
    publisher: Optional[str] = None,
) -> PublishedSpecRecord:
    """Publish 1 SkillSpec vào cùng registry dùng cho AgentSpec (`spec_kind="skill"`)
    — theo ADR-SKILL-IDENTITY §4 (kích hoạt 2026-08-24, Phương án A): không tạo
    registry riêng cho skill, tái dùng `agent_registry.published_specs`. Idempotent
    nếu cùng hash; raise SpecVersionHashConflictError nếu version đã publish với
    nội dung khác."""
    pinned_hash = spec.definition_hash or spec.compute_hash()
    record = PublishedSpecRecord(
        spec_kind="skill",
        spec_id=spec.id,
        version=spec.version,
        definition_hash=pinned_hash,
        content=spec.model_dump(mode="json"),
        publisher=publisher,
    )
    return await repository.publish(record)


async def publish_prompt_spec(
    spec: PromptSpec,
    *,
    repository: SpecRegistryRepository,
    publisher: Optional[str] = None,
) -> PublishedSpecRecord:
    """Publish 1 PromptSpec vào cùng registry dùng cho AgentSpec (`spec_kind="prompt"`)
    — theo ADR-ARTIFACT-IDENTITY-001, không tạo registry riêng cho prompt.
    Idempotent nếu cùng hash; raise SpecVersionHashConflictError nếu version đã
    publish với nội dung khác."""
    pinned_hash = spec.definition_hash or spec.compute_hash()
    record = PublishedSpecRecord(
        spec_kind="prompt",
        spec_id=spec.id,
        version=spec.version,
        definition_hash=pinned_hash,
        content=spec.model_dump(mode="json"),
        publisher=publisher,
    )
    return await repository.publish(record)


async def publish_model_policy_spec(
    spec: ModelPolicySpec,
    *,
    repository: SpecRegistryRepository,
    publisher: Optional[str] = None,
) -> PublishedSpecRecord:
    """Publish 1 ModelPolicySpec vào cùng registry dùng cho AgentSpec
    (`spec_kind="model_policy"`) — theo ADR-ARTIFACT-IDENTITY-001, không tạo
    registry riêng. Idempotent nếu cùng hash; raise SpecVersionHashConflictError
    nếu version đã publish với nội dung khác."""
    pinned_hash = spec.definition_hash or spec.compute_hash()
    record = PublishedSpecRecord(
        spec_kind="model_policy",
        spec_id=spec.id,
        version=spec.version,
        definition_hash=pinned_hash,
        content=spec.model_dump(mode="json"),
        publisher=publisher,
    )
    return await repository.publish(record)
