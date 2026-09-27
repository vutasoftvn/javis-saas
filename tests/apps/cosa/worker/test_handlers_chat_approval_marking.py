"""Chat run buộc founder duyệt mọi capability T2 (spec 2026-09-27-chat-business-actions §4.1):
metadata run và context resume đều mang danh sách T2; policy engine thật siết ALLOW thành
REQUIRE_APPROVAL cho T2 và không đụng tới capability đọc."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from agent.governance.contracts import PolicyOutcome

from apps.cosa.agents.seed import seed_cosa_runtime_specs
from apps.cosa.api.event_stream import CosaEventStreamManager
from apps.cosa.capabilities.access_matrix import CHAT_T2_CAPABILITIES
from apps.cosa.policies.evaluator import REQUIRE_APPROVAL_CAPABILITIES_KEY, CosaPolicyEngine
from apps.cosa.worker.handlers import execute_resume_task, execute_run_task
from tests.apps.cosa.worker.test_handlers import (
    _failed_result,
    _payload,
    _plane,
    _seed_approved_resume,
)


@pytest.mark.asyncio
async def test_chat_run_metadata_marks_t2_capabilities_for_approval() -> None:
    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry, capability_registry=plane.capability_registry
    )
    captured: dict = {}

    async def fake_run_kernel(_plane, prep, **_kw):
        captured["metadata"] = prep.req.metadata
        return _failed_result("run_handler_test_1"), 0.0

    with patch("apps.cosa.worker.handlers.run_kernel", fake_run_kernel):
        await execute_run_task(plane, CosaEventStreamManager(), _payload())

    assert captured["metadata"][REQUIRE_APPROVAL_CAPABILITIES_KEY] == sorted(CHAT_T2_CAPABILITIES)


@pytest.mark.asyncio
async def test_resume_context_keeps_t2_approval_marking() -> None:
    plane = _plane()
    payload = await _seed_approved_resume(plane, run_id="run_resume_t2")
    plane.kernel.resume = AsyncMock(return_value=_failed_result(payload["run_id"]))

    await execute_resume_task(plane, CosaEventStreamManager(), payload)

    updates = plane.kernel.resume.await_args.kwargs["updates"]
    assert updates[REQUIRE_APPROVAL_CAPABILITIES_KEY] == sorted(CHAT_T2_CAPABILITIES)


def test_policy_engine_requires_founder_approval_for_t2_only() -> None:
    engine = CosaPolicyEngine()
    ctx = {REQUIRE_APPROVAL_CAPABILITIES_KEY: sorted(CHAT_T2_CAPABILITIES)}
    for cap in ("okr.key_result.create", "startup_os.goal.create", "operations.task.advance"):
        decision = engine.evaluate(cap, {}, ctx)
        assert decision.outcome == PolicyOutcome.REQUIRE_APPROVAL, cap
        assert decision.requirement is not None and decision.requirement.role == "founder"
    assert engine.evaluate("operations.task.list", {}, ctx).outcome == PolicyOutcome.ALLOW
    assert engine.evaluate("business.read", {}, ctx).outcome == PolicyOutcome.ALLOW
