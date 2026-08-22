from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from db.models import Brain, WorkspaceMember
from core.snowflake import generate_snowflake_id
from business.marketing.models_validation import (
    Assumption,
    Evidence,
    KnowledgeStatement,
    EpistemicStatus,
    KnowledgeOrigin,
    ConfidenceLevel,
    AssumptionCategory,
    AssumptionStatus,
    EvidenceStrength,
    EvidenceSourceType,
)
from business.marketing.schemas.validation_schemas import (
    AssumptionCreate,
    AssumptionUpdate,
    EvidenceCreate,
    KnowledgeStatementCreate,
)
from business.marketing.services.assumption_service import AssumptionService
from business.marketing.routers.validation_router import (
    create_assumption,
    list_assumptions,
    get_assumption,
    update_assumption,
    delete_assumption,
    get_assumptions_summary,
    create_knowledge_statement,
    list_knowledge_statements,
    create_evidence,
    list_evidence,
)
from tests.marketing_fakes import FakeDb


def mock_member(ws_id: int) -> WorkspaceMember:
    m = MagicMock(spec=WorkspaceMember)
    m.user_id = generate_snowflake_id()
    m.workspace_id = ws_id
    m.role = "admin"
    return m


@pytest.fixture
def scope():
    ws_id = generate_snowflake_id()
    brain = Brain(id=generate_snowflake_id(), workspace_id=ws_id)
    return ws_id, brain, mock_member(ws_id)


# ===================================================================
# 1. Criticality Formula (§14 in E3.md: Criticality = Impact * Uncertainty)
# ===================================================================

def test_criticality_calculation():
    assert AssumptionService.calculate_criticality(impact=5, uncertainty=5) == 25
    assert AssumptionService.calculate_criticality(impact=1, uncertainty=3) == 3
    assert AssumptionService.calculate_criticality(impact=4, uncertainty=2) == 8
    # Bounds clamping (1 to 5)
    assert AssumptionService.calculate_criticality(impact=10, uncertainty=0) == 5


# ===================================================================
# 2. Epistemic Principle: AI-generated != Validated (§5, §6 in E3.md)
# ===================================================================

def test_ai_generated_statement_defaults_to_assumption(scope):
    ws_id, brain, member = scope
    db = FakeDb({Brain: [brain]})

    payload = KnowledgeStatementCreate(
        statement="Founder doanh nghiệp nhỏ quan tâm nhất đến khả năng chạy AI local.",
        origin=KnowledgeOrigin.AI_GENERATED,
        epistemic_status=EpistemicStatus.FACT,  # User/AI tried to claim FACT without evidence
        confidence=ConfidenceLevel.HIGH,
    )
    res = create_knowledge_statement(payload=payload, brain_id=brain.id, member=member, db=db)

    # Must be downgraded to ASSUMPTION and LOW confidence
    assert res.epistemic_status == EpistemicStatus.ASSUMPTION.value
    assert res.confidence == ConfidenceLevel.LOW.value
    assert res.origin == KnowledgeOrigin.AI_GENERATED.value


def test_verified_fact_with_evidence_is_allowed(scope):
    ws_id, brain, member = scope
    db = FakeDb({Brain: [brain]})

    payload = KnowledgeStatementCreate(
        statement="Landing page nhận được 127 lượt đăng ký.",
        origin=KnowledgeOrigin.ANALYTICS,
        epistemic_status=EpistemicStatus.FACT,
        confidence=ConfidenceLevel.HIGH,
        evidence_ids=["EVD-001"],
    )
    res = create_knowledge_statement(payload=payload, brain_id=brain.id, member=member, db=db)

    assert res.epistemic_status == EpistemicStatus.FACT.value
    assert res.confidence == ConfidenceLevel.HIGH.value


# ===================================================================
# 3. Assumption CRUD & Criticality Ranking (§13, §14 in E3.md)
# ===================================================================

def test_create_assumption_calculates_criticality(scope):
    ws_id, brain, member = scope
    db = FakeDb({Brain: [brain]})

    payload = AssumptionCreate(
        statement="Khách hàng sẵn sàng trả phí cho công cụ định danh số.",
        category=AssumptionCategory.PRICING,
        impact=5,
        uncertainty=4,
    )
    created = create_assumption(payload=payload, brain_id=brain.id, member=member, db=db)

    assert created.criticality == 20  # 5 * 4
    assert created.status == AssumptionStatus.UNTESTED.value
    assert created.category == AssumptionCategory.PRICING.value
    assert created.workspace_id == ws_id


def test_update_assumption_recalculates_criticality(scope):
    ws_id, brain, member = scope
    asm = Assumption(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain.id,
        statement="Test statement",
        impact=3,
        uncertainty=3,
        criticality=9,
        status="untested",
    )
    db = FakeDb({Brain: [brain], Assumption: [asm]})

    update_payload = AssumptionUpdate(impact=5, uncertainty=5)
    updated = update_assumption(assumption_id=asm.id, payload=update_payload, member=member, db=db)

    assert updated.impact == 5
    assert updated.uncertainty == 5
    assert updated.criticality == 25


def test_list_assumptions_ranks_by_criticality(scope):
    ws_id, brain, member = scope
    asm_low = Assumption(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain.id,
        statement="Button color is blue",
        impact=1,
        uncertainty=2,
        criticality=2,
        status="untested",
    )
    asm_high = Assumption(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain.id,
        statement="ICP has painful problem",
        impact=5,
        uncertainty=5,
        criticality=25,
        status="untested",
    )
    asm_mid = Assumption(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain.id,
        statement="Distribution channel X works",
        impact=4,
        uncertainty=3,
        criticality=12,
        status="testing",
    )
    db = FakeDb({Brain: [brain], Assumption: [asm_low, asm_high, asm_mid]})

    results = list_assumptions(member=member, db=db)
    assert len(results) == 3
    # Top item must be the most critical assumption
    assert results[0].criticality == 25
    assert results[1].criticality == 12
    assert results[2].criticality == 2


# ===================================================================
# 4. Evidence Updating Assumption Status (§34, §40 in E3.md)
# ===================================================================

def test_strong_evidence_supports_assumption(scope):
    ws_id, brain, member = scope
    asm = Assumption(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain.id,
        statement="Small businesses want local AI",
        impact=5,
        uncertainty=5,
        criticality=25,
        confidence=ConfidenceLevel.LOW.value,
        status=AssumptionStatus.UNTESTED.value,
        evidence_ids=[],
    )
    db = FakeDb({Brain: [brain], Assumption: [asm]})

    payload = EvidenceCreate(
        statement="18/20 interviewed founders confirmed they urgently need local AI.",
        source_type=EvidenceSourceType.CUSTOMER_INTERVIEW,
        supports_assumption_ids=[str(asm.id)],
        strength=EvidenceStrength.STRONG,
    )
    ev = create_evidence(payload=payload, brain_id=brain.id, member=member, db=db)

    assert asm.status == AssumptionStatus.SUPPORTED.value
    assert asm.confidence == ConfidenceLevel.HIGH.value
    assert asm.uncertainty == 3  # reduced uncertainty
    assert asm.criticality == 15  # 5 * 3
    assert str(ev.id) in asm.evidence_ids


def test_contradicting_evidence_marks_assumption_contradicted(scope):
    ws_id, brain, member = scope
    asm = Assumption(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain.id,
        statement="Privacy is the primary buying trigger",
        impact=4,
        uncertainty=4,
        criticality=16,
        confidence=ConfidenceLevel.LOW.value,
        status=AssumptionStatus.TESTING.value,
        evidence_ids=[],
    )
    db = FakeDb({Brain: [brain], Assumption: [asm]})

    payload = EvidenceCreate(
        statement="Only 1/15 interviewed customers cared about privacy; 14 cared about integration speed.",
        source_type=EvidenceSourceType.CUSTOMER_INTERVIEW,
        contradicts_assumption_ids=[str(asm.id)],
        strength=EvidenceStrength.STRONG,
    )
    ev = create_evidence(payload=payload, brain_id=brain.id, member=member, db=db)

    assert asm.status == AssumptionStatus.CONTRADICTED.value
    assert str(ev.id) in asm.evidence_ids


# ===================================================================
# 5. Marketing Cockpit Assumptions Summary (§46 in E3.md)
# ===================================================================

def test_assumptions_summary_metrics(scope):
    ws_id, brain, member = scope
    asm1 = Assumption(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain.id,
        statement="Assumption 1",
        impact=5,
        uncertainty=5,
        criticality=25,
        status=AssumptionStatus.UNTESTED.value,
    )
    asm2 = Assumption(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain.id,
        statement="Assumption 2",
        impact=4,
        uncertainty=4,
        criticality=16,
        status=AssumptionStatus.TESTING.value,
    )
    asm3 = Assumption(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain.id,
        statement="Assumption 3",
        impact=3,
        uncertainty=2,
        criticality=6,
        status=AssumptionStatus.SUPPORTED.value,
    )
    db = FakeDb({Brain: [brain], Assumption: [asm1, asm2, asm3]})

    summary = get_assumptions_summary(member=member, db=db)
    assert summary["total_assumptions"] == 3
    assert summary["untested_count"] == 1
    assert summary["testing_count"] == 1
    assert summary["supported_count"] == 1
    assert summary["critical_untested_count"] == 1
    assert summary["highest_criticality"] == 25
    assert len(summary["top_critical_assumptions"]) >= 1


# ===================================================================
# 6. Tenancy & Isolation Protection
# ===================================================================

def test_assumption_from_another_workspace_is_not_found(scope):
    ws_id, brain, member = scope
    other_ws_id = generate_snowflake_id()
    asm_other = Assumption(
        id=generate_snowflake_id(),
        workspace_id=other_ws_id,
        brain_id=generate_snowflake_id(),
        statement="Other ws assumption",
        impact=5,
        uncertainty=5,
        criticality=25,
        status="untested",
    )
    db = FakeDb({Brain: [brain], Assumption: [asm_other]})

    with pytest.raises(HTTPException) as exc:
        get_assumption(assumption_id=asm_other.id, member=member, db=db)
    assert exc.value.status_code == 404
