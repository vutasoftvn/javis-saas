"""Unit & Integration Tests for Cross-cutting Quality Gate (§45, §55, §118, C1/C2 Spec).

Verifies that Quality Gates enforce quality criteria across domains:
- Finance: Runway, burn rate, accounting sanity
- Legal: Citations, mandatory legal disclaimer
- Sales: Lead identity, ICP fit, evidence presence, duplicate prevention
- Marketing: CAC, conversion rate thresholds
"""

import pytest
from workforce.agents.governance.quality_gate import (
    FinanceQualityGate,
    LegalQualityGate,
    MarketingQualityGate,
    QualityGateEvaluator,
    QualityGateVerdict,
    SalesQualityGate,
)
from workforce.agents.domains.legal.reasoning import LEGAL_DISCLAIMER


def test_finance_quality_gate_pass():
    payload = {
        "actual_runway_months": 14.0,
        "target_runway_months": 12.0,
        "net_burn_vnd": 100000000.0,
    }
    result = FinanceQualityGate.evaluate(payload)
    assert result.verdict == QualityGateVerdict.PASS
    assert result.passed is True
    assert len(result.issues) == 0


def test_finance_quality_gate_partial_caution():
    payload = {
        "actual_runway_months": 8.0,
        "target_runway_months": 12.0,
        "net_burn_vnd": 120000000.0,
    }
    result = FinanceQualityGate.evaluate(payload)
    assert result.verdict == QualityGateVerdict.PARTIAL
    assert result.passed is True


def test_finance_quality_gate_fail_zero_runway():
    payload = {
        "actual_runway_months": 0.0,
        "target_runway_months": 12.0,
        "net_burn_vnd": 150000000.0,
    }
    result = FinanceQualityGate.evaluate(payload)
    assert result.verdict == QualityGateVerdict.FAIL
    assert result.passed is False
    assert any("runway" in issue.lower() for issue in result.issues)


def test_legal_quality_gate_pass():
    payload = {
        "citations": ["Điều 12 Luật Doanh nghiệp 2020", "Nghị định 01/2021/NĐ-CP"],
        "disclaimer": LEGAL_DISCLAIMER,
        "analysis": "Review completed successfully with compliance verified.",
    }
    result = LegalQualityGate.evaluate(payload)
    assert result.verdict == QualityGateVerdict.PASS
    assert result.passed is True
    assert result.metrics.get("citations_count") == 2


def test_legal_quality_gate_fail_missing_citations():
    payload = {
        "citations": [],
        "disclaimer": LEGAL_DISCLAIMER,
    }
    result = LegalQualityGate.evaluate(payload)
    assert result.verdict == QualityGateVerdict.FAIL
    assert result.passed is False
    assert any("citation" in issue.lower() for issue in result.issues)


def test_legal_quality_gate_fail_missing_disclaimer():
    payload = {
        "citations": ["Thông tư 58/2026/TT-BTC"],
        "disclaimer": "",
    }
    result = LegalQualityGate.evaluate(payload)
    assert result.verdict == QualityGateVerdict.FAIL
    assert result.passed is False
    assert any("disclaimer" in issue.lower() for issue in result.issues)


def test_sales_quality_gate_leads_pass():
    payload = {
        "leads": [
            {
                "company": "Vuta Corporation",
                "email": "founder@vuta.vn",
                "fit_score": 0.85,
                "evidence": ["TechStack: Next.js + Postgres", "Recent hiring post on LinkedIn"],
            },
            {
                "company": "Acme SaaS",
                "email": "cto@acme.io",
                "fit_score": 0.72,
                "evidence": ["Funding round Series A in Tech in Asia"],
            },
        ]
    }
    result = SalesQualityGate.evaluate(payload)
    assert result.verdict == QualityGateVerdict.PASS
    assert result.passed is True
    assert result.metrics.get("valid_count") == 2
    assert result.metrics.get("invalid_count") == 0


def test_sales_quality_gate_leads_fail_invalid_email_and_duplicates():
    payload = {
        "leads": [
            {
                "company": "Fake Corp",
                "email": "user@fake.com",
                "fit_score": 0.9,
                "evidence": ["Website scraped"],
            },
            {
                "company": "No Evidence Co",
                "email": "valid@realcompany.com",
                "fit_score": 0.8,
                "evidence": [],
            },
            {
                "company": "Duplicate Co",
                "email": "user@fake.com",
                "fit_score": 0.8,
                "evidence": ["Article"],
            },
        ]
    }
    result = SalesQualityGate.evaluate(payload)
    assert result.verdict == QualityGateVerdict.FAIL
    assert result.passed is False
    assert result.metrics.get("invalid_count") == 3


def test_marketing_quality_gate_pass():
    payload = {
        "cac": 40.0,
        "target_cac": 60.0,
        "conversion_rate": 0.04,
    }
    result = MarketingQualityGate.evaluate(payload)
    assert result.verdict == QualityGateVerdict.PASS
    assert result.passed is True


def test_marketing_quality_gate_fail_excessive_cac():
    payload = {
        "cac": 120.0,
        "target_cac": 60.0,
        "conversion_rate": 0.005,
    }
    result = MarketingQualityGate.evaluate(payload)
    assert result.verdict == QualityGateVerdict.FAIL
    assert result.passed is False
    assert len(result.issues) >= 1


def test_quality_gate_evaluator_dispatch():
    fin_res = QualityGateEvaluator.evaluate("finance", {"actual_runway_months": 15.0})
    assert fin_res.domain == "finance"
    assert fin_res.verdict == QualityGateVerdict.PASS

    legal_res = QualityGateEvaluator.evaluate("legal", {"citations": ["Law 1"], "disclaimer": LEGAL_DISCLAIMER})
    assert legal_res.domain == "legal"
    assert legal_res.verdict == QualityGateVerdict.PASS

    unknown_res = QualityGateEvaluator.evaluate("arbitrary_domain", {})
    assert unknown_res.verdict == QualityGateVerdict.PASS
