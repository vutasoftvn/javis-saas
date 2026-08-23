from __future__ import annotations

from typing import Any, Optional
from google.adk.workflow._function_node import FunctionNode

from agentos.profiles.registry import AgentProfileRegistry
from agentos.skills.registry import SkillRegistry


def build_specialist_delegation_node(
    profile_registry: Optional[AgentProfileRegistry] = None,
    skill_registry: Optional[SkillRegistry] = None,
) -> FunctionNode:
    async def specialist_delegation_fn(ctx: Any) -> dict[str, Any]:
        active_domains: list[str] = ctx.state.get("active_domains", [])
        delegated_specialists: list[dict[str, Any]] = []

        if profile_registry is not None:
            available_profiles = profile_registry.list()
            for domain in active_domains:
                # Find profile matching domain
                matched = next(
                    (p for p in available_profiles if domain.lower() in p.id.lower() or domain.lower() in p.role.lower()),
                    None,
                )
                if matched:
                    delegated_specialists.append({"domain": domain, "agent_key": matched.id, "profile": matched})
                else:
                    delegated_specialists.append({"domain": domain, "agent_key": f"{domain}_specialist"})
        else:
            for domain in active_domains:
                delegated_specialists.append({"domain": domain, "agent_key": f"{domain}_specialist"})

        ctx.state["delegated_specialists"] = delegated_specialists
        return {"delegated_count": len(delegated_specialists), "specialists": [d["agent_key"] for d in delegated_specialists]}

    return FunctionNode(func=specialist_delegation_fn, name="specialist_delegation_node")
