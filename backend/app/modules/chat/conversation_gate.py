"""Conversation Gate & Intent Router for COSA Chat.

Implements P0 gate to prevent unintended tool calls on greetings/general questions
and routes user queries with strictly scoped capability namespaces.
"""

from dataclasses import dataclass
from enum import Enum
import re
from typing import Literal, Optional, FrozenSet

from app.modules.company_runtime.intent_classifier import WorkIntentClassifier


class CanonicalVerb(str, Enum):
    CONVERSE = "CONVERSE"          # Casual conversation, greeting, conversational Q&A
    SHAPE = "SHAPE"                # Clarify, structure, scope, plan
    INVESTIGATE = "INVESTIGATE"    # Read, search, research, query data/evidence
    JUDGE = "JUDGE"                # Evaluate against criteria, quality gates
    EXECUTE = "EXECUTE"            # Mutating action, external dispatch, tool call
    FINISH = "FINISH"              # Verify outcomes, produce certificate
    LEARN = "LEARN"                # Extract candidate lessons, memory promotion


class GateIntent(str, Enum):
    SOCIAL_CHAT = "social_chat"
    FOUNDER_BRIEF = "founder_brief"
    GENERAL_QUESTION = "general_question"
    KNOWLEDGE_SEARCH = "knowledge_search"
    PROJECT_DISCOVERY = "project_discovery"
    PROJECT_QUERY = "project_query"
    PROJECT_ANALYSIS = "project_analysis"
    DOMAIN_JOB = "domain_job"
    MISSION_COMMAND = "mission_command"
    TOOL_ACTION = "tool_action"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class GateDecision:
    intent: GateIntent
    confidence: float
    needs_project: bool
    needs_tools: bool
    needs_job: bool
    allowed_namespaces: FrozenSet[str]
    route: Literal["orchestrator", "chat_llm"]
    verb: CanonicalVerb = CanonicalVerb.CONVERSE
    should_route: bool = True
    raw_classification: Optional[dict] = None


SOCIAL_GREETING_PATTERNS = [
    r"^(chào|chao|xin chào|xin chao|hello|hi|hey|helo|alo|halo)(\s+(bạn|em|ad|bot|cosa|anh|chị|chi|nha|nhé|nhe|mọi người))?[\s!.,?~]*$",
    r"^(bạn là ai|ban la ai|ai là bạn|cậu là ai|em là ai|giới thiệu về bạn|bạn có thể làm gì)[\s!.,?~]*$",
    r"^(cảm ơn|cam on|thanks|thank you|cảm ơn bạn|cam on ban)(\s+(nha|nhé|nhe|rất nhiều))?[\s!.,?~]*$",
    r"^(tạm biệt|tam biet|bye|bye bye|goodbye)[\s!.,?~]*$",
    r"^(good morning|good afternoon|good evening)[\s!.,?~]*$",
    r"^(bạn khỏe không|ban khoe khong|khỏe không|khoe khong)[\s!.,?~]*$",
]

FOUNDER_BRIEF_PATTERNS = [
    r"^(hôm nay thế nào|hom nay the nao|hôm nay có gì|hom nay co gi|tình hình hôm nay|tinh hinh hom nay|tổng hợp hôm nay|tong hop hom nay|báo cáo hôm nay|bao cao hom nay|founder brief|daily brief|company pulse)[\s!.,?~]*$",
    r"^(tình hình công ty|tinh hinh cong ty|công ty thế nào|cong ty the nao|công ty hôm nay|nhịp đập công ty|báo cáo nhanh|bao cao nhanh)[\s!.,?~]*$",
    r"^(tổng kết ngày|tong ket ngay|hôm nay cần làm gì|hom nay can lam gi)[\s!.,?~]*$",
]

GENERAL_QUESTION_PATTERNS = [
    r"(.*?)\s+(là gì|la gi|như thế nào|nhu the nao|nghĩa là gì|la sao|hoạt động ra sao|la thuoc gi)\??$",
    r"^(giải thích|giai thich|hướng dẫn|huong dan|cho tôi biết về|cho toi biet ve)\s+(.*?)$",
    r"^(cách tính|cach tinh|công thức|cong thuc|khái niệm|khai niem)\s+(.*?)$",
]

KNOWLEDGE_SEARCH_PATTERNS = [
    r"(tra cứu|tra cuu|tìm trong vault|tim trong vault|tài liệu|tai lieu|chính sách|chinh sach|quy định|quy dinh|sop)\s+(.*?)$",
    r"(chính sách|quy định|hướng dẫn nội bộ)\s+(.*?)$",
]

MISSION_COMMAND_PATTERNS = [
    r"(tìm|tim|find|săn|san)\s+(\d+\s+)?(khách hàng|khach hang|lead|prospect|đối tác|doi tac|khách|khach)",
    r"(lên|tạo|chạy|thực hiện|triển khai)\s+(chiến dịch|chien dich|campaign|marketing|quảng cáo|quang cao)",
    r"(lập|soạn|tạo)\s+(landing page|trang đích|trang dich)",
]

PROJECT_DISCOVERY_PATTERNS = [
    r"(danh sách|danh sach|liệt kê|liet ke|show|list|tất cả|tat ca|những|cac|các)\s+(dự án|du an|project|portfolio)",
    r"(tôi|chúng ta|cty|công ty)\s+(đang có|co|có)\s+(những|các|mấy)?\s*(dự án|du an|project)",
    r"(có|co)\s+(những|các)?\s*(dự án|du an|project)\s*(nào|nao)",
]

PROJECT_QUERY_PATTERNS = [
    r"(kiểm tra|kiem tra|check|tình hình|tinh hinh|tiến độ|tien do|trạng thái|trang thai|chi tiết|chi tiet|xem|tra cứu|tra cuu)\s+(dự án|du an|project|task|nhiệm vụ|cong viec|công việc|công ty|work)",
    r"(dự án|du an|project)\s+([a-zA-Z0-9_\-]+)\s+(sao rồi|thế nào|tiến độ|trạng thái)",
]

PROJECT_ANALYSIS_PATTERNS = [
    r"(phân tích|phan tich|đánh giá|danh gia|báo cáo|bao cao|tổng kết|tong ket)\s+(sales|marketing|doanh thu|tài chính|tai chinh|chi phí|chi phi|pháp lý|phap ly|kpi|okr|lead|khách hàng|khach hang)",
]


def resolve(text: str) -> GateDecision:
    """Resolve user query intent into a routing & permission decision."""
    cleaned = text.strip().lower()
    base = WorkIntentClassifier.classify(text)

    # 1. Social Greeting (Fast-path: 0 tools, 0 project query)
    for pat in SOCIAL_GREETING_PATTERNS:
        if re.search(pat, cleaned, re.IGNORECASE):
            return GateDecision(
                intent=GateIntent.SOCIAL_CHAT,
                confidence=0.98,
                needs_project=False,
                needs_tools=False,
                needs_job=False,
                allowed_namespaces=frozenset(),
                route="chat_llm",
                verb=CanonicalVerb.CONVERSE,
                should_route=False,
                raw_classification=base,
            )

    # 2. Founder Daily Brief Intent
    for pat in FOUNDER_BRIEF_PATTERNS:
        if re.search(pat, cleaned, re.IGNORECASE):
            return GateDecision(
                intent=GateIntent.FOUNDER_BRIEF,
                confidence=0.95,
                needs_project=True,
                needs_tools=True,
                needs_job=False,
                allowed_namespaces=frozenset({"runtime", "tasks", "sales", "finance"}),
                route="chat_llm",
                verb=CanonicalVerb.INVESTIGATE,
                should_route=True,
                raw_classification=base,
            )

    # 3. Knowledge Search Intent
    for pat in KNOWLEDGE_SEARCH_PATTERNS:
        if re.search(pat, cleaned, re.IGNORECASE):
            return GateDecision(
                intent=GateIntent.KNOWLEDGE_SEARCH,
                confidence=0.90,
                needs_project=False,
                needs_tools=True,
                needs_job=False,
                allowed_namespaces=frozenset({"vault"}),
                route="chat_llm",
                verb=CanonicalVerb.INVESTIGATE,
                should_route=True,
                raw_classification=base,
            )

    # 4. Mission Command Intent (Sales/Marketing/Landing Page)
    for pat in MISSION_COMMAND_PATTERNS:
        if re.search(pat, cleaned, re.IGNORECASE):
            return GateDecision(
                intent=GateIntent.MISSION_COMMAND,
                confidence=0.92,
                needs_project=True,
                needs_tools=True,
                needs_job=True,
                allowed_namespaces=frozenset({"sales", "marketing", "tasks", "runtime", "chat"}),
                route="chat_llm",
                verb=CanonicalVerb.EXECUTE,
                should_route=True,
                raw_classification=base,
            )

    # 5. General Conceptual Question (0 tools)
    for pat in GENERAL_QUESTION_PATTERNS:
        if re.search(pat, cleaned, re.IGNORECASE):
            return GateDecision(
                intent=GateIntent.GENERAL_QUESTION,
                confidence=0.85,
                needs_project=False,
                needs_tools=False,
                needs_job=False,
                allowed_namespaces=frozenset(),
                route="chat_llm",
                verb=CanonicalVerb.CONVERSE,
                should_route=False,
                raw_classification=base,
            )

    # 6. Project Discovery
    for pat in PROJECT_DISCOVERY_PATTERNS:
        if re.search(pat, cleaned, re.IGNORECASE):
            return GateDecision(
                intent=GateIntent.PROJECT_DISCOVERY,
                confidence=0.90,
                needs_project=True,
                needs_tools=True,
                needs_job=False,
                allowed_namespaces=frozenset({"strategy"}),
                route="chat_llm",
                verb=CanonicalVerb.INVESTIGATE,
                should_route=True,
                raw_classification=base,
            )

    # 7. Project Query
    for pat in PROJECT_QUERY_PATTERNS:
        if re.search(pat, cleaned, re.IGNORECASE):
            return GateDecision(
                intent=GateIntent.PROJECT_QUERY,
                confidence=0.90,
                needs_project=True,
                needs_tools=True,
                needs_job=False,
                allowed_namespaces=frozenset({"strategy", "tasks", "runtime", "company", "sales", "finance"}),
                route="chat_llm",
                verb=CanonicalVerb.INVESTIGATE,
                should_route=True,
                raw_classification=base,
            )

    # 8. Project Analysis
    for pat in PROJECT_ANALYSIS_PATTERNS:
        if re.search(pat, cleaned, re.IGNORECASE):
            namespaces = {"strategy"}
            if any(k in cleaned for k in ["sales", "doanh thu", "lead", "khách hàng", "khach hang"]):
                namespaces.add("sales")
            if any(k in cleaned for k in ["tài chính", "tai chinh", "chi phí", "chi phi"]):
                namespaces.add("finance")
            return GateDecision(
                intent=GateIntent.PROJECT_ANALYSIS,
                confidence=0.88,
                needs_project=True,
                needs_tools=True,
                needs_job=False,
                allowed_namespaces=frozenset(namespaces),
                route="chat_llm",
                verb=CanonicalVerb.JUDGE,
                should_route=True,
                raw_classification=base,
            )

    # 9. Domain Job / Orchestrator Work from base classifier
    base_intent = base.get("intent")
    if base_intent in {"CYCLE_CHANGE", "STRATEGIC", "COMPANY_WORK", "APPROVAL"}:
        return GateDecision(
            intent=GateIntent.DOMAIN_JOB,
            confidence=base.get("confidence", 0.90),
            needs_project=True,
            needs_tools=False,
            needs_job=True,
            allowed_namespaces=frozenset({"chat"}),
            route="orchestrator",
            verb=CanonicalVerb.SHAPE,
            should_route=True,
            raw_classification=base,
        )

    if base_intent == "QUICK_TASK":
        return GateDecision(
            intent=GateIntent.TOOL_ACTION,
            confidence=base.get("confidence", 0.85),
            needs_project=True,
            needs_tools=True,
            needs_job=False,
            allowed_namespaces=frozenset({"tasks", "runtime", "strategy"}),
            route="chat_llm",
            verb=CanonicalVerb.EXECUTE,
            should_route=True,
            raw_classification=base,
        )

    # 10. Fallback / Ambiguous (only allow proposal action for safe flow)
    return GateDecision(
        intent=GateIntent.AMBIGUOUS,
        confidence=0.70,
        needs_project=False,
        needs_tools=False,
        needs_job=False,
        allowed_namespaces=frozenset({"chat"}),
        route="chat_llm",
        verb=CanonicalVerb.CONVERSE,
        should_route=False,
        raw_classification=base,
    )
