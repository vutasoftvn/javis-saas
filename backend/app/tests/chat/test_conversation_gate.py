import pytest

from app.workforce.chat import conversation_gate
from app.workforce.chat.conversation_gate import GateIntent


def test_social_chat_intent():
    for text in ["chào", "xin chào em", "hello", "hi bạn", "bạn là ai", "cảm ơn nha", "bye bye"]:
        decision = conversation_gate.resolve(text)
        assert decision.intent == GateIntent.SOCIAL_CHAT, f"Failed for '{text}': got {decision.intent}"
        assert decision.needs_tools is False
        assert decision.needs_project is False
        assert decision.allowed_namespaces == frozenset()
        assert decision.route == "chat_llm"


def test_general_question_intent():
    for text in ["funnel marketing là gì?", "PESTEL là gì", "giải thích mô hình OKR", "cách tính chi phí CAC"]:
        decision = conversation_gate.resolve(text)
        assert decision.intent == GateIntent.GENERAL_QUESTION, f"Failed for '{text}': got {decision.intent}"
        assert decision.needs_tools is False
        assert decision.needs_project is False
        assert decision.allowed_namespaces == frozenset()
        assert decision.route == "chat_llm"


def test_project_discovery_intent():
    for text in ["tôi đang có những project nào?", "danh sách dự án hiện tại", "liệt kê tất cả dự án", "công ty có những dự án nào"]:
        decision = conversation_gate.resolve(text)
        assert decision.intent == GateIntent.PROJECT_DISCOVERY, f"Failed for '{text}': got {decision.intent}"
        assert decision.needs_tools is True
        assert decision.needs_project is True
        assert "strategy" in decision.allowed_namespaces
        assert decision.route == "chat_llm"


def test_project_query_intent():
    for text in ["kiểm tra project mID", "tiến độ dự án CRM sao rồi", "chi tiết công việc dự án Alpha"]:
        decision = conversation_gate.resolve(text)
        assert decision.intent == GateIntent.PROJECT_QUERY, f"Failed for '{text}': got {decision.intent}"
        assert decision.needs_tools is True
        assert decision.needs_project is True
        assert "strategy" in decision.allowed_namespaces
        assert "tasks" in decision.allowed_namespaces
        assert decision.route == "chat_llm"


def test_project_analysis_intent():
    decision_sales = conversation_gate.resolve("phân tích sales quý này")
    assert decision_sales.intent == GateIntent.PROJECT_ANALYSIS
    assert "sales" in decision_sales.allowed_namespaces
    assert decision_sales.needs_tools is True

    decision_fin = conversation_gate.resolve("báo cáo tài chính và chi phí dự án")
    assert decision_fin.intent == GateIntent.PROJECT_ANALYSIS
    assert "finance" in decision_fin.allowed_namespaces
    assert decision_fin.needs_tools is True


def test_domain_job_intent():
    for text in ["đổi cycle 8 tuần cho dự án Alpha", "kế hoạch 13 tuần mới"]:
        decision = conversation_gate.resolve(text)
        assert decision.intent == GateIntent.DOMAIN_JOB
        assert decision.route == "orchestrator"
        assert decision.needs_job is True
        # STRATEGIC/COMPANY_WORK/APPROVAL (mọi DOMAIN_JOB trừ CYCLE_CHANGE) không có
        # dispatcher orchestrator riêng - chúng rơi vào vòng lặp chat_llm thường với
        # allowed_namespaces này. Phải còn "chat" để chat_propose_action luôn khả dụng,
        # nếu không thì model không có cách nào khác ngoài tự bịa "đã làm xong".
        assert "chat" in decision.allowed_namespaces


def test_tool_action_intent():
    decision = conversation_gate.resolve("sửa typo và fix nhanh tiêu đề")
    assert decision.intent == GateIntent.TOOL_ACTION
    assert decision.route == "chat_llm"
    assert "tasks" in decision.allowed_namespaces


def test_ambiguous_safe_fallback():
    decision = conversation_gate.resolve("qwerty asdfgh zxcvbn")
    assert decision.intent == GateIntent.AMBIGUOUS
    assert decision.needs_tools is False
    # An toàn vẫn có nghĩa là KHÔNG có tool đọc dữ liệu (strategy/tasks/...) - nhưng phải
    # còn đúng namespace "chat" để chat_propose_action khả dụng. Không có nó, model không
    # tool nào cả và tự bịa ra là đã hoàn thành yêu cầu (bug tái hiện ở
    # test_worker_offers_propose_action_instead_of_hallucinating_on_ambiguous_action_request).
    assert decision.allowed_namespaces == frozenset({"chat"})
    assert decision.route == "chat_llm"


def test_ambiguous_request_with_no_keyword_match_still_gets_propose_action():
    """Câu tái hiện đúng bug thật: không khớp bất kỳ pattern/từ khóa nào của gate, không
    phải chào hỏi, không phải câu hỏi khái niệm - nhưng rõ ràng là một yêu cầu có hệ quả
    thật ("cập nhật giai đoạn ... thành ..."), không phải trò chuyện phiếm."""
    decision = conversation_gate.resolve(
        "giai đoạn 1 và 2 đã triển khai xong, hãy cập nhật giai đoạn 3 thành test và prod"
    )
    assert "chat" in decision.allowed_namespaces
    assert "strategy" not in decision.allowed_namespaces


def test_stage_aware_consultation_intent():
    """P1.1: câu hỏi tư vấn chiến lược/next-action phải nạp Stage context (mục 21, AC-14),
    nhưng câu chào xã giao vẫn phải là SOCIAL_CHAT như cũ (AC-13)."""
    for text in [
        "Tôi nên làm gì tiếp theo với project X?",
        "chúng ta nên làm gì tiếp theo",
        "tôi nên ưu tiên gì lúc này",
        "chiến lược tiếp theo nào phù hợp cho dự án này",
        "giai đoạn dự án cần làm gì",
    ]:
        decision = conversation_gate.resolve(text)
        assert decision.intent == GateIntent.STAGE_AWARE_CONSULTATION, f"Failed for '{text}': got {decision.intent}"
        assert decision.needs_project is True
        assert decision.needs_tools is True
        assert "strategy" in decision.allowed_namespaces
        assert decision.route == "chat_llm"

    # AC-13: chào xã giao KHÔNG được rơi vào STAGE_AWARE_CONSULTATION
    greeting_decision = conversation_gate.resolve("chào")
    assert greeting_decision.intent == GateIntent.SOCIAL_CHAT


def test_save_persistence_intent():
    for text in [
        "lưu vào data nhé",
        "lưu vào db",
        "lưu vào vault",
        "lưu kế hoạch này",
        "xác nhận lộ trình này",
    ]:
        decision = conversation_gate.resolve(text)
        assert decision.intent == GateIntent.TOOL_ACTION
        assert decision.needs_tools is True
        assert "vault" in decision.allowed_namespaces
        assert "strategy" in decision.allowed_namespaces
        assert "project" in decision.allowed_namespaces

