from __future__ import annotations

import pytest

from apps.cosa.capabilities.engagement_message_draft import (
    ENGAGEMENT_MESSAGE_DRAFT_SPEC,
    create_engagement_message_draft_handler,
)


@pytest.mark.asyncio
async def test_engagement_message_draft_anti_bypass():
    handler = create_engagement_message_draft_handler()

    # 1. Valid draft
    res = await handler(
        {
            "thread_id": "thread-123",
            "draft_body": "Thank you for your feedback on our product.",
            "evidence_refs": ["ev-support-1"],
            "rationale": "Addressing customer feedback with verified answer",
        },
        context={"workspace_id": "ws-1"},
    )
    assert res["artifact_kind"] == "message_draft"
    assert res["delivery"] == "none"

    # 2. Attempting to send or auto-send is rejected
    with pytest.raises(ValueError, match="cannot execute external delivery or send messages"):
        await handler(
            {
                "thread_id": "thread-123",
                "draft_body": "Hello",
                "evidence_refs": ["ev-1"],
                "send": True,
            },
            context={"workspace_id": "ws-1"},
        )
