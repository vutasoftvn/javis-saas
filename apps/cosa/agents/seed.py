from __future__ import annotations

from pathlib import Path
from typing import Any

from agent.capabilities.registry import CapabilityRegistry
from agent.contracts.spec import AgentSpec
from agent.registry.publisher import (
    publish_agent_spec,
    publish_model_policy_spec,
    publish_prompt_spec,
)
from agent.registry.repository import SpecRegistryRepository
from agent.skills.resolver import SkillResolver

from apps.cosa.agents.advisor_overlay_validation import validate_advisor_overlay
from apps.cosa.agents.capability_readiness import get_skill_required_capabilities
from apps.cosa.agents.catalog import CATALOG_BY_PROFILE, deployed_entries, seeded_entries
from apps.cosa.agents.executive_advisor_overlays_generated import ADVISOR_OVERLAY_CATALOG
from apps.cosa.agents.skillpack_seed import seed_builtin_skillpacks
from apps.cosa.agents.specs import COSA_DEFAULT_MODEL_POLICY

__all__ = ["seed_cosa_agent_specs", "seed_cosa_runtime_specs"]


async def seed_cosa_agent_specs(spec_registry: SpecRegistryRepository) -> None:
    """Publish toàn bộ Prompt/ModelPolicy/AgentSpec của COSA vào registry —
    được `seed_cosa_runtime_specs()` gọi ở mỗi entrypoint thật
    (`apps/cosa/api/app.py` lifespan, `apps/cosa/worker/main.py::main()`)
    SAU khi `build_cosa_agent_plane()` đã dựng xong.

    Thứ tự chuẩn hóa từ canonical catalog (Task 4):
    (1) publish toàn bộ prompt_spec của seeded_entries();
    (2) publish model policy spec;
    (3) publish toàn bộ agent_spec của seeded_entries().
    """
    entries = seeded_entries()

    for entry in entries:
        await publish_prompt_spec(
            entry.prompt_spec, repository=spec_registry, publisher="cosa-seed"
        )

    await publish_model_policy_spec(
        COSA_DEFAULT_MODEL_POLICY, repository=spec_registry, publisher="cosa-seed"
    )

    for entry in entries:
        await publish_agent_spec(entry.agent_spec, repository=spec_registry, publisher="cosa-seed")


async def seed_cosa_runtime_specs(
    *,
    spec_registry: SpecRegistryRepository,
    capability_registry: CapabilityRegistry,
    skillpacks_root: Path | None = None,
) -> None:
    """Khởi tạo đầy đủ runtime specs của COSA theo đúng thứ tự bắt buộc —
    entrypoint duy nhất mà `apps/cosa/api/app.py` (lifespan) và
    `apps/cosa/worker/main.py::main()` phải gọi trước khi phục vụ traffic
    (Wave M2b).

    Thứ tự:
    (1) publish toàn bộ skillpack built-in qua `seed_builtin_skillpacks`;
    (2) publish Prompt/ModelPolicy/AgentSpec qua `seed_cosa_agent_specs`;
    (3) verify mọi deployed entry: bản ghi AgentSpec tồn tại trong registry
        và mọi `pinned_skills` resolve được qua `SkillResolver`.
    """
    await seed_builtin_skillpacks(
        spec_registry,
        capability_ids={spec.id for spec in capability_registry.list_specs()},
        skillpacks_root=skillpacks_root,
    )
    await seed_cosa_agent_specs(spec_registry)
    resolver = SkillResolver(spec_registry)
    for entry in deployed_entries():
        record = await spec_registry.get("agent", entry.agent_spec.id, entry.agent_spec.version)
        if record is None:
            raise RuntimeError(
                f"Deployed agent spec {entry.agent_spec.id}:{entry.agent_spec.version} "
                "not found in registry after seeding"
            )
        await resolver.resolve(entry.agent_spec.pinned_skills)

    capability_ids = {spec.id for spec in capability_registry.list_specs()}
    _verify_agent_capability_refs_registered(capability_ids)
    await _verify_skill_capability_closure(spec_registry, capability_ids)
    await _verify_advisor_overlays(spec_registry, capability_ids)


def _verify_agent_capability_refs_registered(capability_ids: set[str]) -> None:
    """Fail-closed: mọi `capability_refs` của AgentSpec phải có trong capability registry.

    Kernel bỏ qua âm thầm capability chưa đăng ký khi dựng tool — id gõ sai sẽ làm
    agent mất tool mà không có lỗi nào; chặn ngay lúc khởi động thay vì lúc chạy.
    """
    unregistered = {
        entry.agent_spec.id: sorted(set(entry.agent_spec.capability_refs) - capability_ids)
        for entry in seeded_entries()
        if set(entry.agent_spec.capability_refs) - capability_ids
    }
    if unregistered:
        raise RuntimeError(f"Agent specs reference unregistered capabilities: {unregistered}")


async def _skill_manifests(
    spec_registry: SpecRegistryRepository, spec: AgentSpec
) -> dict[str, dict[str, Any]]:
    """Manifest dạng `{runtime: {tools}}` của các skill spec pin, đọc từ registry đã publish."""
    manifests: dict[str, dict[str, Any]] = {}
    for pinned in spec.pinned_skills:
        record = await spec_registry.get("skill", pinned.skill_id, pinned.version)
        if record is not None:
            tools = list(record.content.get("required_capabilities") or [])
            manifests[pinned.skill_id] = {"runtime": {"tools": tools}}
    return manifests


async def _verify_skill_capability_closure(
    spec_registry: SpecRegistryRepository, capability_ids: set[str]
) -> None:
    """Fail-closed: tool của skill pin phải có trong capability registry VÀ trong
    `capability_refs` của chính AgentSpec sở hữu (skill không được mở rộng quyền agent)."""
    for entry in seeded_entries():
        spec = entry.agent_spec
        manifests = await _skill_manifests(spec_registry, spec)
        missing = [p.skill_id for p in spec.pinned_skills if p.skill_id not in manifests]
        if missing:
            raise RuntimeError(f"Agent spec {spec.id} pins skills absent from registry: {missing}")
        skill_tools: set[str] = set()
        for manifest in manifests.values():
            skill_tools |= get_skill_required_capabilities(manifest)
        # Chỉ xét tool của skill: capability_refs riêng của AgentSpec (kể cả id chưa đăng ký)
        # không thuộc invariant này.
        unregistered = sorted(skill_tools - capability_ids)
        outside_spec = sorted(skill_tools - set(spec.capability_refs))
        if unregistered or outside_spec:
            raise RuntimeError(
                f"Agent spec {spec.id} skill tools not closed: unregistered={unregistered} "
                f"outside_capability_refs={outside_spec}"
            )


async def _verify_advisor_overlays(
    spec_registry: SpecRegistryRepository, capability_ids: set[str]
) -> None:
    """Fail-closed trước khi poll: mọi role trong contract phải có overlay đã publish
    đúng exact id/version/hash và không vượt quyền profile bắt buộc."""
    for role_key, overlay in ADVISOR_OVERLAY_CATALOG.items():
        record = await spec_registry.get(
            "agent", overlay.overlay_spec_id, overlay.overlay_spec_version
        )
        if record is None or record.definition_hash != overlay.overlay_definition_hash:
            raise RuntimeError(
                f"Advisor overlay {role_key} ({overlay.overlay_spec_id}:"
                f"{overlay.overlay_spec_version}) missing or hash drift in registry"
            )
        profile = CATALOG_BY_PROFILE.get(overlay.required_profile_key)
        if profile is None:
            raise RuntimeError(
                f"Advisor overlay {role_key} requires unknown profile {overlay.required_profile_key}"
            )
        overlay_spec = next(
            e.agent_spec for e in seeded_entries() if e.agent_spec.id == overlay.overlay_spec_id
        )
        violations = validate_advisor_overlay(
            overlay_spec,
            profile.agent_spec,
            await _skill_manifests(spec_registry, overlay_spec),
        )
        if violations:
            raise RuntimeError(f"Advisor overlay {role_key} invalid: {'; '.join(violations)}")
