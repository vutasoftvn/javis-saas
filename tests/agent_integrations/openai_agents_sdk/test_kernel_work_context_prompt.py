from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("agents")

from agent.contracts.run import RunRequest, RunStatus
from agent.contracts.spec import AgentSpec
from agent.governance.contracts import ExecutionMode
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.repository import InMemoryRunRepository
from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel
from agent_testkit.fake_sdk_model import FakeSDKModel, text_response


class _CapturingSDKModel(FakeSDKModel):
    def __init__(self) -> None:
        super().__init__(responses=[text_response("ok")])
        self.system_instructions: list[Any] = []

    async def get_response(self, system_instructions, *args, **kwargs):
        self.system_instructions.append(system_instructions)
        return await super().get_response(system_instructions, *args, **kwargs)


@pytest.mark.asyncio
async def test_sdk_kernel_renders_goal_context_and_done_criteria_from_metadata() -> None:
    model = _CapturingSDKModel()
    kernel = RealOpenAIAgentsSDKKernel(
        repository=InMemoryRunRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        model=model,
    )
    spec = AgentSpec(
        id="analyst",
        version="1.0.0",
        instructions="Analyze data",
        model_input_capability_ref="model.input.direct-user-message",
    ).with_hash()
    request = RunRequest(
        input={"prompt": "làm task"},
        principal="user:test",
        root_executable_ref=spec.to_pinned_identity(),
        execution_mode=ExecutionMode.AUTONOMOUS,
        workspace_id="ws_wc",
        metadata={
            "goal_ancestry": {"goalChain": [{"title": "Chiến lược Q4", "goalType": "strategic"}]},
            "done_criteria": {
                "version": 1,
                "criteria": [
                    {"id": "c1", "description": "Có tài liệu", "required": True,
                     "check": "rubric", "rubric": "r"}
                ],
            },
        },
    )

    result = await kernel.run(request, spec)

    assert result.status == RunStatus.COMPLETED
    prompt = model.system_instructions[0]
    assert "Chiến lược Q4 (strategic)" in prompt
    assert "- [required] Có tài liệu" in prompt
