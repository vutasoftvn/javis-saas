"""Nối dây trong kernel: lỗi 4xx của tool trả về model, AgentRuntimeError vẫn
ném ra, và project_id được tự điền / chặn theo scope của run."""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("agents")

from agent.capabilities.gateway import CapabilityGateway
from agent.capabilities.registry import CapabilityRegistry
from agent.contracts.capability import CapabilitySpec
from agent.contracts.errors import AgentRuntimeError, RuntimeErrorCode
from agent.governance.contracts import CapabilityRisk
from agent.runs.repository import InMemoryRunRepository
from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel
from agent_testkit.fake_sdk_model import FakeSDKModel
from fastapi import HTTPException

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


@pytest.mark.asyncio
async def test_invalid_json_args_become_error_result() -> None:
    async def never(*a: Any, **k: Any) -> Any:
        raise AssertionError("không được gọi executor khi args hỏng")

    result = await _tool({}, never).on_invoke_tool(_Ctx(), "{not json")
    assert "error" in result and "hint" in result


# --- Nối dây với CapabilityGateway THẬT (như COSA: capability_executor=gateway.execute)

GW_READ = CapabilitySpec(
    id="gw.read",
    description="read",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["q"],
        "properties": {"q": {"type": "string"}},
    },
)
GW_WRITE = CapabilitySpec(
    id="gw.write",
    description="write",
    risk=CapabilityRisk.HIGH,
    input_schema={"type": "object", "properties": {"q": {"type": "string"}}},
)
GW_CTX = {"workspace_id": "ws_test", "principal": "u1"}


def _gateway_tool(spec: CapabilitySpec, handler: Any, context: dict[str, Any] | None = None) -> Any:
    registry = CapabilityRegistry()
    registry.register(spec, handler)
    repo = InMemoryRunRepository()
    gateway = CapabilityGateway(registry=registry, repository=repo)
    kernel = RealOpenAIAgentsSDKKernel(
        repository=repo,
        capability_registry=registry,
        model=FakeSDKModel(responses=[]),
        capability_executor=gateway.execute,
    )
    return kernel._make_tool(spec, "run_gw", {**GW_CTX, **(context or {})})


@pytest.mark.asyncio
async def test_gateway_handler_http_422_becomes_error_result() -> None:
    def handler(payload: dict[str, Any], ctx: Any) -> Any:
        raise HTTPException(status_code=422, detail="unknown variables: ['query']")

    result = await _gateway_tool(GW_READ, handler).on_invoke_tool(_Ctx(), '{"q": "x"}')
    assert "unknown variables" in result["error"] and "hint" in result


@pytest.mark.asyncio
async def test_gateway_schema_validation_failure_becomes_error_result() -> None:
    tool = _gateway_tool(GW_READ, lambda p, c: {"ok": True})
    result = await tool.on_invoke_tool(_Ctx(), "{}")
    assert "'q'" in result["error"] and "hint" in result


@pytest.mark.asyncio
async def test_gateway_handler_internal_error_still_raises() -> None:
    def handler(payload: dict[str, Any], ctx: Any) -> Any:
        raise RuntimeError("db down")

    with pytest.raises(AgentRuntimeError) as ei:
        await _gateway_tool(GW_READ, handler).on_invoke_tool(_Ctx(), '{"q": "x"}')
    assert ei.value.code == RuntimeErrorCode.CAPABILITY_DENIED


@pytest.mark.asyncio
async def test_gateway_denied_still_raises() -> None:
    tool = _gateway_tool(GW_READ, lambda p, c: {"ok": True}, {"emergency_lock": True})
    with pytest.raises(AgentRuntimeError) as ei:
        await tool.on_invoke_tool(_Ctx(), '{"q": "x"}')
    assert ei.value.code == RuntimeErrorCode.CAPABILITY_DENIED
    assert ei.value.details["status"] == "denied"


@pytest.mark.asyncio
async def test_gateway_waiting_approval_still_raises() -> None:
    tool = _gateway_tool(GW_WRITE, lambda p, c: {"ok": True})
    with pytest.raises(AgentRuntimeError) as ei:
        await tool.on_invoke_tool(_Ctx(), '{"q": "x"}')
    assert ei.value.code == RuntimeErrorCode.APPROVAL_REQUIRED


# --- _needs_approval đánh giá args ĐÃ scope; project lệch không tạo approval


def _approval_tool(seen: list[dict[str, Any]]) -> Any:
    def policy(tool_name: str, args: dict[str, Any], context: dict[str, Any]) -> str:
        seen.append(dict(args))
        return "REQUIRE_APPROVAL"

    kernel = RealOpenAIAgentsSDKKernel(
        repository=InMemoryRunRepository(),
        capability_registry=CapabilityRegistry(),
        model=FakeSDKModel(responses=[]),
        policy_evaluator=policy,
    )
    return kernel._make_tool(CAP, "run_1", {"project_id": "p1"})


@pytest.mark.asyncio
async def test_needs_approval_evaluates_scoped_args() -> None:
    seen: list[dict[str, Any]] = []
    assert await _approval_tool(seen).needs_approval(None, {}, "call_1") is True
    assert seen == [{"project_id": "p1"}]


@pytest.mark.asyncio
async def test_needs_approval_skips_interrupt_for_other_project() -> None:
    seen: list[dict[str, Any]] = []
    tool = _approval_tool(seen)
    assert await tool.needs_approval(None, {"project_id": "p2"}, "call_1") is False
    assert seen == []
    # Không xin duyệt, nhưng lệnh gọi vẫn bị chặn và trả lỗi cho model.
    result = await tool.on_invoke_tool(_Ctx(), '{"project_id": "p2"}')
    assert "project_id" in result["error"]
