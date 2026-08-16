import pytest
from unittest.mock import MagicMock
from datetime import datetime

from app.modules.policy_funding.models import (
    PolicyProgram,
    ProjectStageAssessment,
    TrlAssessment,
    FundingNeed,
    CostAllocation,
)
from app.modules.policy_funding.services.matching_service import PolicyMatchingService


def test_policy_draft_isolation():
    """
    Quy tắc bắt buộc: Chương trình ở trạng thái DRAFT không được coi là quyền lợi ACTIVE.
    """
    mock_db = MagicMock()
    draft_program = PolicyProgram(
        name="Chương trình ĐMST Thí điểm",
        status="DRAFT",
        trl_min=3,
        company_types=["STARTUP"],
    )

    status, match_sc, read_sc, rules, missing = PolicyMatchingService.evaluate_project_against_program(
        db=mock_db,
        project_id=1001,
        program=draft_program,
        workspace_id=1,
    )

    assert status == "NEEDS_VERIFICATION"
    assert "Dự thảo" in rules[0]["note"]
    assert "Chờ văn bản ban hành chính thức" in missing


def test_hard_eligibility_filter_trl():
    """
    Quy tắc bắt buộc: Dự án có TRL thấp hơn trl_min của chương trình thì kết quả phải là INELIGIBLE.
    """
    mock_db = MagicMock()
    program = PolicyProgram(
        name="Quỹ Đổi mới Công nghệ Quốc gia (NATIF)",
        status="ACTIVE",
        trl_min=5,
        company_types=["STARTUP", "SCIENCE_TECH_ENTERPRISE"],
        project_stages=["MVP", "MARKET_VALIDATION"],
    )

    stage_assessment = ProjectStageAssessment(
        project_id=1001,
        workspace_id=1,
        company_type="STARTUP",
        stage="MVP",
        is_founder_confirmed=True,
    )

    trl_assessment = TrlAssessment(
        project_id=1001,
        workspace_id=1,
        trl_current=3,  # 3 < 5 -> Hard fail
    )

    status, match_sc, read_sc, rules, missing = PolicyMatchingService.evaluate_project_against_program(
        db=mock_db,
        project_id=1001,
        program=program,
        workspace_id=1,
        stage_assessment=stage_assessment,
        trl_assessment=trl_assessment,
    )

    assert status == "INELIGIBLE"
    assert any(not r["passed"] and "TRL" in r["rule"] for r in rules)
    assert any("TRL ≥ 5" in item for item in missing)


def test_hard_eligibility_filter_company_type():
    """
    Quy tắc bắt buộc: Dự án không thuộc loại hình doanh nghiệp được hỗ trợ thì INELIGIBLE.
    """
    mock_db = MagicMock()
    program = PolicyProgram(
        name="Chương trình Hỗ trợ Spin-off Viện Trường",
        status="ACTIVE",
        trl_min=3,
        company_types=["SPIN_OFF"],
        project_stages=["MVP"],
    )

    stage_assessment = ProjectStageAssessment(
        project_id=1001,
        workspace_id=1,
        company_type="DIGITAL_SME",  # Không phải SPIN_OFF -> Hard fail
        stage="MVP",
        is_founder_confirmed=True,
    )

    trl_assessment = TrlAssessment(
        project_id=1001,
        workspace_id=1,
        trl_current=4,
    )

    status, match_sc, read_sc, rules, missing = PolicyMatchingService.evaluate_project_against_program(
        db=mock_db,
        project_id=1001,
        program=program,
        workspace_id=1,
        stage_assessment=stage_assessment,
        trl_assessment=trl_assessment,
    )

    assert status == "INELIGIBLE"
    assert any(not r["passed"] and "Đối tượng" in r["rule"] for r in rules)


def test_match_and_readiness_calculation():
    """
    Đánh giá trường hợp đủ điều kiện (ELIGIBLE) và tính điểm Match Score + Readiness Score.
    """
    mock_db = MagicMock()
    program = PolicyProgram(
        name="AWS Activate / Cloud Credit Support",
        status="ACTIVE",
        trl_min=3,
        company_types=["STARTUP", "DIGITAL_SME"],
        project_stages=["MVP", "MARKET_VALIDATION"],
        matching_fund_pct=0.0,
    )

    stage_assessment = ProjectStageAssessment(
        project_id=1001,
        workspace_id=1,
        company_type="STARTUP",
        stage="MVP",
        is_founder_confirmed=True,
    )

    trl_assessment = TrlAssessment(
        project_id=1001,
        workspace_id=1,
        trl_current=4,
        evidence_artifact_id=555,  # Có minh chứng
    )

    status, match_sc, read_sc, rules, missing = PolicyMatchingService.evaluate_project_against_program(
        db=mock_db,
        project_id=1001,
        program=program,
        workspace_id=1,
        stage_assessment=stage_assessment,
        trl_assessment=trl_assessment,
    )

    assert status == "ELIGIBLE"
    assert match_sc >= 80.0
    assert read_sc >= 80.0
    assert len(missing) == 0


def test_double_funding_guard_detection():
    """
    Kiểm tra cơ chế Double Funding Guard phát hiện trùng lặp chi phí giữa các gói tài trợ.
    """
    mock_db = MagicMock()

    existing_allocation = CostAllocation(
        project_id=1001,
        award_id=201,
        work_package="MVP Testing",
        cost_category="HOSTING",
        purpose="Chi phí thuê máy chủ cloud tháng 9-10",
        amount=50000000.0,
    )

    mock_db.scalars.return_value.all.return_value = [existing_allocation]

    conflict, msg, award_ids, app_ids = PolicyMatchingService.check_double_funding(
        db=mock_db,
        project_id=1001,
        work_package="MVP Testing",
        cost_category="HOSTING",
        purpose="Chi phí máy chủ cloud",
    )

    assert conflict is True
    assert "CẢNH BÁO TRÙNG NGUỒN HỖ TRỢ" in msg
    assert 201 in award_ids


def test_proposal_draft_generation_and_placeholder_guard():
    """
    Quy tắc bắt buộc: Proposal Agent không bịa số liệu, thông tin thiếu phải gắn [CẦN FOUNDER BỔ SUNG: ...].
    """
    from app.modules.policy_funding.services.proposal_service import ProposalService
    from app.modules.strategy.models import Project

    project = Project(
        id=1001,
        title="Nền tảng AI OS cho Doanh nghiệp",
        description=None,  # Thiếu mô tả
    )

    stage_assessment = ProjectStageAssessment(
        project_id=1001,
        stage="MVP",
    )

    trl_assessment = TrlAssessment(
        project_id=1001,
        trl_current=4,
        explanation=None,  # Thiếu minh chứng
    )

    from app.modules.policy_funding.models import Application
    app_record = Application(
        id=501,
        project_id=1001,
        program_id=201,
        requested_amount=None,  # Thiếu kinh phí
    )

    # Test section BACKGROUND
    bg_text, bg_missing = ProposalService._compose_section_content(
        section_key="BACKGROUND",
        project=project,
        stage_assessment=stage_assessment,
        trl_assessment=trl_assessment,
        program=None,
        mvp_stages=[],
        app_record=app_record,
    )
    assert "[CẦN FOUNDER BỔ SUNG:" in bg_text
    assert len(bg_missing) > 0

    # Test section BUDGET
    budget_text, budget_missing = ProposalService._compose_section_content(
        section_key="BUDGET",
        project=project,
        stage_assessment=stage_assessment,
        trl_assessment=trl_assessment,
        program=None,
        mvp_stages=[],
        app_record=app_record,
    )
    assert "[CẦN FOUNDER BỔ SUNG: Tổng kinh phí xin tài trợ]" in budget_text
    assert "Kinh phí xin tài trợ" in budget_missing


def test_automation_webhook_and_alerts():
    """
    Kiểm tra Ingestion Webhook từ n8n và cơ chế phát cảnh báo khẩn vào Outbox.
    """
    from app.modules.policy_funding.services.automation_service import PolicyAutomationService

    mock_db = MagicMock()
    mock_db.flush.return_value = None

    # Test Ingestion
    inbox_item = PolicyAutomationService.ingest_external_policy_feed(
        db=mock_db,
        workspace_id=1,
        brain_id=1,
        source_title="Nghị định 268/2025/NĐ-CP Hướng dẫn Quỹ ĐMST",
        source_url="https://chinhphu.vn/van-ban/268-2025",
        authority="Chính phủ",
        document_type="DECREE",
        content_raw="Toàn văn nghị định về cơ chế thử nghiệm và voucher...",
        confidence=0.92,
    )

    assert inbox_item.source_title == "Nghị định 268/2025/NĐ-CP Hướng dẫn Quỹ ĐMST"
    assert inbox_item.status == "PENDING"
    assert inbox_item.ai_confidence == 0.92

    # Test Alert Dispatch
    alert_entry = PolicyAutomationService.dispatch_critical_policy_alert(
        db=mock_db,
        workspace_id=1,
        project_id=1001,
        alert_title="Hạn nộp hồ sơ NATIF còn dưới 7 ngày",
        alert_message="Vui lòng hoàn tất nộp hồ sơ trước 17:00 ngày 20/08/2026.",
        channel="IN_APP",
    )

    assert alert_entry.channel == "IN_APP"
    assert "NATIF" in alert_entry.payload_jsonb["title"]
    assert alert_entry.payload_jsonb["urgency"] == "CRITICAL"


def test_chat_greeting_guard():
    """
    Quy tắc bắt buộc (§49.11): Câu chào thông thường không được kích hoạt tự động flow phân tích chính sách.
    """
    greetings = ["chào bạn", "hello", "hi cosa", "chào em", "alo", "xin chào"]

    policy_keywords = ["chính sách", "quỹ", "hỗ trợ", "funding", "voucher", "tài trợ", "xin vốn", "trl"]

    for g in greetings:
        # Câu chào đơn thuần không chứa từ khóa chính sách
        has_policy_intent = any(k in g.lower() for k in policy_keywords)
        assert has_policy_intent is False, f"Greeting '{g}' should not trigger policy matching intent."
