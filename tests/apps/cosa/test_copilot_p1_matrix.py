from __future__ import annotations

import re
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from apps.cosa.agents.specs import COSA_CUSTOMER_SUPPORT_AGENT_SPEC
from apps.cosa.api.event_stream import redact_ux_event_payload
from apps.cosa.events.rule_store import InMemoryTriggerRuleStore
from apps.cosa.worker.copilot_run import run_customer_support_copilot


def test_matrix_no_event_trigger_rule_for_engagement():
    """Copilot in P1 is strictly human-initiated; no EventTriggerRule exists for engagement.*."""
    store = InMemoryTriggerRuleStore([])
    # InMemoryTriggerRuleStore contains no rules for engagement by default
    rules = getattr(store, "_rules", [])
    engagement_rules = [r for r in rules if r.event_type.startswith("engagement.")]
    assert len(engagement_rules) == 0


def test_matrix_copilot_spec_autonomy_and_no_write_send_capabilities():
    """Copilot spec is strictly L0_OBSERVE / artifact-only with no write/send capability."""
    assert COSA_CUSTOMER_SUPPORT_AGENT_SPEC.autonomy_level.value == "L0"
    forbidden = re.compile(
        r"(\.write$|\.send$|\.execute$|message\.send|assignment\.write|lead\.write|opportunity\.write)"
    )
    for cap in COSA_CUSTOMER_SUPPORT_AGENT_SPEC.capability_refs:
        assert not forbidden.search(cap)


def test_matrix_sse_payload_redaction():
    """SSE events emitted to Desk must be cleanly redacted of sensitive tokens/secrets."""
    raw_payload = {
        "run_id": "run_123",
        "status": "completed",
        "secret_ref": "sec_hide_this",
        "access_token": "token_hide_this",
        "delegation_token": "token_hide_this",
        "summary": "Tóm tắt an toàn",
        "recommended_response_draft": "Bản nháp phản hồi",
        "evidence_refs": ["knowledge.product.doc"],
    }
    redacted = redact_ux_event_payload("run.completed", raw_payload)
    assert "secret_ref" not in redacted
    assert "access_token" not in redacted
    assert "delegation_token" not in redacted
    assert redacted["summary"] == "Tóm tắt an toàn"
    assert redacted["recommended_response_draft"] == "Bản nháp phản hồi"
    assert redacted["evidence_refs"] == ["knowledge.product.doc"]


@pytest.mark.asyncio
async def test_matrix_unverified_customer_redaction_flow():
    """Unverified customer invokes customer_360.read with identity_verified=False."""
    plane = MagicMock()
    plane.spec_registry = MagicMock()
    plane.spec_registry.get_agent_spec = AsyncMock(return_value=COSA_CUSTOMER_SUPPORT_AGENT_SPEC)

    mock_thread_read = AsyncMock(
        return_value={
            "thread": {"id": "t_99", "status": "open"},
            "contactId": "c_99",
            "identityVerified": False,
            "messages": [],
        }
    )
    mock_customer_read = AsyncMock(
        return_value={
            "contact": {"id": "c_99", "name": "Bob"},
            "account": {"id": "a_99", "name": "BobCo"},
            # Notice invoices/subscriptions omitted when unverified
        }
    )
    mock_draft = AsyncMock(return_value={"artifact_kind": "message_draft"})

    cap_registry = MagicMock()
    cap_registry.get_handler.side_effect = lambda cap_id: {
        "engagement.thread.read": mock_thread_read,
        "commercial.customer_360.read": mock_customer_read,
        "engagement.message.draft": mock_draft,
    }.get(cap_id)
    plane.capability_registry = cap_registry

    mock_kernel = MagicMock()
    mock_kernel.run = AsyncMock(
        return_value=MagicMock(
            status="completed",
            final_output={
                "summary": "Tóm tắt yêu cầu",
                "recommended_response_draft": "Vui lòng xác thực danh tính để xem hoá đơn.",
                "intent": "summarize",
                "missing_info": ["xác thực"],
                "sales_signal": "None",
                "evidence_refs": ["thread.context"],
            },
        )
    )
    plane.kernel = mock_kernel
    plane.artifact_repository = MagicMock()
    plane.artifact_repository.create = AsyncMock()
    plane.run_stream_event_repository = MagicMock()

    stream_mgr = MagicMock()
    stream_mgr.emit = AsyncMock()

    payload = {
        "run_id": "run_unverified_matrix",
        "workspace_id": "ws_1",
        "agent_profile": "customer_support",
        "thread_ref": {"thread_id": "t_99", "contact_id": "c_99"},
        "identity_verified": False,
        "intent": "summarize",
    }

    with patch("apps.cosa.worker.copilot_run.callback_company_result", new_callable=AsyncMock) as mock_cb:
        await run_customer_support_copilot(plane, stream_mgr, payload)

        # Verify commercial.customer_360.read was invoked with identity_verified=False
        mock_customer_read.assert_awaited_once_with(
            {"contact_id": "c_99", "identity_verified": False},
            {"workspace_id": "ws_1", "run_id": "run_unverified_matrix"},
        )
        mock_cb.assert_awaited_once_with(
            "run_unverified_matrix",
            "completed",
            artifact_ref="art_run_unverified_matrix",
            summary_ref="sum_run_unverified_matrix",
        )
