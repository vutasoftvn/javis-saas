"""Capability nháp theo domain: chỉ tạo bản nháp, không side-effect (G-5)."""

from __future__ import annotations

import pytest

from apps.cosa.capabilities.domain_draft import (
    DOMAIN_DRAFT_SPECS,
    DOMAIN_DRAFTS,
    create_domain_draft_handler,
    draft_capability_for_profile,
)


def test_specs_are_low_risk_drafts_without_approval():
    ids = [s.id for s in DOMAIN_DRAFT_SPECS]
    assert len(ids) == len(set(ids))
    for spec in DOMAIN_DRAFT_SPECS:
        assert spec.id.endswith(".draft")
        assert str(getattr(spec.risk, "value", spec.risk)).upper() == "LOW"


def test_profile_lookup():
    assert draft_capability_for_profile("sales") == "project.crm.lead.draft"
    assert draft_capability_for_profile("operations") is None


@pytest.mark.asyncio
async def test_handler_returns_pending_review_draft():
    handler = create_domain_draft_handler("product.decision.draft")
    out = await handler(
        {
            "title": "Chọn gói giá cho bản beta",
            "body": "Đề xuất thử 2 gói giá với 10 khách hàng đầu tiên.",
            "evidence_refs": ["interview:1", " "],
            "next_steps": ["Phỏng vấn 3 khách"],
        },
        None,
    )
    assert out["artifact_kind"] == "product_decision_draft"
    assert out["status"] == "pending_founder_review"
    assert out["delivery"] == "none"
    assert out["evidence_refs"] == ["interview:1"]
    assert out["assumptions"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("flag", ["send", "publish", "apply", "execute"])
async def test_handler_refuses_external_action_flags(flag):
    handler = create_domain_draft_handler(DOMAIN_DRAFTS[0].capability_id)
    with pytest.raises(ValueError):
        await handler({"title": "abc", "body": "0123456789", flag: True}, None)


@pytest.mark.asyncio
async def test_handler_requires_title_and_body():
    handler = create_domain_draft_handler("legal.issue.draft")
    with pytest.raises(ValueError):
        await handler({"title": "", "body": "0123456789"}, None)
    with pytest.raises(ValueError):
        await handler({"title": "abc", "body": "short"}, None)
