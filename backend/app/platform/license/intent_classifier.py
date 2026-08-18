import re
from typing import Dict, Any, Optional, List


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
    CYCLE_COMMAND_KEYWORDS = {
        "replan", "đổi cycle", "kế hoạch 13 tuần", "tuần 13", "kích hoạt chu kỳ",
        "kích hoạt cycle", "chốt chu kỳ", "áp dụng chu kỳ", "áp dụng cycle",
        "cycle change", "kích hoạt kế hoạch", "12wy", "chu kỳ"
    }
    CYCLE_KEYWORDS = {"chu kỳ chiến lược"}
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
    def extract_duration_weeks(cls, text: str) -> int:
        """Extract requested week count from natural text. Defaults to 13 weeks."""
        # Matches patterns like "6 tuần", "chu kỳ 8 tuần", "12 weeks", "4-week", "kế hoạch 5 tuần"
        match = re.search(r"(?:chu kỳ|cycle|kế hoạch)?\s*(\d{1,2})\s*(?:tuần|weeks?)", text, re.IGNORECASE)
        if match:
            try:
                weeks = int(match.group(1))
                if 1 <= weeks <= 52:
                    return weeks
            except ValueError:
                pass
        return 13

    @classmethod
    def extract_project_hint(cls, text: str) -> Optional[str]:
        """Extract project name or identifier hint from text."""
        match = re.search(r"(?:cho dự án|dự án|project)\s+([a-zA-Z0-9_\-\s]+)", text, re.IGNORECASE)
        if match:
            raw_hint = match.group(1).strip()
            # Stop at common delimiters if present
            for stop_word in [" trong ", " với ", " để ", " giai đoạn ", " và "]:
                pos = f" {raw_hint.lower()} ".find(stop_word)
                if pos != -1:
                    raw_hint = raw_hint[:pos].strip()
            if raw_hint and len(raw_hint) > 1:
                return raw_hint
        return None

    @classmethod
    def generate_confirmation_prompt(cls, duration_weeks: int, project_hint: Optional[str] = None) -> str:
        """Generate bi-directional confirmation prompt for Founder."""
        proj_str = f" cho Dự án **{project_hint}**" if project_hint else ""
        if duration_weeks == 13:
            return (
                f"✅ Đã nhận lệnh: Thiết lập Chu kỳ Chiến lược Chuẩn **13 tuần** (12 tuần thực thi + Tuần 13 Đánh giá & Transition){proj_str}.\n"
                f"Bạn có muốn kích hoạt chu kỳ và phân rã nhiệm vụ cho 5 phòng ban AI không?"
            )
        exec_weeks = duration_weeks - 1 if duration_weeks > 1 else 1
        return (
            f"✅ Đã nhận lệnh: Thiết lập Chu kỳ Chiến lược **{duration_weeks} tuần** ({exec_weeks} tuần thực thi + Tuần {duration_weeks} Đánh giá & Transition){proj_str}.\n"
            f"Tôi sẽ cấu trúc {duration_weeks} Weekly Plans tương ứng. Bạn có muốn kích hoạt ngay không?"
        )

    @classmethod
    def classify(cls, text: str) -> Dict[str, Any]:
        lower_text = text.lower()
        duration_weeks = cls.extract_duration_weeks(text)
        project_hint = cls.extract_project_hint(text)

        # 1. Approval Intent
        if any(kw in lower_text for kw in cls.APPROVAL_KEYWORDS):
            return {
                "intent": "APPROVAL",
                "confidence": 0.95,
                "suggested_route": "approvals",
                "description": "User requests approval decision on an existing item",
                "duration_weeks": duration_weeks,
                "project_hint": project_hint,
            }

        # 2. Cycle Change Intent (explicit activation/replan commands)
        if any(kw in lower_text for kw in cls.CYCLE_COMMAND_KEYWORDS):
            return {
                "intent": "CYCLE_CHANGE",
                "confidence": 0.90,
                "suggested_route": "cycle_planner",
                "description": "User intends to modify cycle planning or 12WY commitments",
                "duration_weeks": duration_weeks,
                "project_hint": project_hint,
                "confirmation_prompt": cls.generate_confirmation_prompt(duration_weeks, project_hint),
            }

        # 3. Strategic Intent (Strategy, planning, drafting, SWOT, 12WY design)
        if any(kw in lower_text for kw in cls.STRATEGIC_KEYWORDS) or any(kw in lower_text for kw in cls.CYCLE_KEYWORDS):
            return {
                "intent": "STRATEGIC",
                "confidence": 0.90,
                "suggested_route": "terra_strategic",
                "description": "Strategic planning, SWOT/TOWS, or PESTEL analysis",
                "duration_weeks": duration_weeks,
                "project_hint": project_hint,
                "confirmation_prompt": cls.generate_confirmation_prompt(duration_weeks, project_hint),
            }

        # 4. Company Work Intent (Multi-function missions)
        if any(kw in lower_text for kw in cls.COMPANY_WORK_KEYWORDS):
            return {
                "intent": "COMPANY_WORK",
                "confidence": 0.90,
                "suggested_route": "company_runtime",
                "description": "Decomposable multi-function company work",
                "duration_weeks": duration_weeks,
                "project_hint": project_hint,
            }

        # 5. Quick Task Intent
        if any(kw in lower_text for kw in cls.QUICK_TASK_KEYWORDS):
            return {
                "intent": "QUICK_TASK",
                "confidence": 0.85,
                "suggested_route": "single_function_task",
                "description": "Single-step or quick action item",
                "duration_weeks": duration_weeks,
                "project_hint": project_hint,
            }

        # 6. Fallback to CHAT
        return {
            "intent": "CHAT",
            "confidence": 0.80,
            "suggested_route": "chat",
            "description": "Routine conversational or informational query",
            "duration_weeks": duration_weeks,
            "project_hint": project_hint,
        }

