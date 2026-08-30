from __future__ import annotations

import pytest

from agent.capabilities.enablements import (
    CapabilityEnablement,
    InMemoryEnablementStore,
    assert_enabled_for_invocation,
)


@pytest.mark.asyncio
async def test_growth_scale_holdouts_fail_closed():
    store = InMemoryEnablementStore()

    # 1. Negative holdout: attempting to invoke B action with empty hash fails
    is_ok, reason = await assert_enabled_for_invocation(
        enablement_store=store,
        workspace_id="ws-1",
        capability_id="operations.task.create_draft",
        skill_hash="",
        action_class="B",
    )
    assert not is_ok
    assert "requires exact skill definition_hash" in reason

    # 2. Negative holdout: attempting to invoke B action without workspace_id fails
    is_ok, reason = await assert_enabled_for_invocation(
        enablement_store=store,
        workspace_id="",
        capability_id="operations.task.create_draft",
        skill_hash="hash_123",
        action_class="B",
    )
    assert not is_ok
    assert "requires workspace_id" in reason

    # 3. Negative holdout: attempting to invoke X action with unapproved enablement fails
    is_ok, reason = await assert_enabled_for_invocation(
        enablement_store=store,
        workspace_id="ws-1",
        capability_id="engagement.message.send",
        skill_hash="hash_msg",
        action_class="X",
    )
    assert not is_ok
    assert "No enablement record found" in reason
