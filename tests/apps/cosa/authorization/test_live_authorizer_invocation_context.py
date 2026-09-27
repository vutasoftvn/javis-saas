"""Kernel SDK truyền InvocationContext (không phải dict) vào gateway: LiveAuthorizer phải đọc
member id/workspace từ `.metadata`, nếu không mọi capability ghi đều fail closed."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from agent.contracts.capability import CapabilitySpec
from agent.contracts.invocation import InvocationContext

from apps.cosa.authorization.live_authorizer import LiveAuthorizationAuthorizer

SPEC = CapabilitySpec(id="okr.key_result.create", description="x")


def _req(metadata: dict) -> SimpleNamespace:
    ctx = InvocationContext(
        run_id="run_1",
        tool_call_id="call_1",
        checkpoint_ref="ckpt_1",
        workspace_id="ws_1",
        principal="user:1",
        metadata=metadata,
    )
    return SimpleNamespace(
        context=ctx,
        workspace_id="ws_1",
        run_id="run_1",
        tool_call_id="call_1",
        checkpoint_ref="ckpt_1",
        capability_id=SPEC.id,
        principal="user:1",
    )


@pytest.mark.asyncio
async def test_reads_agent_member_from_invocation_context_metadata() -> None:
    client = AsyncMock()
    client.post.return_value = {"ticketId": "tkt_1", "authorizationEpoch": 3}
    res = await LiveAuthorizationAuthorizer(company_client=client).authorize(
        _req({"agent_workforce_member_id": "wm_7"}), SPEC
    )
    assert res.allowed and res.ticket_id == "tkt_1"
    assert client.post.await_args.kwargs["json"]["agentWorkforceMemberId"] == "wm_7"


@pytest.mark.asyncio
async def test_still_fails_closed_without_member_id() -> None:
    client = AsyncMock()
    res = await LiveAuthorizationAuthorizer(company_client=client).authorize(_req({}), SPEC)
    assert res.allowed is False
    client.post.assert_not_awaited()


def test_draft_flag_in_invocation_metadata_skips_ticket() -> None:
    authorizer = LiveAuthorizationAuthorizer()
    assert authorizer.is_ticket_required(SPEC, _req({}).context, SPEC.id) is True
    assert authorizer.is_ticket_required(SPEC, _req({"draft_only": True}).context, SPEC.id) is False


def test_ticket_requirement_follows_access_matrix() -> None:
    authorizer = LiveAuthorizationAuthorizer()

    def required(cap_id: str) -> bool:
        return authorizer.is_ticket_required(CapabilitySpec(id=cap_id, description="x"), {}, cap_id)

    # T0 đọc, kể cả hậu tố lạ, không cần ticket.
    assert not required("startup_os.goal.tree_read")
    assert not required("web.search")
    assert not required("business.read")
    # T1 nháp không gọi company: không side-effect.
    assert not required("strategy.plan.draft")
    # Ghi qua company (T1 có AGENT_CAP, T2, T3) luôn cần ticket.
    assert required("operations.task.create_draft")
    assert required("okr.key_result.create")
    assert required("engagement.message.send")
