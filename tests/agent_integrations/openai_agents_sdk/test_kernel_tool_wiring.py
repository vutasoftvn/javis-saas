"""Nối dây trong kernel: lỗi 4xx của tool trả về model, AgentRuntimeError vẫn
ném ra, và project_id được tự điền / chặn theo scope của run."""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("agents")

from agent.capabilities.registry import CapabilityRegistry
from agent.contracts.capability import CapabilitySpec
from agent.contracts.errors import AgentRuntimeError, RuntimeErrorCode
from agent.runs.repository import InMemoryRunRepository
from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel
from agent_testkit.fake_sdk_model import FakeSDKModel

CAP = CapabilitySpec(
    id="proj.read",
    description="read",
    input_schema={"type": "object", "properties": {"project_id": {"type": "string"}}},
)


class _Ctx:
    tool_call_id = "call_1"


def _tool(context: dict[str, Any], fake_exec: Any) -> Any:
    kernel = RealOpenAIAgentsSDKKernel(
        repository=InMemoryRunRepository(),
        capability_registry=CapabilityRegistry(),
        model=FakeSDKModel(responses=[]),
    )
    kernel._execute_tool = fake_exec  # type: ignore[method-assign]
    return kernel._make_tool(CAP, "run_1", context)


class _Http4xx(Exception):
    status_code = 422
    detail = "bad project_id"


@pytest.mark.asyncio
async def test_4xx_becomes_error_result() -> None:
    async def boom(*a: Any, **k: Any) -> Any:
        raise _Http4xx()

    result = await _tool({}, boom).on_invoke_tool(_Ctx(), "{}")
    assert result["error"] == "bad project_id"


@pytest.mark.asyncio
async def test_agent_runtime_error_propagates() -> None:
    async def boom(*a: Any, **k: Any) -> Any:
        raise AgentRuntimeError(RuntimeErrorCode.TENANT_UNAUTHORIZED, "denied")

    with pytest.raises(AgentRuntimeError):
        await _tool({}, boom).on_invoke_tool(_Ctx(), "{}")


@pytest.mark.asyncio
async def test_project_id_filled_and_mismatch_rejected() -> None:
    seen: dict[str, Any] = {}

    async def ok(name: str, args: dict[str, Any], **k: Any) -> Any:
        seen.update(args)
        return {"ok": True}

    tool = _tool({"project_id": "p1"}, ok)
    assert await tool.on_invoke_tool(_Ctx(), "{}") == {"ok": True}
    assert seen["project_id"] == "p1"
    result = await tool.on_invoke_tool(_Ctx(), '{"project_id": "p2"}')
    assert "project_id" in result["error"]
