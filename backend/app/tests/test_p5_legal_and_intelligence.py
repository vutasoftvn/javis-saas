import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.core.snowflake import generate_snowflake_id
from app.db.models import WorkspaceMember
from app.workforce.memory.models import AgentMemoryEntry
from app.business.legal import legal_review_service
from app.business.legal.router import status, AnalyzeContractRequest, analyze_contract


def test_legal_cross_tenant_forbidden():
    """Verify that user cannot access legal status of another workspace."""
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = generate_snowflake_id()

    other_ws_id = generate_snowflake_id()
    db = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        status(workspace_id=other_ws_id, member=member, db=db)

    assert exc_info.value.status_code == 403


def test_contract_risk_analyzer_penalty_cap():
    """Verify detection of penalty clauses exceeding the 8% statutory limit."""
    contract = """
    ĐIỀU KHOẢN PHẠT VI PHẠM:
    Nếu Bên B chậm tiến độ bàn giao quá 5 ngày, Bên B sẽ bị phạt 15% tổng giá trị hợp đồng
    và phải bồi thường toàn bộ thiệt hại phát sinh.
    """
    res = legal_review_service.analyze_contract_risks(contract, "COMMERCIAL_SERVICE")

    assert res["status"] == "success"
    assert res["total_risks_found"] >= 1
    penalty_risk = next((r for r in res["risks"] if r["category"] == "PENALTY"), None)
    assert penalty_risk is not None
    assert penalty_risk["severity"] == "HIGH"
    assert "8%" in penalty_risk["issue"]
    assert res["safety_score"] < 100


def test_contract_risk_analyzer_ip_clause():
    """Verify detection of total IP ownership transfer risks."""
    contract = """
    ĐIỀU KHOẢN SỞ HỮU TRÍ TUỆ:
    Bên B đồng ý chuyển giao toàn bộ quyền tác giả và toàn quyền sở hữu mọi mã nguồn và công nghệ gốc cho Bên A.
    Bên A có quyền chấm dứt bất kỳ lúc nào mà không cần báo trước.
    """
    res = legal_review_service.analyze_contract_risks(contract, "COMMERCIAL_SERVICE")

    assert res["status"] == "success"
    assert res["total_risks_found"] >= 2
    ip_risk = next((r for r in res["risks"] if r["category"] == "INTELLECTUAL_PROPERTY"), None)
    assert ip_risk is not None
    assert ip_risk["severity"] == "HIGH"

    term_risk = next((r for r in res["risks"] if r["category"] == "TERMINATION"), None)
    assert term_risk is not None
    assert term_risk["severity"] == "HIGH"


def test_contract_risk_analyzer_clean_contract():
    """Verify that a compliant contract scores highly and returns safe status."""
    contract = """
    HỢP ĐỒNG DỊCH VỤ PHẦN MỀM SAAS:
    - Thời hạn thanh toán: 15 ngày kể từ ngày xuất hóa đơn hợp lệ.
    - Mức phạt vi phạm: Tối đa không quá 8% giá trị phần nghĩa vụ bị vi phạm theo Luật Thương Mại.
    - Giải quyết tranh chấp: Tại Trung tâm Trọng tài Quốc tế Việt Nam (VIAC).
    """
    res = legal_review_service.analyze_contract_risks(contract, "COMMERCIAL_SERVICE")

    assert res["status"] == "success"
    assert res["total_risks_found"] == 0
    assert res["safety_score"] == 100
    assert res["risk_level"] == "AN TOÀN"


def test_l4_pattern_learning_recording():
    """Verify recording lessons into L4 pattern memory."""
    ws_id = generate_snowflake_id()
    db = MagicMock()

    res = legal_review_service.record_l4_pattern_lesson(
        db=db,
        workspace_id=ws_id,
        domain="LEGAL",
        lesson_text="Khách hàng ngành Tài chính luôn yêu cầu SLA 99.9% và giới hạn phạt 8%.",
        tags=["sla", "finance", "contract"],
    )

    assert res["status"] == "success"
    assert res["layer"] == "L4"
    assert res["domain"] == "LEGAL"
    assert db.commit.called
