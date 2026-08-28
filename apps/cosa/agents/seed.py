from __future__ import annotations

import contextlib

from agent_core.registry.publisher import (
    publish_agent_spec,
    publish_model_policy_spec,
    publish_prompt_spec,
)
from agent_core.registry.repository import (
    SpecRegistryRepository,
    SpecVersionHashConflictError,
)

from apps.cosa.agents.specs import (
    COSA_CUSTOMER_SUPPORT_AGENT_SPEC,
    COSA_CUSTOMER_SUPPORT_PROMPT,
    COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC,
    COSA_CUSTOMER_SUPPORT_AUTOPILOT_PROMPT,
    COSA_DEFAULT_MODEL_POLICY,
    COSA_FINANCE_AGENT_SPEC,
    COSA_FINANCE_PROMPT,
    COSA_MARKETING_AGENT_SPEC,
    COSA_MARKETING_PROMPT,
    COSA_OPERATIONS_AGENT_SPEC,
    COSA_OPERATIONS_PROMPT,
)

__all__ = ["seed_cosa_agent_specs"]


async def seed_cosa_agent_specs(spec_registry: SpecRegistryRepository) -> None:
    """Publish toàn bộ Prompt/ModelPolicy/AgentSpec của COSA vào registry —
    gọi 1 lần ở mỗi entrypoint thật (`apps/cosa/api/app.py` lifespan,
    `apps/cosa/worker/main.py::main()`) SAU khi `build_cosa_agent_plane()`
    đã dựng xong (hàm đó vẫn sync, seeding là bước async riêng — Wave M2b).
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
        with contextlib.suppress(SpecVersionHashConflictError):
            await fn(spec, repository=spec_registry, publisher="cosa-seed")  # type: ignore[arg-type]
