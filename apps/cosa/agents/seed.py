from __future__ import annotations

from pathlib import Path

from agent.capabilities.registry import CapabilityRegistry
from agent.registry.publisher import (
    publish_agent_spec,
    publish_model_policy_spec,
    publish_prompt_spec,
)
from agent.registry.repository import SpecRegistryRepository
from agent.skills.resolver import SkillResolver

from apps.cosa.agents.catalog import deployed_entries, seeded_entries
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
