from typing import Dict, Any, Optional


class WorkIntentClassifier:
    """Classifies user intent into CHAT, QUICK_TASK, COMPANY_WORK, CYCLE_CHANGE, STRATEGIC, or APPROVAL."""

    INTENTS = {
        "CHAT",
        "QUICK_TASK",
        "COMPANY_WORK",
        "CYCLE_CHANGE",
        "STRATEGIC",
        "APPROVAL",
    }

    APPROVAL_KEYWORDS = {"approve", "duyệt", "reject", "từ chối", "phê duyệt", "chấp thuận", "xác nhận"}
    CYCLE_KEYWORDS = {"replan", "đổi cycle", "kế hoạch 13 tuần", "tuần 13", "cycle change", "12wy", "chu kỳ"}
    STRATEGIC_KEYWORDS = {"pestel", "swot", "tows", "chiến lược", "strategy", "tầm nhìn", "định vị"}
    COMPANY_WORK_KEYWORDS = {
        "beta launch", "launch", "ra mắt", "weekly mission", "nhiệm vụ tuần",
        "giảm burn", "10 beta users", "khởi chạy", "chuẩn bị", "dự án", "chiến dịch"
    }
    QUICK_TASK_KEYWORDS = {
        "fix", "typo", "sửa", "draft", "soạn", "ghi nhận", "tạo task", "hóa đơn",
        "chi phí", "kiểm tra", "check", "gửi email"
    }

    @classmethod
    def classify(cls, text: str) -> Dict[str, Any]:
        lower_text = text.lower()
        tokens = {t.strip(".,:;!?()[]{}") for t in lower_text.split()}

        # 1. Approval Intent
        if any(kw in lower_text for kw in cls.APPROVAL_KEYWORDS):
            return {
                "intent": "APPROVAL",
                "confidence": 0.95,
                "suggested_route": "approvals",
                "description": "User requests approval decision on an existing item",
            }

        # 2. Cycle Change Intent
        if any(kw in lower_text for kw in cls.CYCLE_KEYWORDS):
            return {
                "intent": "CYCLE_CHANGE",
                "confidence": 0.90,
                "suggested_route": "cycle_planner",
                "description": "User intends to modify cycle planning or 12WY commitments",
            }

        # 3. Strategic Intent
        if any(kw in lower_text for kw in cls.STRATEGIC_KEYWORDS):
            return {
                "intent": "STRATEGIC",
                "confidence": 0.90,
                "suggested_route": "terra_strategic",
                "description": "Strategic planning, SWOT/TOWS, or PESTEL analysis",
            }

        # 4. Company Work Intent (Multi-function missions)
        if any(kw in lower_text for kw in cls.COMPANY_WORK_KEYWORDS):
            return {
                "intent": "COMPANY_WORK",
                "confidence": 0.90,
                "suggested_route": "company_runtime",
                "description": "Decomposable multi-function company work",
            }

        # 5. Quick Task Intent
        if any(kw in lower_text for kw in cls.QUICK_TASK_KEYWORDS):
            return {
                "intent": "QUICK_TASK",
                "confidence": 0.85,
                "suggested_route": "single_function_task",
                "description": "Single-step or quick action item",
            }

        # 6. Fallback to CHAT
        return {
            "intent": "CHAT",
            "confidence": 0.80,
            "suggested_route": "chat",
            "description": "Routine conversational or informational query",
        }
