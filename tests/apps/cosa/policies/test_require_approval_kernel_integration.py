"""WGA G7 — metadata `require_approval_capabilities` của run đi qua kernel SDK
thật tới CosaPolicyEngine và làm run dừng WAITING_APPROVAL với approval bind
đúng tool_call_id (không chỉ unit test của policy)."""

from __future__ import annotations

import pytest

pytest.importorskip("agents")

from agent.capabilities.registry import CapabilityRegistry
from agent.contracts.capability import CapabilitySpec
from agent.contracts.run import RunRequest, RunStatus
from agent.contracts.spec import AgentSpec
from agent.governance.contracts import ExecutionMode
from agent.runs.repository import InMemoryRunRepository
from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel
from agent_testkit.fake_sdk_model import FakeSDKModel, text_response, tool_call_response

from apps.cosa.policies.evaluator import REQUIRE_APPROVAL_CAPABILITIES_KEY, CosaPolicyEngine

_CAP = "operations.task.list"


def _spec() -> AgentSpec:
    return AgentSpec(
        id="wga_needs_approval_agent",
        version="1.0.0",
        instructions="Do the work item.",
        capability_refs=[_CAP],
        model_input_capability_ref="model.input.direct-user-message",
    ).with_hash()


async def _run(metadata: dict) -> tuple:
    repo = InMemoryRunRepository()
    registry = CapabilityRegistry()
    registry.register(
        CapabilitySpec(
            id=_CAP,
            description="List tasks",
            input_schema={"type": "object", "properties": {}},
        ),
        lambda args: {},
    )
    executed: list[str] = []

    async def executor(tool_name: str, args: dict) -> dict:
        executed.append(tool_name)
        return {"tasks": []}

    kernel = RealOpenAIAgentsSDKKernel(
        repository=repo,
        capability_registry=registry,
        capability_executor=executor,
        model=FakeSDKModel(
            responses=[tool_call_response("call_1", _CAP, arguments="{}"), text_response("done")]
        ),
        policy_evaluator=CosaPolicyEngine().evaluate,
    )
    spec = _spec()
    req = RunRequest(
        input={"prompt": "List stale tasks"},
        principal="system:wga:ws1",
        root_executable_ref=spec.to_pinned_identity(),
        execution_mode=ExecutionMode.HUMAN_IN_THE_LOOP,
        workspace_id="ws1",
        metadata=metadata,
    )
    return await kernel.run(req, spec), repo, executed


@pytest.mark.asyncio
@pytest.mark.integration
async def test_marked_capability_pauses_run_for_founder_approval():
    result, repo, executed = await _run({REQUIRE_APPROVAL_CAPABILITIES_KEY: [_CAP]})
    assert result.status == RunStatus.WAITING_APPROVAL
    assert executed == []
    approval = await repo.get_approval(result.interruptions_waits[0].related_ref)
    assert approval is not None
    assert approval.tool_call_id == "call_1"
    assert approval.action == _CAP


@pytest.mark.asyncio
@pytest.mark.integration
async def test_unmarked_run_executes_without_approval():
    result, _, executed = await _run({})
    assert result.status == RunStatus.COMPLETED
    assert executed == [_CAP]
