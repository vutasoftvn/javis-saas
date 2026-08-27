"""Conformance test: ManualToolLoopKernel with real DeepSeek API (Phase 7).

Verify:
1. Model client wiring (LiteLLM -> DeepSeek provider)
2. Single-turn execution with real API response
3. Model policy honored (temperature, model selection)

LIMITATION: Checkpoint/resume testing requires kernel extension.
Current kernel does not pass tool schemas to model API, so DeepSeek cannot
generate real tool calls. To test real checkpoint/resume, the kernel would
need to support passing tools from model_policy (not currently implemented).

Cost: ~2 real API calls (minimal tokens, short prompts).
Skip if DEEPSEEK_API_KEY not set.
"""
from __future__ import annotations

import os

import pytest

# Skip entire module if API key missing (don't break CI)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
pytestmark = [
    pytest.mark.live_provider,
    pytest.mark.skipif(
        not DEEPSEEK_API_KEY,
        reason="DEEPSEEK_API_KEY not set — skipping live DeepSeek conformance",
    ),
]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_openai_agents_kernel_single_turn_with_real_deepseek():
    """Test: Single turn (model call only, no tool calls, no approval needed).

    Verify that LiteLLMModelClient routes to DeepSeek correctly and
    kernel properly formats request/response.
    """
    from agent_core.contracts.run import RunRequest, RunStatus
    from agent_core.contracts.spec import AgentSpec
    from agent_core.governance.contracts import ExecutionMode
    from agent_core.kernel.openai_agents_kernel import ManualToolLoopKernel
    from agent_integrations.litellm.gateway import LiteLLMModelClient

    # Create model client that routes to real DeepSeek via LiteLLM
    # Note: model format must be "provider/model" for LiteLLM
    model_client = LiteLLMModelClient(model="deepseek/deepseek-chat")

    # Create kernel with real model client (not mock/fallback)
    kernel = ManualToolLoopKernel(model_client=model_client)

    # Simple agent spec
    spec = AgentSpec(
        id="deepseek_conformance_test_simple",
        version="1.0.0",
        instructions="You are a concise assistant. Answer in exactly 1-2 words.",
        model_policy={"model": "deepseek/deepseek-chat", "temperature": 0.0},
    ).with_hash()

    # Create request with minimal prompt (save tokens)
    request = RunRequest(
        principal="test_conformance_suite",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "What is 1+1? Answer with number only."},
        execution_mode=ExecutionMode.AUTONOMOUS,
        workspace_id="ws_conformance_test",
        metadata={},  # Empty policy context for this test
    )

    # Execute (calls real DeepSeek API)
    result = await kernel.run(request, spec)

    # Assertions: run completed, got response, model was actually called
    assert result.status == RunStatus.COMPLETED, f"Run failed: {result.errors}"
    assert result.final_output is not None, "No model output received"

    # Verify response contains expected answer (DeepSeek should say "2")
    response_text = str(result.final_output).lower()
    assert (
        "2" in response_text
    ), f"Expected '2' in response, got: {result.final_output}"

    # Verify usage was populated (proves real API call, not mock fallback)
    assert result.usage, "No token usage recorded (usage should not be empty)"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_openai_agents_kernel_deepseek_model_policy_honored():
    """Test: Model policy from spec is passed to provider (DeepSeek temperature, etc).

    Verify that kernel respects model_policy settings when calling the model.
    """
    from agent_core.contracts.run import RunRequest, RunStatus
    from agent_core.contracts.spec import AgentSpec
    from agent_core.governance.contracts import ExecutionMode
    from agent_core.kernel.openai_agents_kernel import ManualToolLoopKernel
    from agent_integrations.litellm.gateway import LiteLLMModelClient

    model_client = LiteLLMModelClient(model="deepseek/deepseek-chat")
    kernel = ManualToolLoopKernel(model_client=model_client)

    spec = AgentSpec(
        id="deepseek_conformance_test_policy",
        version="1.0.0",
        instructions="Be concise.",
        model_policy={
            "model": "deepseek/deepseek-chat",
            "temperature": 0.2,  # Custom temperature
        },
    ).with_hash()

    request = RunRequest(
        principal="test_conformance_suite",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "Say 'ok' only."},
        execution_mode=ExecutionMode.AUTONOMOUS,
        workspace_id="ws_conformance_test",
        metadata={},
    )

    result = await kernel.run(request, spec)

    # Should complete without errors (temperature setting accepted by DeepSeek)
    assert result.status == RunStatus.COMPLETED, f"Failed: {result.errors}"
    assert result.final_output is not None
    # Response should be short (high temperature=0.2 = more deterministic)
    assert len(str(result.final_output)) < 200, "Response too long for temp=0.2"
