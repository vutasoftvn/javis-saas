from enum import Enum
import re
from typing import Any, Optional
from pydantic import BaseModel, Field


class IntentType(str, Enum):
    CHAT = "CHAT"          # Casual greeting/chitchat (e.g. "Chào COSA")
    QUERY = "QUERY"        # Read-only state or data question (e.g. "Doanh thu tuần này bao nhiêu?")
    COMMAND = "COMMAND"    # Short-term bounded command/task (e.g. "Tạo báo cáo sales tuần này")
    GOAL = "GOAL"          # High-level business goal requiring decomposition (e.g. "Trong 6 tuần tăng pipeline lên 500tr")
    EVENT = "EVENT"        # External or lifecycle trigger event (e.g. "deal.updated", "invoice.overdue")


class IntentClassificationResult(BaseModel):
    intent_type: IntentType
    confidence: float = 1.0
    suggested_domain: str = "founder"  # founder, sales, finance, marketing, legal, learning
    suggested_title: Optional[str] = None
    target_metric: Optional[dict[str, Any]] = None
    reasoning: str = ""


class IntentClassifier:
    """Classifies incoming user messages or events into the 5 core COSA Agentic intent types.

    Architecture Note (Harness Integration Plan §5.1 / Item 1):
    This classifier operates in harmony with `app.modules.chat.conversation_gate.py::resolve()`
    and `app.modules.company_runtime.intent_classifier.py::WorkIntentClassifier`.
    While `conversation_gate` governs live chat tool gating (SOCIAL_CHAT vs TOOL_ACTION vs DOMAIN_JOB),
    `IntentClassifier` provides taxonomy translation (CHAT/QUERY/COMMAND/GOAL/EVENT) for
    autonomous agent orchestration, router APIs, and goal planning loops.
    """

    CHAT_PATTERNS = [
        r"^(chào|hello|hi|hey|alo|good morning|good afternoon|bạn là ai|who are you)\b",
        r"^(cảm ơn|thank you|thanks|bye|tạm biệt)\b",
    ]

    QUERY_PATTERNS = [
        r"^(bao nhiêu|thế nào|sao rồi|tình hình|thống kê|check|xem|tra cứu|show|list|get)\b",
        r"\?$",
        r"(doanh thu|pipeline|tồn kho|số dư|chi phí|danh sách|kết quả) (bao nhiêu|như thế nào|hiện tại)",
    ]

    GOAL_PATTERNS = [
        r"(trong \d+ (tuần|tháng|quý|ngày)|đạt mục tiêu|tăng|giảm|nâng cao|đạt được|xây dựng|triển khai)",
        r"(target|mục tiêu|kế hoạch \d+|tăng doanh số|tăng pipeline|tối ưu chi phí)",
    ]

    COMMAND_PATTERNS = [
        r"^(tạo|gửi|soạn|lập|xuất|tải|chạy|thực hiện|quét|sync|import|export|gửi mail|gửi tin)\b",
    ]

    @classmethod
    def classify(cls, text: str, context: Optional[dict[str, Any]] = None) -> IntentClassificationResult:
        normalized = text.strip().lower()

        # 1. Check EVENT if marked or structured
        if context and context.get("is_event"):
            return IntentClassificationResult(
                intent_type=IntentType.EVENT,
                confidence=1.0,
                suggested_domain=context.get("domain", "founder"),
                reasoning="Context marked as system event trigger.",
            )

        # 2. Check GOAL pattern
        has_goal_metric = bool(re.search(r"(\d+[\s]*(triệu|tỷ|tr|k|m|b|%|khách|lead|deal))", normalized))
        for pattern in cls.GOAL_PATTERNS:
            if re.search(pattern, normalized) and (has_goal_metric or "mục tiêu" in normalized or "kế hoạch" in normalized or "trong " in normalized):
                domain = "sales" if ("pipeline" in normalized or "khách" in normalized or "lead" in normalized or "sales" in normalized or "deal" in normalized) else ("finance" if ("chi phí" in normalized or "doanh thu" in normalized or "lợi nhuận" in normalized) else "founder")
                return IntentClassificationResult(
                    intent_type=IntentType.GOAL,
                    confidence=0.92,
                    suggested_domain=domain,
                    suggested_title=text.strip(),
                    reasoning="High-level goal syntax detected with timeline or metric constraints.",
                )

        # 3. Check COMMAND pattern
        for pattern in cls.COMMAND_PATTERNS:
            if re.search(pattern, normalized):
                domain = "sales" if ("khách" in normalized or "lead" in normalized or "sales" in normalized) else ("finance" if ("báo cáo tài chính" in normalized or "chi phí" in normalized) else "founder")
                return IntentClassificationResult(
                    intent_type=IntentType.COMMAND,
                    confidence=0.88,
                    suggested_domain=domain,
                    suggested_title=text.strip(),
                    reasoning="Direct operational command requiring short-turn action.",
                )

        # 4. Check QUERY pattern
        for pattern in cls.QUERY_PATTERNS:
            if re.search(pattern, normalized):
                domain = "sales" if ("pipeline" in normalized or "lead" in normalized or "sales" in normalized) else ("finance" if ("doanh thu" in normalized or "chi phí" in normalized or "lãi" in normalized or "lỗ" in normalized) else "founder")
                return IntentClassificationResult(
                    intent_type=IntentType.QUERY,
                    confidence=0.85,
                    suggested_domain=domain,
                    reasoning="Informational query seeking data summary or status.",
                )

        # 5. Check CHAT pattern
        for pattern in cls.CHAT_PATTERNS:
            if re.search(pattern, normalized):
                return IntentClassificationResult(
                    intent_type=IntentType.CHAT,
                    confidence=0.95,
                    suggested_domain="founder",
                    reasoning="Conversational greeting or chitchat.",
                )

        # Default fallback: COMMAND if action oriented, otherwise CHAT
        if len(text.split()) > 6:
            return IntentClassificationResult(
                intent_type=IntentType.COMMAND,
                confidence=0.70,
                suggested_domain="founder",
                suggested_title=text.strip(),
                reasoning="Defaulted complex prompt to COMMAND execution.",
            )

        return IntentClassificationResult(
            intent_type=IntentType.CHAT,
            confidence=0.75,
            suggested_domain="founder",
            reasoning="Defaulted brief utterance to CHAT.",
        )
