from __future__ import annotations

import pytest
from agent_core.governance.contracts import ApprovalPolicy, CapabilityRisk
from apps.cosa.capabilities.engagement_message_draft import (
    ENGAGEMENT_MESSAGE_DRAFT_SPEC,
    create_engagement_message_draft_handler,
)


def test_engagement_message_draft_spec_properties():
    assert ENGAGEMENT_MESSAGE_DRAFT_SPEC.id == "engagement.message.draft"
    assert ENGAGEMENT_MESSAGE_DRAFT_SPEC.risk == CapabilityRisk.LOW
    assert ENGAGEMENT_MESSAGE_DRAFT_SPEC.approval_policy == ApprovalPolicy.NEVER


@pytest.mark.asyncio
async def test_engagement_message_draft_success():
    handler = create_engagement_message_draft_handler()
    result = await handler(
        {
            "thread_id": "t_100",
            "draft_body": "Xin chào, tôi đã kiểm tra thông tin của bạn.",
            "evidence_refs": ["knowledge.product.faq", "thread.msg.1"],
            "rationale": "Phản hồi hướng dẫn kiểm tra trạng thái",
        },
        {"workspace_id": "ws_test"},
    )

    assert result["artifact_kind"] == "message_draft"
    assert result["thread_id"] == "t_100"
    assert result["draft_body"] == "Xin chào, tôi đã kiểm tra thông tin của bạn."
    assert result["evidence_refs"] == ["knowledge.product.faq", "thread.msg.1"]
    assert result["rationale"] == "Phản hồi hướng dẫn kiểm tra trạng thái"
    assert result["delivery"] == "none"


@pytest.mark.asyncio
async def test_engagement_message_draft_requires_non_empty_body():
    handler = create_engagement_message_draft_handler()
    with pytest.raises(ValueError, match="draft_body"):
        await handler(
            {"thread_id": "t_100", "draft_body": "   ", "evidence_refs": ["ref1"]},
            {"workspace_id": "ws_test"},
        )


@pytest.mark.asyncio
async def test_engagement_message_draft_requires_evidence_refs():
    handler = create_engagement_message_draft_handler()
    with pytest.raises(ValueError, match="evidence_refs"):
        await handler(
            {"thread_id": "t_100", "draft_body": "Nội dung phản hồi", "evidence_refs": []},
            {"workspace_id": "ws_test"},
        )
