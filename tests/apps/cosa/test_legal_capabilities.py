from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from apps.cosa.capabilities._advisory_envelope import wrap_advisory
from apps.cosa.capabilities.legal_read import (
    LEGAL_APPLICABILITY_ASSESS_SPEC,
    create_legal_applicability_assess_handler,
)
from apps.cosa.capabilities.legal_write import (
    LEGAL_OBLIGATION_CREATE_DRAFT_SPEC,
    create_legal_obligation_create_draft_handler,
)
from apps.cosa.capabilities.venture_profile import (
    VENTURE_PROFILE_READ_SPEC,
    VENTURE_PROFILE_PROPOSE_UPDATE_SPEC,
    create_venture_profile_read_handler,
    create_venture_profile_propose_update_handler,
)


def test_wrap_advisory_valid():
    advisory = wrap_advisory(
        layer="CURRENT_LAW",
        label="insight",
        content="Quy định TT58 áp dụng cho DN siêu nhỏ.",
        sources=[{"number": "58/2026/TT-BTC", "version": "2026"}],
        confidence=0.98,
        next_actions=["Nộp BCTC năm"],
    )
    assert advisory["layer"] == "CURRENT_LAW"
    assert advisory["label"] == "insight"
    assert advisory["confidence"] == 0.98
    assert len(advisory["sources"]) == 1
    assert advisory["next_actions"] == ["Nộp BCTC năm"]


def test_wrap_advisory_invalid_layer():
    with pytest.raises(ValueError, match="Invalid advisory layer"):
        wrap_advisory(
            layer="UNKNOWN_LAYER",  # type: ignore
            label="insight",
            content="test",
            sources=[],
        )


def test_wrap_advisory_invalid_label():
    with pytest.raises(ValueError, match="Invalid advisory label"):
        wrap_advisory(
            layer="POLICY_WATCH",
            label="unknown_label",  # type: ignore
            content="test",
            sources=[],
        )


@pytest.mark.asyncio
async def test_legal_applicability_assess_handler():
    client = AsyncMock()
    client.get.return_value = {
        "applicableObligations": [
            {
                "obligationTemplateId": "201",
                "title": "Nộp báo cáo tài chính năm theo TT58",
                "sourceRegulationNumber": "58/2026/TT-BTC",
                "sourceRegulationVersion": "2026",
                "layer": "CURRENT_LAW",
            }
        ]
    }
    handler = create_legal_applicability_assess_handler(client)

    result = await handler({"workspace_id": 1001}, context=None)
    assert "applicable_obligations" in result
    assert len(result["applicable_obligations"]) == 1
    assert result["advisory"]["layer"] == "CURRENT_LAW"
    assert result["advisory"]["label"] == "insight"


@pytest.mark.asyncio
async def test_legal_obligation_create_draft_handler():
    client = AsyncMock()
    client.post.return_value = {
        "id": "501",
        "title": "Nộp thuế môn bài",
        "source": "AI_PROPOSAL",
        "status": "OPEN",
    }
    handler = create_legal_obligation_create_draft_handler(client)

    result = await handler(
        {"workspace_id": 1001, "title": "Nộp thuế môn bài", "due_date": "2026-01-30"},
        context=None,
    )
    assert result["obligation_instance"]["id"] == "501"
    assert result["advisory"]["layer"] == "CURRENT_LAW"
    assert result["advisory"]["label"] == "proposal"


@pytest.mark.asyncio
async def test_venture_profile_handlers():
    client = AsyncMock()
    client.get.return_value = {
        "profile": {
            "id": "1",
            "workspaceId": "1001",
            "industry": "SaaS",
            "currency": "VND",
        }
    }
    client.put.return_value = {
        "id": "1",
        "workspaceId": "1001",
        "industry": "Fintech",
        "currency": "VND",
    }

    read_handler = create_venture_profile_read_handler(client)
    profile = await read_handler({"workspace_id": 1001}, context=None)
    assert profile["profile"]["industry"] == "SaaS"

    update_handler = create_venture_profile_propose_update_handler(client)
    updated = await update_handler(
        {"workspace_id": 1001, "industry": "Fintech"}, context=None
    )
    assert updated["profile"]["industry"] == "Fintech"
    assert updated["advisory"]["layer"] == "POLICY_WATCH"
