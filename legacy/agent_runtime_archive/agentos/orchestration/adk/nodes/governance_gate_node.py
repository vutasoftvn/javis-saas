from __future__ import annotations

from typing import Any, Optional
from google.adk.workflow._function_node import FunctionNode

from agentos.core.policy import PermissionLevel, PolicyDecision, PolicyEngine, ToolRiskLevel


def build_governance_gate_node(policy_engine: Optional[PolicyEngine] = None, name: str = "governance_gate_node") -> FunctionNode:
    engine = policy_engine or PolicyEngine()

    async def governance_gate_fn(ctx: Any) -> dict[str, Any]:
        role = ctx.state.get("role", "founder")
        agent_perm_level = ctx.state.get("agent_permission_level", PermissionLevel.L3_EXECUTE)
        risk_level_str = ctx.state.get("risk_level", "LOW")
        try:
            risk_level = ToolRiskLevel(risk_level_str)
        except ValueError:
            risk_level = ToolRiskLevel.LOW

        tool_perm = ctx.state.get("tool_permission", ToolPermission.SCOPED_WRITE)
        tenant_pol = ctx.state.get("tenant_policy")
        exec_mode = ctx.state.get("execution_mode")
        scope = ctx.state.get("data_scope")

        decision = engine.evaluate_access(
            role=role,
            agent_permission_level=agent_perm_level,
            tool_risk_level=risk_level,
            tool_permission=tool_perm,
            tenant_policy=tenant_pol,
            execution_mode=exec_mode,
            data_scope=scope,
            run_id=ctx.state.get("mission_id"),
            workspace_id=ctx.state.get("workspace_id"),
        )

        if decision == PolicyDecision.DENY:
            ctx.state["governance_block_reason"] = "Policy denied access for the requested mission tier"
            ctx.route = "blocked"
            return {"blocked": True, "decision": "DENY"}

        if decision == PolicyDecision.REQUIRE_APPROVAL:
            ctx.route = "requires_approval"
            return {"blocked": False, "decision": "REQUIRE_APPROVAL"}

        ctx.route = "continue"
        return {"blocked": False, "decision": "ALLOW"}

    return FunctionNode(func=governance_gate_fn, name=name)
