from __future__ import annotations

import pytest

from agentos.core.adapters.tenant_policy_client import TenantPolicyClient
from agentos.core.approval import ApprovalService
from agentos.core.executor import Executor
from agentos.core.model_provider import ModelResponse, ToolCallRequest
from agentos.core.planner import Planner
from agentos.core.policy import PermissionLevel, PolicyEngine, TenantPolicyDecision, ToolPermission, ToolRiskLevel
from agentos.core.trace import TraceRecorder
from agentos.tools.encore_client import EncoreClientError
from agentos.tools.registry import ToolRegistry, ToolSpecV2
from agentos.core.context import AgentContext
from agentos.core.models import TaskContext


class _FakeEncoreClient:
    def __init__(self, responses: dict[tuple[str, str], dict]) -> None:
        self._responses = responses
        self.calls: list[dict] = []

    async def get(self, path: str, params: dict | None = None, headers: dict | None = None) -> dict:
        self.calls.append({"path": path, "params": params})
        key = (params["companyId"], params["toolName"])
        return self._responses.get(key, {"decision": None, "matchedPattern": None, "reason": None})


class _FailingEncoreClient:
    async def get(self, path: str, params: dict | None = None, headers: dict | None = None) -> dict:
        raise EncoreClientError("network down")


@pytest.mark.asyncio
async def test_get_decision_returns_none_when_no_policy_configured():
    fake = _FakeEncoreClient({})
    client = TenantPolicyClient(encore_client=fake)

    decision = await client.get_decision(company_id="c1", tool_name="commercial.lead.create")

    assert decision is None
    assert fake.calls[0]["params"] == {"companyId": "c1", "toolName": "commercial.lead.create"}


@pytest.mark.asyncio
async def test_get_decision_returns_configured_decision():
    fake = _FakeEncoreClient(
        {("c1", "finance.transfer.funds"): {"decision": "DENY", "matchedPattern": "finance.*", "reason": "frozen"}}
    )
    client = TenantPolicyClient(encore_client=fake)

    decision = await client.get_decision(company_id="c1", tool_name="finance.transfer.funds")

    assert decision == TenantPolicyDecision.DENY


@pytest.mark.asyncio
async def test_get_decision_caches_within_ttl():
    fake = _FakeEncoreClient({("c1", "tool.x"): {"decision": "ALLOW", "matchedPattern": "*", "reason": None}})
    client = TenantPolicyClient(encore_client=fake, cache_ttl_seconds=60)

    await client.get_decision(company_id="c1", tool_name="tool.x")
    await client.get_decision(company_id="c1", tool_name="tool.x")

    assert len(fake.calls) == 1


@pytest.mark.asyncio
async def test_get_decision_fails_open_to_none_on_control_plane_error():
    client = TenantPolicyClient(encore_client=_FailingEncoreClient())

    decision = await client.get_decision(company_id="c1", tool_name="tool.x")

    assert decision is None


@pytest.mark.asyncio
async def test_executor_applies_tenant_policy_deny_from_control_plane():
    # roadmap 10a: TenantPolicy đọc thật từ control-plane phải chặn được tool call
    # dù role/risk level bình thường sẽ ALLOW.
    async def handler(args):
        return {"ok": True}

    registry = ToolRegistry()
    registry.register(
        ToolSpecV2(
            name="commercial.lead.create",
            description="Create lead",
            handler=handler,
            risk_level=ToolRiskLevel.LOW,
            tool_permission=ToolPermission.SCOPED_WRITE,
        )
    )

    fake_encore = _FakeEncoreClient(
        {("company_frozen", "commercial.lead.create"): {"decision": "DENY", "matchedPattern": "*", "reason": "company frozen"}}
    )
    tenant_policy_client = TenantPolicyClient(encore_client=fake_encore)

    class _CallToolModel:
        async def generate(self, system_prompt, messages):
            return ModelResponse(tool_call=ToolCallRequest(tool_name="commercial.lead.create", arguments={}))

    executor = Executor(
        _CallToolModel(),
        registry,
        Planner(),
        TraceRecorder(run_id="run1", correlation_id="corr1", workspace_id="ws1", company_id="company_frozen"),
        policy_engine=PolicyEngine(),
        approval_service=ApprovalService(),
        tenant_policy_client=tenant_policy_client,
        requester="tester",
    )

    task = TaskContext(
        goal="create a lead",
        agent_key="sales_agent",
        workspace_id="ws1",
        company_id="company_frozen",
        role="founder",
        agent_permission_level=PermissionLevel.L3_EXECUTE,
    )
    context = AgentContext(task=task, system_policy="policy")

    with pytest.raises(Exception) as exc_info:
        await executor.run(context)
    assert "denied" in str(exc_info.value).lower() or "ToolPermissionDeniedError" in type(exc_info.value).__name__
