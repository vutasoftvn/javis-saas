from enum import StrEnum
from typing import Optional, Set
import re


class Intent(StrEnum):
    # Co-Founder Intent Layers (F4 Spec)
    GREETING = "GREETING"
    FOUNDER_REVIEW = "FOUNDER_REVIEW"
    FOUNDER_DECISION = "FOUNDER_DECISION"
    FOUNDER_COMMAND = "FOUNDER_COMMAND"
    FOUNDER_REFLECTION = "FOUNDER_REFLECTION"

    # Core Domain & Operational Intents
    GENERAL_CHAT = "GENERAL_CHAT"
    PROJECT_QUERY = "PROJECT_QUERY"
    PROJECT_ANALYSIS = "PROJECT_ANALYSIS"
    TASK_MANAGEMENT = "TASK_MANAGEMENT"
    OKR_MANAGEMENT = "OKR_MANAGEMENT"
    SALES = "SALES"
    MARKETING = "MARKETING"
    FINANCE = "FINANCE"
    LEGAL = "LEGAL"
    RESEARCH = "RESEARCH"
    DEVELOPER = "DEVELOPER"
    AUTOMATION = "AUTOMATION"
    UNKNOWN = "UNKNOWN"


GREETING_EXACT: Set[str] = {
    "chào",
    "xin chào",
    "chào bạn",
    "chào cosa",
    "chào javis",
    "hello",
    "hello cosa",
    "hello javis",
    "hi",
    "hi cosa",
    "hi javis",
    "hey",
    "hey cosa",
    "alo",
    "cảm ơn",
    "cảm ơn bạn",
    "thanks",
    "thank you",
}


def deterministic_intent(message: str) -> Optional[Intent]:
    """Phân loại intent tất định: Nếu là câu chào hoặc hội thoại cơ bản, trả về ngay GENERAL_CHAT."""
    if not message:
        return Intent.GENERAL_CHAT

    normalized = message.strip().lower()
    # Loại bỏ dấu câu ở cuối (vd: "chào!", "hello?")
    clean_msg = re.sub(r"[?!.,;:~]+$", "", normalized).strip()

    if clean_msg in GREETING_EXACT:
        return Intent.GENERAL_CHAT

    # Kiểm tra prefix câu chào ngắn (vd: "hello cosa", "chào bạn")
    for greeting in ["chào", "xin chào", "hello", "hi", "hey"]:
        if clean_msg == greeting or clean_msg.startswith(f"{greeting} "):
            # Nếu chỉ là chào hỏi ngắn dưới 4 từ
            if len(clean_msg.split()) <= 3:
                return Intent.GENERAL_CHAT

    return None


