from app.workforce.agents.governance.policy_engine import (
    PermissionLevel,
    PolicyAction,
    PolicyDecision,
    PolicyEngine,
)


_PERMISSION_RANK = {
    PermissionLevel.L0_READ: 0,
    PermissionLevel.L1_SUGGEST: 1,
    PermissionLevel.L2_DRAFT: 2,
    PermissionLevel.L3A_EXECUTE_WITH_APPROVAL: 3,
    PermissionLevel.L3_EXECUTE: 4,
}

_APPROVAL_REQUIRED_PROVIDERS = {
    "codex_device",
    "claude_device",
    "n8n",
    "sandbox",
}


class DelegationPolicyEngine:
    """Evaluate assignment authority without disguising delegation as a tool."""

    @classmethod
    def evaluate(
        cls,
        *,
        parent_permission: str,
        child_permission: str,
        risk_level: str,
        provider_name: str,
        provider_healthy: bool,
        provider_enabled: bool = True,
    ) -> PolicyDecision:
        risk_raw, risk = PolicyEngine.normalize_risk_level(risk_level)
        parent = PolicyEngine.normalize_permission_level(parent_permission)
        child = PolicyEngine.normalize_permission_level(child_permission)

        if not provider_enabled or not provider_healthy:
            return cls._decision(
                PolicyAction.DENY,
                f"Delegation provider '{provider_name}' is unavailable",
                risk,
            )

        if risk not in {"low", "medium", "high", "critical"}:
            return cls._decision(
                PolicyAction.DENY,
                f"Unknown delegation risk level '{risk_level}'",
                risk,
            )

        if _PERMISSION_RANK[child] > _PERMISSION_RANK[parent]:
            return cls._decision(
                PolicyAction.DENY,
                "Delegated profile cannot exceed the parent run permission",
                risk,
            )

        if provider_name in _APPROVAL_REQUIRED_PROVIDERS:
            return cls._decision(
                PolicyAction.REQUIRE_APPROVAL,
                f"Delegation provider '{provider_name}' requires human approval",
                risk,
            )

        if risk in {"high", "critical"} or risk_raw in {"r3", "r4"}:
            return cls._decision(
                PolicyAction.REQUIRE_APPROVAL,
                f"Delegation carrying {risk_raw.upper()} risk requires human approval",
                risk,
            )

        if risk == "low":
            return cls._decision(
                PolicyAction.ALLOW,
                "Low-risk delegation is allowed within parent authority",
                risk,
            )

        if parent == PermissionLevel.L0_READ:
            return cls._decision(
                PolicyAction.DENY,
                "Medium-risk delegation is forbidden under L0_READ",
                risk,
            )
        if parent in {
            PermissionLevel.L1_SUGGEST,
            PermissionLevel.L3A_EXECUTE_WITH_APPROVAL,
        }:
            return cls._decision(
                PolicyAction.REQUIRE_APPROVAL,
                "Medium-risk delegation requires approval under parent authority",
                risk,
            )
        return cls._decision(
            PolicyAction.ALLOW,
            "Medium-risk delegation is allowed within parent authority",
            risk,
        )

    @staticmethod
    def _decision(
        action: PolicyAction,
        reason: str,
        risk_level: str,
    ) -> PolicyDecision:
        return PolicyDecision(
            action=action,
            reason=reason,
            risk_level=risk_level,
            requires_approval=action == PolicyAction.REQUIRE_APPROVAL,
        )
