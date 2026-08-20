"""
COSA Intent Router Implementation
Bộ định tuyến ý định tất định (Deterministic Intent Classifier) (Structure.md Mục 15 & CLAUDE.md Mục 9).
Chặn đứng 100% việc nạp context dự án hoặc quét database khi người dùng chỉ gửi lời chào hỏi.
"""
import re
from typing import Any, Dict, List, Optional
from agent.routing.base import (
    IntentCategory,
    IntentClassificationResult,
    IntentRouterInterface,
)


class IntentRouter(IntentRouterInterface):
    """Hiện thực bộ phân loại ý định người dùng độc lập"""

    # Danh mục từ khóa chào hỏi thông dụng (Việt & Anh)
    GREETING_PATTERNS = [
        r"^(?:xin\s+)?chào(?:\s+bạn|\s+em|\s+anh|\s+chị|\s+bot|\s+ad|\s+cosa|\s+ai|\s+mọi\s+người|\s+cả\s+nhà)?[\s!\.\?]*$",
        r"^alo(?:\s+bot|\s+ad|\s+bạn|\s+anh|\s+em)?[\s!\.\?]*$",
        r"^hi(?:\s+there|\s+bot|\s+all|\s+everyone|\s+friend)?[\s!\.\?]*$",
        r"^hello(?:\s+there|\s+bot|\s+all|\s+everyone|\s+friend)?[\s!\.\?]*$",
        r"^hey(?:\s+there|\s+bot|\s+all)?[\s!\.\?]*$",
        r"^good\s+(?:morning|afternoon|evening|day)[\s!\.\?]*$",
        r"^chào\s+buổi\s+(?:sáng|trưa|chiều|tối)[\s!\.\?]*$",
    ]

    # Pattern nhận diện nhắc đích danh dự án
    PROJECT_TAG_PATTERN = r"@([a-zA-Z0-9_-]+)"
    PROJECT_KEYWORD_PATTERN = r"(?:dự\s*án|project)\s+([a-zA-Z0-9_\-]+)"

    # Từ khóa chiến lược & Startup Stage
    STRATEGY_KEYWORDS = ["chiến lược", "strategy", "giai đoạn", "startup stage", "pmf", "okr", "12wy", "tầm nhìn", "mission"]
    # Từ khóa nghiên cứu & Marketing
    MARKETING_KEYWORDS = ["nghiên cứu thị trường", "market research", "đối thủ", "competitor", "icp", "khách hàng mục tiêu", "định vị", "positioning", "copywriting"]
    # Từ khóa bán hàng & CRM
    SALES_KEYWORDS = ["lead", "leads", "khách hàng tiềm năng", "bán hàng", "sales pipeline", "doanh thu", "chốt deal"]
    # Từ khóa tài chính
    FINANCE_KEYWORDS = ["tài chính", "finance", "tt58", "kế toán", "chi phí", "runway", "dòng tiền", "p&l", "báo cáo tài chính"]
    # Từ khóa lập trình & kỹ thuật
    CODING_KEYWORDS = ["code", "lập trình", "refactor", "bug", "buildspec", "deploy", "fix", "kiểm thử", "test"]

    async def route_intent(
        self, 
        user_message: str, 
        current_session_context: Optional[Dict[str, Any]] = None
    ) -> IntentClassificationResult:
        """Phân loại ý định từ tin nhắn người dùng mà KHÔNG tự ý quét database"""
        clean_text = user_message.strip().lower()

        # 1. KIỂM TRA LỜI CHÀO (GREETING) — CHẶN ĐỨNG QUÉT CONTEXT NGẦM
        for pattern in self.GREETING_PATTERNS:
            if re.match(pattern, clean_text, re.IGNORECASE):
                return IntentClassificationResult(
                    category=IntentCategory.GREETING,
                    confidence=1.0,
                    requires_project_context=False,
                    target_project_id=None,
                    suggested_skills=[],
                    suggested_tools=[],
                    suggested_workflow_id=None,
                    extracted_parameters={"is_greeting": True}
                )

        # 2. KIỂM TRA NHẮC ĐÍCH DANH DỰ ÁN (EXPLICIT PROJECT MENTION)
        target_project_id: Optional[str] = None
        tag_match = re.search(self.PROJECT_TAG_PATTERN, user_message)
        if tag_match:
            target_project_id = tag_match.group(1)
        else:
            kw_match = re.search(self.PROJECT_KEYWORD_PATTERN, user_message, re.IGNORECASE)
            if kw_match:
                target_project_id = kw_match.group(1)

        requires_project = target_project_id is not None

        # 3. PHÂN LOẠI CÁC NHÓM Ý ĐỊNH NGHIỆP VỤ
        if any(kw in clean_text for kw in self.CODING_KEYWORDS):
            return IntentClassificationResult(
                category=IntentCategory.CODING_TASK,
                confidence=0.9,
                requires_project_context=requires_project,
                target_project_id=target_project_id,
                suggested_skills=["coding-refactor"],
                suggested_tools=["claude_code.execute", "filesystem.read", "filesystem.write"],
                suggested_workflow_id="wf-coding-task"
            )

        if any(kw in clean_text for kw in self.MARKETING_KEYWORDS):
            return IntentClassificationResult(
                category=IntentCategory.BUSINESS_QUERY,
                confidence=0.9,
                requires_project_context=requires_project,
                target_project_id=target_project_id,
                suggested_skills=["market-research", "positioning"],
                suggested_tools=["web.search", "crm.read"],
                suggested_workflow_id="wf-market-analysis"
            )

        if any(kw in clean_text for kw in self.SALES_KEYWORDS):
            return IntentClassificationResult(
                category=IntentCategory.BUSINESS_QUERY,
                confidence=0.9,
                requires_project_context=requires_project,
                target_project_id=target_project_id,
                suggested_skills=["lead-generation", "lead-qualification"],
                suggested_tools=["crm.read", "crm.write"],
                suggested_workflow_id="wf-lead-generation"
            )

        if any(kw in clean_text for kw in self.FINANCE_KEYWORDS):
            return IntentClassificationResult(
                category=IntentCategory.BUSINESS_QUERY,
                confidence=0.9,
                requires_project_context=requires_project,
                target_project_id=target_project_id,
                suggested_skills=["tt58-audit", "financial-modeling"],
                suggested_tools=["finance.read"],
                suggested_workflow_id="wf-finance-report"
            )

        if any(kw in clean_text for kw in self.STRATEGY_KEYWORDS):
            return IntentClassificationResult(
                category=IntentCategory.STRATEGY_ADVICE,
                confidence=0.85,
                requires_project_context=requires_project,
                target_project_id=target_project_id,
                suggested_skills=["pmf-discovery", "okr-setting"],
                suggested_tools=["knowledge.search"],
                suggested_workflow_id="wf-strategy-planning"
            )

        # Mặc định là General Chat (vẫn không tự ý nạp project context nếu không yêu cầu)
        return IntentClassificationResult(
            category=IntentCategory.GENERAL_CHAT,
            confidence=0.7,
            requires_project_context=requires_project,
            target_project_id=target_project_id,
            suggested_skills=[],
            suggested_tools=[]
        )
