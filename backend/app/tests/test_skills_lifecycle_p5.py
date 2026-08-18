"""Test suite for Global Skill Registry & Lifecycle in P5 (Spec §61, §62)."""

from unittest.mock import MagicMock
import pytest

from app.core.snowflake import generate_snowflake_id
from app.workforce.skills.models import SkillRegistryItem, SkillTrajectoryCandidate
from app.workforce.skills.service import SkillLifecycleService, SkillSafetyScanner


def test_skill_safety_scanner():
    """Test safety scanner catches leaked secrets and unmasked PII."""
    # 1. Leaked secret
    bad_secret_content = "Here is the key: sk-abcdef12345678901234567890123456 to access provider."
    pii_ok, secret_ok, issues = SkillSafetyScanner.scan_content(bad_secret_content)
    assert secret_ok is False
    assert len(issues) > 0

    # 2. Leaked PII
    bad_pii_content = "Contact representative at john.doe@acme-corp.com or 0912345678."
    pii_ok2, secret_ok2, issues2 = SkillSafetyScanner.scan_content(bad_pii_content)
    assert pii_ok2 is False
    assert len(issues2) > 0

    # 3. Clean content
    clean_content = "Deploy Next.js container with environment variables injected from Secret Broker."
    pii_ok3, secret_ok3, issues3 = SkillSafetyScanner.scan_content(clean_content)
    assert pii_ok3 is True
    assert secret_ok3 is True
    assert len(issues3) == 0


def test_skill_trajectory_candidate_extraction():
    """Test extracting candidate from trajectory."""
    mock_db = MagicMock()
    mock_db.add = MagicMock()
    mock_db.commit = MagicMock()
    mock_db.refresh = MagicMock()

    cand = SkillLifecycleService.create_candidate_from_trajectory(
        db=mock_db,
        workspace_id=1,
        domain="sales",
        proposed_name="prospect_enrichment",
        extracted_sop="1. Query company registry. 2. Verify domain status. 3. Extract buying signals.",
        mission_id="mis_123",
        run_id=456,
        tools_used=["crm.search_company", "web.fetch_domain"],
    )
    assert cand.domain == "sales"
    assert cand.pii_scan_passed is True
    assert cand.secret_scan_passed is True
    assert cand.status == "scanned"


def test_skill_evaluation_and_promotion_lifecycle():
    """Test candidate registration, evaluation gate, and promotion to active."""
    mock_db = MagicMock()
    
    skill_id = generate_snowflake_id()
    item = SkillRegistryItem(
        id=skill_id,
        workspace_id=1,
        name="finance.reconcile_vat",
        domain="finance",
        version="1.0.0",
        status="candidate",
        instructions="Reconcile VAT invoices against TT58 ledger records.",
    )
    mock_db.query.return_value.filter.return_value.first.return_value = item

    # 1. Evaluate with low score (< 0.70)
    item_low = SkillLifecycleService.evaluate_skill(mock_db, skill_id, eval_score=0.55)
    assert item_low.status == "evaluation"

    # 2. Evaluate with high score (>= 0.70)
    item_high = SkillLifecycleService.evaluate_skill(mock_db, skill_id, eval_score=0.88)
    assert item_high.status == "pending_approval"

    # 3. Promote by User
    item_active = SkillLifecycleService.promote_skill(mock_db, skill_id, approved_by_user_id=10)
    assert item_active.status == "active"
    assert item_active.approved_by_user_id == 10

    # 4. Record usage
    item_used = SkillLifecycleService.record_usage(mock_db, skill_id, success=True, rating=5)
    assert item_used.usage_count == 1
    assert item_used.positive_feedback == 1
    assert item_used.success_rate == 1.0


def test_skill_deprecation():
    """Test deprecating a skill."""
    mock_db = MagicMock()
    skill_id = generate_snowflake_id()
    item = SkillRegistryItem(
        id=skill_id,
        workspace_id=1,
        name="legacy.export_csv",
        domain="tech",
        status="active",
    )
    mock_db.query.return_value.filter.return_value.first.return_value = item

    deprecated = SkillLifecycleService.deprecate_skill(
        mock_db,
        skill_id,
        user_id=1,
        reason="Replaced by modern parquet streaming exporter",
    )
    assert deprecated.status == "deprecated"
    assert deprecated.rejection_reason == "Replaced by modern parquet streaming exporter"
