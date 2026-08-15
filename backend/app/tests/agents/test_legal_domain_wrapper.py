import pytest
from unittest.mock import MagicMock

from app.agents.domains.legal import (
    LegalDataCapability,
    LegalReasoningCapability,
    LegalResearchCapability,
    LegalCommunicationCapability,
    LegalActionCapability,
    LegalEvaluationCapability,
    LEGAL_DISCLAIMER,
)
from app.agents.control_plane.router import DomainCapabilityRouter


def test_legal_reasoning_five_capabilities_with_citations():
    citations = ["law.vn.civil_code:art_401", "internal.policy:dpa_v1"]

    # 1. Issue Classification
    c1 = LegalReasoningCapability.issue_classification("Indemnity clause review", citations=citations)
    assert c1["status"] == "success"
    assert c1["policy_restriction"] == "L1_SUGGEST_ONLY"
    assert c1["disclaimer"] == LEGAL_DISCLAIMER

    # 2. Clause Extraction
    c2 = LegalReasoningCapability.contract_clause_extraction("Limitation of liability shall not exceed...", citations=citations)
    assert c2["status"] == "success"
    assert len(c2["extracted_clauses"]) >= 1

    # 3. Risk Summary
    c3 = LegalReasoningCapability.risk_summary({}, citations=citations)
    assert c3["status"] == "success"
    assert "identified_risks" in c3

    # 4. Checklist Draft
    c4 = LegalReasoningCapability.checklist_draft("GDPR / Decree 13 Compliance", citations=citations)
    assert c4["status"] == "success"
    assert len(c4["items"]) >= 1

    # 5. Expert Escalation Package
    c5 = LegalReasoningCapability.expert_escalation_package("Cross-border data transfer", "Context", citations=citations)
    assert c5["status"] == "success"
    assert len(c5["questions_for_counsel"]) >= 1


def test_legal_reasoning_fails_without_evidence_citations():
    with pytest.raises(ValueError, match="mandatory"):
        LegalReasoningCapability.issue_classification("Review", citations=[])

    with pytest.raises(ValueError, match="mandatory"):
        LegalReasoningCapability.contract_clause_extraction("Text", citations=None)


def test_legal_router_strictly_capped_at_l2_draft():
    # Verify no legal route is L3 or L3A
    for cap in ("data", "research", "reasoning", "communication", "action", "evaluation", "execute", "arbitrary"):
        route = DomainCapabilityRouter.resolve_route("legal", cap)
        assert route.default_policy not in ("L3_EXECUTE", "L3A_EXECUTE_WITH_APPROVAL")
        assert route.default_policy in ("L0_READ", "L1_SUGGEST", "L2_DRAFT")


def test_legal_evaluation_capability_enforces_citations_and_disclaimer():
    valid_output = {
        "citations": ["evidence_1"],
        "disclaimer": "COSA disclaimer",
    }
    eval_res = LegalEvaluationCapability.evaluate_legal_output(valid_output)
    assert eval_res["passed_validation"] is True

    invalid_output = {"data": "no citations"}
    with pytest.raises(ValueError, match="verification failed"):
        LegalEvaluationCapability.evaluate_legal_output(invalid_output)
