"""Verify `RealOpenAIAgentsSDKKernel` với model DeepSeek THẬT qua
`agents.extensions.models.litellm_model.LitellmModel` (OpenAI Agents SDK hỗ
trợ LiteLLM làm model backend chính thức) — gọi API thật, không mock.

Skip nếu thiếu `DEEPSEEK_API_KEY` — không phá CI khi không có key thật."""
from __future__ import annotations

import os

import pytest

pytest.importorskip("agents")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

pytestmark = pytest.mark.skipif(
    not DEEPSEEK_API_KEY,
    reason="DEEPSEEK_API_KEY not set — skipping live DeepSeek model call",
)


@pytest.mark.asyncio
async def test_openai_agents_sdk_kernel_with_real_deepseek_model():
    from agent.contracts.run import RunRequest, RunStatus
    from agent.contracts.spec import AgentSpec
    from agent.governance.contracts import ExecutionMode
    from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel
    from agents.extensions.models.litellm_model import LitellmModel

    model = LitellmModel(
        model="deepseek/deepseek-chat",
        base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        api_key=DEEPSEEK_API_KEY,
    )
    kernel = RealOpenAIAgentsSDKKernel(model=model)
    spec = AgentSpec(
        id="deepseek_live_test_agent",
        version="1.0.0",
        model_input_capability_ref="model.input.direct-user-message",
        instructions="Bạn là trợ lý ngắn gọn. Trả lời đúng 1 câu, không giải thích thêm.",
    ).with_hash()
    request = RunRequest(
        input={"prompt": "1 + 1 bằng mấy? Chỉ trả lời bằng số."},
        principal="test-suite",
        root_executable_ref=spec.to_pinned_identity(),
        execution_mode=ExecutionMode.AUTONOMOUS,
        workspace_id="ws_test",
    )

    result = await kernel.run(request, spec)

    assert result.status == RunStatus.COMPLETED, f"DeepSeek live call failed: {result.errors}"
    assert result.final_output
    assert "2" in str(result.final_output)
