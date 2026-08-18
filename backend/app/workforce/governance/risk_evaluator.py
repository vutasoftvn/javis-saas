from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any


class RiskTier(str, Enum):
    LOW = "LOW"            # Tự động chạy: Đọc dữ liệu, tóm tắt, draft
    HIGH = "HIGH"          # Cần Human/Lead duyệt: Gửi email, cập nhật CRM, sinh code
    CRITICAL = "CRITICAL"  # Chỉ đích danh Founder: Chi tiền, xóa DB, hạch toán tài chính, cấp quyền


@dataclass
class RiskEvaluation:
    tier: RiskTier
    requires_approval: bool
    required_role: str  # 'LEAD' hoặc 'FOUNDER'
    reason: str


class RiskPolicyEvaluator:
    """Đánh giá mức độ rủi ro của tác vụ hoặc lệnh gọi công cụ."""

    # Danh mục tool nhạy cảm cao
    CRITICAL_TOOLS = {
        "finance.post_entry",
        "system.database_drop",
        "iam.grant_founder_role",
        "payment.transfer_money",
        "deploy.production_release",
    }

    HIGH_RISK_TOOLS = {
        "email.send",
        "marketing.social.publish",
        "developer.claude_code",
        "crm.update",
        "sandbox.execute",
    }

    @classmethod
    def evaluate(
        cls,
        tool_key: Optional[str] = None,
        action_type: str = "TOOL_EXEC",
        risk_level_int: Optional[int] = 1,
        requires_approval_flag: bool = False,
    ) -> RiskEvaluation:
        risk_val = int(risk_level_int) if risk_level_int is not None else 1

        # 1. Kiểm tra Critical
        if tool_key in cls.CRITICAL_TOOLS or risk_val >= 4 or action_type == "PAYMENT":
            return RiskEvaluation(
                tier=RiskTier.CRITICAL,
                requires_approval=True,
                required_role="FOUNDER",
                reason=f"Action '{tool_key or action_type}' has CRITICAL financial/system impact. Requires Founder explicit approval."
            )

        # 2. Kiểm tra High Risk
        if tool_key in cls.HIGH_RISK_TOOLS or risk_val == 3 or requires_approval_flag or action_type in ["PUBLISH", "DATA_MUTATE"]:
            return RiskEvaluation(
                tier=RiskTier.HIGH,
                requires_approval=True,
                required_role="LEAD",
                reason=f"Action '{tool_key or action_type}' has external or mutating side-effects. Requires Lead review."
            )

        # 3. Mặc định LOW
        return RiskEvaluation(
            tier=RiskTier.LOW,
            requires_approval=False,
            required_role="NONE",
            reason=f"Action '{tool_key or action_type}' is low risk (read-only or local drafting). Auto-executing."
        )
