import pytest
from unittest.mock import MagicMock
from business.marketing.services.racro_retain_service import RACRORetainService
from founder_os.strategy.models import EvidenceItem
from business.sales.models import SalesLead, Contact


def test_generate_followup_playbook():
    service = RACRORetainService()

    # Nurturing stage
    p1 = service.generate_followup_playbook(stage="NURTURING", customer_name="Anh Tuấn")
    assert "Tài liệu hữu ích" in p1["subject"]
    assert p1["scheduled_after_days"] == 3

    # Inactive stage
    p2 = service.generate_followup_playbook(stage="INACTIVE", customer_name="Chị Lan")
    assert "quay trở lại" in p2["subject"]
    assert p2["scheduled_after_days"] == 30


def test_process_positive_review_to_evidence():
    service = RACRORetainService()
    mock_db = MagicMock()

    evidence, alert = service.process_customer_review(
        workspace_id=1,
        contact_id=101,
        rating=5,
        review_text="Phần mềm rất tuyệt vời, giúp đội ngũ tiết kiệm 50% thời gian!",
        customer_name="Công ty Hoàng Long",
        db=mock_db,
    )

    assert evidence is not None
    assert isinstance(evidence, EvidenceItem)
    assert evidence.reliability == "high"
    assert evidence.tags["social_proof"] is True
    assert evidence.tags["rating"] == 5
    assert alert["action"] == "PROMOTED_TO_EVIDENCE"
    assert mock_db.add.called


def test_process_negative_review_service_recovery():
    service = RACRORetainService()
    mock_db = MagicMock()

    evidence, alert = service.process_customer_review(
        workspace_id=1,
        contact_id=102,
        rating=2,
        review_text="Gặp khó khăn khi tích hợp API với hệ thống cũ",
        customer_name="Khách hàng B",
        db=mock_db,
    )

    assert evidence is None
    assert alert["action"] == "SERVICE_RECOVERY_ALERT"
    assert alert["requires_human_attention"] is True
    assert alert["rating"] == 2
    assert not mock_db.add.called


def test_create_referral_lead():
    service = RACRORetainService()
    mock_db = MagicMock()

    contact, lead = service.create_referral_lead(
        workspace_id=1,
        referrer_contact_id=101,
        referred_name="Trần Văn C",
        referred_email="vanc@partner.com",
        referred_phone="0901234567",
        company_name="TechPro VN",
        db=mock_db,
    )

    assert isinstance(contact, Contact)
    assert contact.name == "Trần Văn C"
    assert contact.source == "referral"

    assert isinstance(lead, SalesLead)
    assert lead.source == "referral"
    assert lead.qualification_status == "QUALIFIED"
    assert lead.next_action_type == "REFERRAL_OUTREACH"
    assert mock_db.add.called
