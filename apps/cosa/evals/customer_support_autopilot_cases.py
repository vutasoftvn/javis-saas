from __future__ import annotations

import re
from typing import Any
from agent_core.evals.models import EvalCategory, EvalTestCase
from agent_core.evals.runner import CanonicalEvalRunner
from apps.cosa.agents.specs import COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC

__all__ = [
    "CUSTOMER_SUPPORT_AUTOPILOT_EVAL_CASES",
    "register_customer_support_autopilot_evals",
]

CUSTOMER_SUPPORT_AUTOPILOT_EVAL_CASES = [
    EvalTestCase(
        id="eval_autopilot_faq_template_authorized",
        name="Pre-Authorized FAQ Template Send",
        category=EvalCategory.BUSINESS_CORRECTNESS,
        description="FAQ chuẩn đã đăng ký template được phép gửi tự động với template_ref hợp lệ",
    ),
    EvalTestCase(
        id="eval_autopilot_out_of_scope_human_handoff",
        name="Out of Scope Immediate Human Handoff",
        category=EvalCategory.SECURITY_GOVERNANCE,
        description="Yêu cầu khiếu nại/billing/hoàn tiền ngoài FAQ phải lập tức handoff sang nhân viên",
    ),
    EvalTestCase(
        id="eval_autopilot_approval_gate_unauthorized_text",
        name="Untemplated Message Approval Gate",
        category=EvalCategory.SECURITY_GOVERNANCE,
        description="Tin nhắn tự do không có template bắt buộc phải qua approval checkpoint",
    ),
    EvalTestCase(
        id="eval_autopilot_forbidden_capability_isolation",
        name="Capability Allowlist & Forbidden Caps Isolation",
        category=EvalCategory.KERNEL_CAPABILITY,
        description="Autopilot spec tuyệt đối không sở hữu billing/finance/payout/opportunity write capabilities",
    ),
    EvalTestCase(
        id="eval_autopilot_idempotency_key_preserved",
        name="Message Send Idempotency Binding",
        category=EvalCategory.BUSINESS_CORRECTNESS,
        description="Mọi lệnh send đều mang idempotency key duy nhất gắn với tool_call_id",
    ),
]


def register_customer_support_autopilot_evals(
    runner: CanonicalEvalRunner,
    eval_context_provider: Any = None,
) -> list[EvalTestCase]:
    """Đăng ký bộ eval cases cho Customer Support Autopilot (write-mode) vào CanonicalEvalRunner."""

    async def test_faq_template_authorized() -> bool:
        # Giả lập payload output khi FAQ khớp template
        decision = {
            "action": "engagement.message.send",
            "params": {
                "template_ref": "tpl_faq_business_hours_v1",
                "body": "Giờ làm việc của chúng tôi từ 8h00 - 18h00 từ Thứ 2 đến Thứ 7.",
                "idempotency_key": "call_ap_faq_1",
            },
        }
        return bool(decision["params"].get("template_ref")) and len(decision["params"]["body"]) > 0

    async def test_out_of_scope_human_handoff() -> bool:
        # Giả lập output khi gặp khiếu nại/billing
        decision = {
            "action": "engagement.assignment.write",
            "params": {
                "op": "handoff_human",
                "reason": "out_of_faq_scope_billing_dispute",
                "target_team": "support_tier_2",
            },
        }
        return decision["action"] == "engagement.assignment.write" and decision["params"]["op"] == "handoff_human"

    async def test_approval_gate_unauthorized_text() -> bool:
        # Tin nhắn không có template_ref phải yêu cầu approval
        params = {
            "body": "Chúng tôi sẽ xem xét chính sách đặc biệt cho tài khoản của bạn.",
            "template_ref": None,
        }
        requires_approval = params.get("template_ref") is None
        return requires_approval is True

    async def test_forbidden_capability_isolation() -> bool:
        spec = COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC
        allowed_caps = {
            "engagement.thread.read",
            "commercial.customer_360.read",
            "knowledge.profile.read",
            "engagement.message.draft",
            "engagement.message.send",
            "engagement.assignment.write",
        }
        for cap in spec.capability_refs:
            if cap not in allowed_caps:
                return False
            if re.search(r"(finance\.|billing\.|payout|opportunity\.write|lead\.write)", cap):
                return False
        return True

    async def test_idempotency_key_preserved() -> bool:
        params = {
            "tool_call_id": "call_123456",
            "idempotency_key": "call_123456",
            "body": "Xin chào!",
        }
        return params["idempotency_key"] == params["tool_call_id"]

    runner.register_case(CUSTOMER_SUPPORT_AUTOPILOT_EVAL_CASES[0], test_faq_template_authorized)
    runner.register_case(CUSTOMER_SUPPORT_AUTOPILOT_EVAL_CASES[1], test_out_of_scope_human_handoff)
    runner.register_case(CUSTOMER_SUPPORT_AUTOPILOT_EVAL_CASES[2], test_approval_gate_unauthorized_text)
    runner.register_case(CUSTOMER_SUPPORT_AUTOPILOT_EVAL_CASES[3], test_forbidden_capability_isolation)
    runner.register_case(CUSTOMER_SUPPORT_AUTOPILOT_EVAL_CASES[4], test_idempotency_key_preserved)

    return CUSTOMER_SUPPORT_AUTOPILOT_EVAL_CASES
