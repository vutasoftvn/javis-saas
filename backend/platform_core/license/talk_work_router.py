from typing import Any, Dict, Optional
from platform_core.license.intent_classifier import WorkIntentClassifier


class TalkWorkMode:
    TALK = "TALK"
    WORK = "WORK"


class TalkWorkRouter:
    """Routes voice/chat inputs between instant TALK (Realtime response) and asynchronous WORK (Agent Runtime mission)."""

    TALK_KEYWORDS = {
        "xin chào", "hello", "bạn là ai", "thời tiết", "giải thích", "nghĩa là gì",
        "hôm nay", "tóm tắt nhanh", "kể chuyện", "chào bạn", "cảm ơn"
    }

    @classmethod
    def classify_talk_vs_work(cls, text: str) -> Dict[str, Any]:
        lower_text = text.lower().strip()
        work_intent = WorkIntentClassifier.classify(text)

        # 1. If explicit work/mission intent detected with high confidence
        if work_intent["intent"] in ("COMPANY_WORK", "CYCLE_CHANGE", "STRATEGIC", "APPROVAL"):
            return {
                "mode": TalkWorkMode.WORK,
                "intent": work_intent["intent"],
                "confidence": work_intent.get("confidence", 0.9),
                "target_agent": "chief_of_staff" if work_intent["intent"] in ("COMPANY_WORK", "STRATEGIC", "CYCLE_CHANGE") else "specialist",
                "description": f"Asynchronous multi-agent execution required for {work_intent['intent']}",
            }

        # 2. Check for simple conversational TALK keywords
        if any(kw in lower_text for kw in cls.TALK_KEYWORDS) and len(lower_text.split()) < 10:
            return {
                "mode": TalkWorkMode.TALK,
                "intent": "CHAT",
                "confidence": 0.95,
                "target_agent": "realtime_companion",
                "description": "Instant conversational response via Realtime voice companion",
            }

        # 3. Default routing based on work classifier
        if work_intent["intent"] == "QUICK_TASK":
            return {
                "mode": TalkWorkMode.WORK,
                "intent": "QUICK_TASK",
                "confidence": 0.85,
                "target_agent": "specialist",
                "description": "Quick operational task dispatch",
            }

        return {
            "mode": TalkWorkMode.TALK,
            "intent": "CHAT",
            "confidence": 0.80,
            "target_agent": "realtime_companion",
            "description": "Conversational stream reply",
        }

    @classmethod
    def normalize_mission_state(cls, raw_status: str) -> str:
        s = raw_status.lower()
        if s in ("awaiting_approval", "pending_approval", "approval_required"):
            return "waiting_approval"
        if s in ("waiting_user", "needs_input", "user_input_required"):
            return "waiting_user"
        if s in ("running", "in_progress", "executing"):
            return "running"
        if s in ("completed", "succeeded", "finished"):
            return "completed"
        if s in ("failed", "error", "cancelled"):
            return "failed"
        return s
