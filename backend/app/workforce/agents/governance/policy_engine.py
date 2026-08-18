from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from app.core.tool_registry import ToolSpec


class PermissionLevel(str, Enum):
    L0_READ = "L0_READ"
    L1_SUGGEST = "L1_SUGGEST"
    L2_DRAFT = "L2_DRAFT"
    L3A_EXECUTE_WITH_APPROVAL = "L3A_EXECUTE_WITH_APPROVAL"
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
        if "l3a" in profile_lower or "execute_with_approval" in profile_lower:
            return PermissionLevel.L3A_EXECUTE_WITH_APPROVAL
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
        risk_raw = tool_spec.risk_level.lower()
        if risk_raw in ("r0", "r1"):
            risk = "low"
        elif risk_raw == "r2":
            risk = "medium"
        elif risk_raw == "r3":
            risk = "high"
        elif risk_raw == "r4":
            risk = "critical"
        else:
            risk = risk_raw
        perm = tool_spec.permission_level.lower()

        # 1. Check Agent Key Whitelist on tool
        if tool_spec.allowed_agent_keys and agent_key not in tool_spec.allowed_agent_keys:
            if not (agent_key == "chat" and tool_spec.chat_schema is not None):
                return PolicyDecision(
                    action=PolicyAction.DENY,
                    reason=f"Agent '{agent_key}' is not allowed to invoke tool '{tool_spec.qualified_name}'",
                    risk_level=risk,
                    requires_approval=False,
                )

        # 2. Critical risk actions (R4) always mandate approval regardless of permission level
        if risk == "critical" or tool_spec.requires_approval or risk_raw == "r4":
            return PolicyDecision(
                action=PolicyAction.REQUIRE_APPROVAL,
                reason=f"Tool '{tool_spec.qualified_name}' carries {risk_raw.upper() if risk_raw.startswith('r') else risk} risk and mandates human approval",
                risk_level=risk,
                requires_approval=True,
            )

        # 3. L0 — Read-Only (R0 automatic, writes denied)
        if level == PermissionLevel.L0_READ:
            if perm == "read_only" or risk_raw in ("r0", "r1"):
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

        # 4. L1 — Suggest (R0/R1 automatic, R2/R3 require approval)
        if level == PermissionLevel.L1_SUGGEST:
            if perm == "read_only" or risk_raw in ("r0", "r1"):
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
            if perm == "read_only" or risk_raw in ("r0", "r1"):
                return PolicyDecision(
                    action=PolicyAction.ALLOW,
                    reason="Read tool permitted under L2_DRAFT",
                    risk_level=risk,
                    requires_approval=False,
                )
            if perm == "scoped_write" and (risk == "low" or risk_raw == "r2"):
                return PolicyDecision(
                    action=PolicyAction.ALLOW,
                    reason="Internal scoped write permitted under L2_DRAFT",
                    risk_level=risk,
                    requires_approval=False,
                )
            return PolicyDecision(
                action=PolicyAction.REQUIRE_APPROVAL,
                reason=f"High risk write '{tool_spec.qualified_name}' requires approval under L2_DRAFT",
                risk_level=risk,
                requires_approval=True,
            )

        # 6. L3A — Execute with Approval (Autonomous preparation/drafting, but execution requires human approval)
        if level == PermissionLevel.L3A_EXECUTE_WITH_APPROVAL:
            if perm == "read_only" or risk_raw in ("r0", "r1"):
                return PolicyDecision(
                    action=PolicyAction.ALLOW,
                    reason="Read tool permitted under L3A_EXECUTE_WITH_APPROVAL",
                    risk_level=risk,
                    requires_approval=False,
                )
            return PolicyDecision(
                action=PolicyAction.REQUIRE_APPROVAL,
                reason=f"Action '{tool_spec.qualified_name}' mandates explicit human approval before execution under L3A_EXECUTE_WITH_APPROVAL",
                risk_level=risk,
                requires_approval=True,
            )

        # 7. L3 — Execute (R0, R1, R2 direct execution for Founder/Admin; R3/R4 requires approval)
        if level == PermissionLevel.L3_EXECUTE:
            if risk in ("low", "medium") and perm in ("read_only", "scoped_write", "admin_write"):
                return PolicyDecision(
                    action=PolicyAction.ALLOW,
                    reason=f"Execution permitted for {risk_raw.upper() if risk_raw.startswith('r') else risk} risk tool under L3_EXECUTE",
                    risk_level=risk,
                    requires_approval=False,
                )
            return PolicyDecision(
                action=PolicyAction.REQUIRE_APPROVAL,
                reason=f"External/critical risk tool '{tool_spec.qualified_name}' requires approval under L3_EXECUTE",
                risk_level=risk,
                requires_approval=True,
            )

        return PolicyDecision(
            action=PolicyAction.DENY,
            reason="Unrecognized permission configuration",
            risk_level=risk,
            requires_approval=False,
        )
