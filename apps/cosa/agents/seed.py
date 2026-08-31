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

from apps.cosa.agents.skillpack_seed import seed_builtin_skillpacks
from apps.cosa.agents.specs import (
    COSA_CUSTOMER_SUPPORT_AGENT_SPEC,
    COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC,
    COSA_CUSTOMER_SUPPORT_AUTOPILOT_PROMPT,
    COSA_CUSTOMER_SUPPORT_PROMPT,
    COSA_DEFAULT_MODEL_POLICY,
    COSA_DEPLOYED_AGENT_SPECS,
    COSA_FINANCE_AGENT_SPEC,
    COSA_FINANCE_PROMPT,
    COSA_MARKETING_AGENT_SPEC,
    COSA_MARKETING_PROMPT,
    COSA_OPERATIONS_AGENT_SPEC,
    COSA_OPERATIONS_PROMPT,
)

__all__ = ["seed_cosa_agent_specs", "seed_cosa_runtime_specs"]


async def seed_cosa_agent_specs(spec_registry: SpecRegistryRepository) -> None:
    """Publish toàn bộ Prompt/ModelPolicy/AgentSpec của COSA vào registry —
    được `seed_cosa_runtime_specs()` gọi ở mỗi entrypoint thật
    (`apps/cosa/api/app.py` lifespan, `apps/cosa/worker/main.py::main()`)
    SAU khi `build_cosa_agent_plane()` đã dựng xong (hàm đó vẫn sync,
    seeding là bước async riêng — Wave M2b).
    Idempotent: publish_* chỉ lỗi nếu version đã publish với hash KHÁC, mà
    `apps/cosa/agents/specs.py` là module-level constant nên hash luôn ổn
    định giữa các lần gọi. `publish_agent_spec()` validate prompt_ref/
    model_policy_ref đã publish trước (Wave M2 §5) — vì vậy Prompt/ModelPolicy
    PHẢI publish trước AgentSpec, đúng thứ tự dưới đây."""
    for fn, spec in (
        (publish_prompt_spec, COSA_OPERATIONS_PROMPT),
        (publish_prompt_spec, COSA_FINANCE_PROMPT),
        (publish_prompt_spec, COSA_MARKETING_PROMPT),
        (publish_prompt_spec, COSA_CUSTOMER_SUPPORT_PROMPT),
        (publish_prompt_spec, COSA_CUSTOMER_SUPPORT_AUTOPILOT_PROMPT),
        (publish_model_policy_spec, COSA_DEFAULT_MODEL_POLICY),
        (publish_agent_spec, COSA_OPERATIONS_AGENT_SPEC),
        (publish_agent_spec, COSA_FINANCE_AGENT_SPEC),
        (publish_agent_spec, COSA_MARKETING_AGENT_SPEC),
        (publish_agent_spec, COSA_CUSTOMER_SUPPORT_AGENT_SPEC),
        (publish_agent_spec, COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC),
    ):
        await fn(spec, repository=spec_registry, publisher="cosa-seed")  # type: ignore[arg-type]


async def seed_cosa_runtime_specs(
    *,
    spec_registry: SpecRegistryRepository,
    capability_registry: CapabilityRegistry,
    skillpacks_root: Path | None = None,
) -> None:
    """Khởi tạo đầy đủ runtime specs của COSA theo đúng thứ tự bắt buộc —
    entrypoint duy nhất mà `apps/cosa/api/app.py` (lifespan) và
    `apps/cosa/worker/main.py::main()` phải gọi trước khi phục vụ traffic
    (Wave M2b). Thứ tự: (1) publish toàn bộ skillpack built-in — fail-closed
    qua `seed_builtin_skillpacks` (BuiltinSkillpackSeedError nếu thiếu bundle
    root, vi phạm contract, hay parse/publish lỗi); (2) publish Prompt/
    ModelPolicy/AgentSpec qua `seed_cosa_agent_specs` (đã tự đảm bảo thứ tự
    dependency bên trong); (3) verify mọi `pinned_skills` của
    `COSA_DEPLOYED_AGENT_SPECS` resolve được — nếu một AgentSpec pin skill
    chưa publish hoặc hash lệch, `SkillResolver.resolve()` raise ngay, không
    để runtime khởi động với agent spec tham chiếu treo."""
    await seed_builtin_skillpacks(
        spec_registry,
        capability_ids={spec.id for spec in capability_registry.list_specs()},
        skillpacks_root=skillpacks_root,
    )
    await seed_cosa_agent_specs(spec_registry)
    resolver = SkillResolver(spec_registry)
    for agent_spec in COSA_DEPLOYED_AGENT_SPECS:
        await resolver.resolve(agent_spec.pinned_skills)
