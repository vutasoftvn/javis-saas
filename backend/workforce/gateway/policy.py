from enum import IntEnum
from typing import Dict, Any, Optional
from dataclasses import dataclass


class RiskLevel(IntEnum):
    R0_READ_ONLY = 0        # Read-only / không side effect
    R1_RECOMMENDATION = 1   # AI recommendation / draft
    R2_REVERSIBLE_WRITE = 2 # Reversible internal write (tạo task, update crm draft)
    R3_EXTERNAL_SIDE_EFFECT = 3 # External side effect (gửi email, publish social)
    R4_HIGH_RISK = 4        # High-risk / financial post / database delete / deploy


@dataclass
class PolicyEvaluationResult:
    allowed: bool
    requires_approval: bool
    risk_level: RiskLevel
    reason: str


class RiskPolicyEvaluator:
    """Đánh giá mức độ rủi ro và xác định xem tool execution có cần Human Approval hay không."""

    @staticmethod
    def evaluate(
        tool_risk_level: int,
        requires_approval_flag: bool = False,
        agent_role: Optional[str] = None
    ) -> PolicyEvaluationResult:
        level = RiskLevel(min(max(tool_risk_level, 0), 4))

        # R0 & R1: Luôn tự động cho phép
        if level in (RiskLevel.R0_READ_ONLY, RiskLevel.R1_RECOMMENDATION):
            return PolicyEvaluationResult(
                allowed=True,
                requires_approval=False,
                risk_level=level,
                reason="Safe action (R0/R1) executed automatically."
            )

        # R2: Có thể cấu hình theo flag
        if level == RiskLevel.R2_REVERSIBLE_WRITE:
            need_appr = requires_approval_flag
            return PolicyEvaluationResult(
                allowed=True,
                requires_approval=need_appr,
                risk_level=level,
                reason="Reversible internal write (R2)." if not need_appr else "R2 configured to require human approval."
            )

        # R3 & R4: Bắt buộc hoặc ưu tiên Human Approval
        if level == RiskLevel.R3_EXTERNAL_SIDE_EFFECT:
            return PolicyEvaluationResult(
                allowed=True,
                requires_approval=True,
                risk_level=level,
                reason="External side-effect (R3) requires Human Approval."
            )

        # R4: Mandatory Approval
        return PolicyEvaluationResult(
            allowed=True,
            requires_approval=True,
            risk_level=RiskLevel.R4_HIGH_RISK,
            reason="High-risk / destructive / financial operation (R4) requires Mandatory Human Approval."
        )
