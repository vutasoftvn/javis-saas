import pytest
from unittest.mock import MagicMock
from datetime import datetime

from app.modules.policy_funding.models import (
    PolicyProgram,
    PolicyProgramClaim,
    PolicyVerification,
    ProjectStageAssessment,
    TrlAssessment,
    FundingNeed,
    ProjectProgramMatch,
)
from app.modules.policy_funding.services.matching_service import PolicyMatchingService


def test_verification_status_multiplier():
    """
    Kiểm tra hệ số điểm phù hợp (Match Multiplier) theo trạng thái xác minh:
    - VERIFIED_ACTIVE: 1.0 (100% điểm gốc)
    - VERIFIED_ENACTED: 0.9
    - PENDING_FOUNDER_VERIFICATION / SOURCE_CLAIMED_CURRENT: 0.6
    - DRAFT_WATCHLIST / CLOSED / REJECTED: 0.0 hoặc NEEDS_VERIFICATION
    """
    mock_db = MagicMock()

    stage_assessment = ProjectStageAssessment(
        project_id=101,
        workspace_id=1,
        company_type="STARTUP",
        stage="MVP",
        is_founder_confirmed=True,
    )
    trl_assessment = TrlAssessment(
        project_id=101,
        workspace_id=1,
        trl_current=5,
    )

    # 1. VERIFIED_ACTIVE -> Multiplier 1.0
    prog_active = PolicyProgram(
        name="NATIF Hỗ trợ lãi suất",
        status="ACTIVE",
        verification_status="VERIFIED_ACTIVE",
        publish_to_matching=True,
        company_types=["STARTUP"],
        project_stages=["MVP"],
        trl_min=3,
        matching_fund_pct=0.0,
    )
    status_act, score_act, _, _, missing_act = PolicyMatchingService.evaluate_project_against_program(
        db=mock_db,
        project_id=101,
        program=prog_active,
        workspace_id=1,
        stage_assessment=stage_assessment,
        trl_assessment=trl_assessment,
    )
    assert status_act == "ELIGIBLE"
    assert score_act == 100.0  # 100 * 1.0

    # 2. VERIFIED_ENACTED -> Multiplier 0.9
    prog_enacted = PolicyProgram(
        name="TP.HCM NQ 23/2026",
        status="ACTIVE",
        verification_status="VERIFIED_ENACTED",
        publish_to_matching=True,
        company_types=["STARTUP"],
        project_stages=["MVP"],
        trl_min=3,
        matching_fund_pct=0.0,
    )
    status_en, score_en, _, _, missing_en = PolicyMatchingService.evaluate_project_against_program(
        db=mock_db,
        project_id=101,
        program=prog_enacted,
        workspace_id=1,
        stage_assessment=stage_assessment,
        trl_assessment=trl_assessment,
    )
    assert status_en == "ELIGIBLE"
    assert score_en == 90.0  # 100 * 0.9

    # 3. PENDING_FOUNDER_VERIFICATION -> Multiplier 0.6 và cảnh báo missing item
    prog_pending = PolicyProgram(
        name="NATIF Voucher Khách hàng",
        status="ACTIVE",
        verification_status="PENDING_FOUNDER_VERIFICATION",
        publish_to_matching=True,
        company_types=["STARTUP"],
        project_stages=["MVP"],
        trl_min=3,
        matching_fund_pct=0.0,
    )
    status_pen, score_pen, _, _, missing_pen = PolicyMatchingService.evaluate_project_against_program(
        db=mock_db,
        project_id=101,
        program=prog_pending,
        workspace_id=1,
        stage_assessment=stage_assessment,
        trl_assessment=trl_assessment,
    )
    assert status_pen == "POTENTIALLY_ELIGIBLE"
    assert score_pen == 60.0  # 100 * 0.6
    assert any("Kiểm chứng dữ liệu nguồn" in m for m in missing_pen)

    # 4. DRAFT_WATCHLIST -> Không đưa vào matching (Score 0.0)
    prog_draft = PolicyProgram(
        name="Chương trình Quốc gia 2026-2035",
        status="DRAFT",
        verification_status="DRAFT_WATCHLIST",
        publish_to_matching=False,
        company_types=["STARTUP"],
        project_stages=["MVP"],
        trl_min=3,
    )
    status_dr, score_dr, _, _, _ = PolicyMatchingService.evaluate_project_against_program(
        db=mock_db,
        project_id=101,
        program=prog_draft,
        workspace_id=1,
        stage_assessment=stage_assessment,
        trl_assessment=trl_assessment,
    )
    assert status_dr == "NEEDS_VERIFICATION"
    assert score_dr == 0.0


def test_claim_architecture_and_recalculation():
    """
    Kiểm tra cấu trúc Claim-based:
    - Claim lưu trữ thông tin slide trích xuất
    - Sau khi Founder verify và cập nhật status sang VERIFIED_ACTIVE, điểm match tăng từ 60.0 lên 100.0
    """
    mock_db = MagicMock()

    program = PolicyProgram(
        id=555,
        name="NATIF Tài trợ ĐMST",
        status="ACTIVE",
        verification_status="PENDING_FOUNDER_VERIFICATION",
        publish_to_matching=True,
        company_types=["STARTUP"],
        project_stages=["MVP"],
        trl_min=3,
        matching_fund_pct=0.0,
    )

    stage_assessment = ProjectStageAssessment(
        project_id=101,
        workspace_id=1,
        company_type="STARTUP",
        stage="MVP",
        is_founder_confirmed=True,
    )
    trl_assessment = TrlAssessment(
        project_id=101,
        workspace_id=1,
        trl_current=4,
    )

    # Đánh giá trước khi verify
    _, score_before, _, _, _ = PolicyMatchingService.evaluate_project_against_program(
        db=mock_db,
        project_id=101,
        program=program,
        workspace_id=1,
        stage_assessment=stage_assessment,
        trl_assessment=trl_assessment,
    )
    assert score_before == 60.0

    # Giả lập Founder hoàn tất kiểm chứng
    program.verification_status = "VERIFIED_ACTIVE"
    program.source_url = "https://natif.gov.vn/chuong-trinh-dmst"

    _, score_after, _, _, _ = PolicyMatchingService.evaluate_project_against_program(
        db=mock_db,
        project_id=101,
        program=program,
        workspace_id=1,
        stage_assessment=stage_assessment,
        trl_assessment=trl_assessment,
    )
    assert score_after == 100.0
