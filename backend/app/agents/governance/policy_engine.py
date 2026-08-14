from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from app.core.tool_registry import ToolSpec


class PermissionLevel(str, Enum):
    L0_READ = "L0_READ"
    L1_SUGGEST = "L1_SUGGEST"
    L2_DRAFT = "L2_DRAFT"
    L3_EXECUTE = "L3_EXECUTE"


class PolicyAction(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


@dataclass(frozen=True)
class PolicyDecision:
    action: PolicyAction
    reason: str
    risk_level: str
    requires_approval: bool


class PolicyEngine:
    """Evaluates agent tool requests against L0-L3 permission profiles and risk classifications."""

    @staticmethod
    def normalize_permission_level(profile: str) -> PermissionLevel:
        profile_lower = profile.lower().replace("-", "_")
        if "l3" in profile_lower or "execute" in profile_lower:
            return PermissionLevel.L3_EXECUTE
        if "l2" in profile_lower or "draft" in profile_lower:
            return PermissionLevel.L2_DRAFT
        if "l1" in profile_lower or "suggest" in profile_lower:
            return PermissionLevel.L1_SUGGEST
        return PermissionLevel.L0_READ

    @classmethod
    def evaluate(
        cls,
        agent_key: str,
        tool_spec: ToolSpec,
        permission_profile: str = "read_only",
        input_data: Optional[dict[str, Any]] = None,
    ) -> PolicyDecision:
        level = cls.normalize_permission_level(permission_profile)
        risk = tool_spec.risk_level.lower()
        perm = tool_spec.permission_level.lower()

        # 1. Check Agent Key Whitelist on tool
        if tool_spec.allowed_agent_keys and agent_key not in tool_spec.allowed_agent_keys:
            return PolicyDecision(
                action=PolicyAction.DENY,
                reason=f"Agent '{agent_key}' is not allowed to invoke tool '{tool_spec.qualified_name}'",
                risk_level=risk,
                requires_approval=False,
            )

        # 2. Critical risk actions always require approval regardless of L0-L3 level
        if risk == "critical" or tool_spec.requires_approval:
            return PolicyDecision(
                action=PolicyAction.REQUIRE_APPROVAL,
                reason=f"Tool '{tool_spec.qualified_name}' carries {risk} risk and mandates human approval",
                risk_level=risk,
                requires_approval=True,
            )

        # 3. L0 — Read-Only
        if level == PermissionLevel.L0_READ:
            if perm == "read_only":
                return PolicyDecision(
                    action=PolicyAction.ALLOW,
                    reason="Read-only tool permitted under L0_READ",
                    risk_level=risk,
                    requires_approval=False,
                )
            return PolicyDecision(
                action=PolicyAction.DENY,
                reason=f"Write action '{tool_spec.qualified_name}' forbidden under L0_READ policy",
                risk_level=risk,
                requires_approval=False,
            )

        # 4. L1 — Suggest
        if level == PermissionLevel.L1_SUGGEST:
            if perm == "read_only":
                return PolicyDecision(
                    action=PolicyAction.ALLOW,
                    reason="Read tool permitted under L1_SUGGEST",
                    risk_level=risk,
                    requires_approval=False,
                )
            return PolicyDecision(
                action=PolicyAction.REQUIRE_APPROVAL,
                reason=f"Write action '{tool_spec.qualified_name}' requires human approval under L1_SUGGEST",
                risk_level=risk,
                requires_approval=True,
            )

        # 5. L2 — Draft
        if level == PermissionLevel.L2_DRAFT:
            if perm == "read_only":
                return PolicyDecision(
                    action=PolicyAction.ALLOW,
                    reason="Read tool permitted under L2_DRAFT",
                    risk_level=risk,
                    requires_approval=False,
                )
            if perm == "scoped_write" and risk == "low":
                return PolicyDecision(
                    action=PolicyAction.ALLOW,
                    reason="Low-risk internal scoped write permitted under L2_DRAFT",
                    risk_level=risk,
                    requires_approval=False,
                )
            return PolicyDecision(
                action=PolicyAction.REQUIRE_APPROVAL,
                reason=f"Medium/high risk write '{tool_spec.qualified_name}' requires approval under L2_DRAFT",
                risk_level=risk,
                requires_approval=True,
            )

        # 6. L3 — Execute
        if level == PermissionLevel.L3_EXECUTE:
            if risk in ("low", "medium") and perm in ("read_only", "scoped_write"):
                return PolicyDecision(
                    action=PolicyAction.ALLOW,
                    reason=f"Execution permitted for {risk} risk tool under L3_EXECUTE",
                    risk_level=risk,
                    requires_approval=False,
                )
            return PolicyDecision(
                action=PolicyAction.REQUIRE_APPROVAL,
                reason=f"High risk tool '{tool_spec.qualified_name}' requires approval under L3_EXECUTE",
                risk_level=risk,
                requires_approval=True,
            )

        return PolicyDecision(
            action=PolicyAction.DENY,
            reason="Unrecognized permission configuration",
            risk_level=risk,
            requires_approval=False,
        )
