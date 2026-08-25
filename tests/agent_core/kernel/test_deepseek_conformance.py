"""Conformance test: OpenAIAgentsKernel with real DeepSeek API (Phase 7).

Verify:
1. Model client wiring (LiteLLM -> DeepSeek provider)
2. Single-turn execution with real API response
3. Checkpoint/resume with state serialization

Cost: ~2-4 real API calls (minimal tokens, short prompts).
Skip if DEEPSEEK_API_KEY not set.
"""
from __future__ import annotations

import os

import pytest

# Skip entire module if API key missing (don't break CI)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
pytestmark = pytest.mark.skipif(
    not DEEPSEEK_API_KEY,
    reason="DEEPSEEK_API_KEY not set — skipping live DeepSeek conformance",
)


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
    from agent_core.kernel.openai_agents_kernel import OpenAIAgentsKernel
    from agent_integrations.litellm.gateway import LiteLLMModelClient

    # Create model client that routes to real DeepSeek via LiteLLM
    # Note: model format must be "provider/model" for LiteLLM
    model_client = LiteLLMModelClient(model="deepseek/deepseek-chat")

    # Create kernel with real model client (not mock/fallback)
    kernel = OpenAIAgentsKernel(model_client=model_client)

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
async def test_openai_agents_kernel_checkpoint_resume_with_deepseek_kernel():
    """Test: Checkpoint and resume with kernel state serialization.

    Verify that:
    1. Kernel creates checkpoint when tool needs approval
    2. Checkpoint serializes KernelRunState correctly
    3. Resume deserializes state and continues execution

    Note: Uses mock model client (not real DeepSeek) to ensure tool calls
    are generated. The single-turn test already proves DeepSeek wiring.
    This test focuses on checkpoint/resume mechanism.
    """
    from agent_core.contracts.run import RunRequest, RunStatus
    from agent_core.contracts.spec import AgentSpec
    from agent_core.governance.contracts import ExecutionMode
    from agent_core.kernel.openai_agents_kernel import OpenAIAgentsKernel
    from agent_core.runs.repository import InMemoryRunRepository

    # Setup: in-memory repository to track checkpoints
    repo = InMemoryRunRepository()

    # Use mock model client (returns tool calls to trigger checkpoint flow)
    # This allows us to test checkpoint/resume without depending on
    # real model behavior with tool definitions
    class MockModelClientWithTools:
        @property
        def chat(self):
            return self

        @property
        def completions(self):
            return self

        async def create(self, **kwargs):
            # Mock response with a tool call to trigger approval flow
            class MockChoice:
                class Message:
                    content = "I'll help you transfer the funds."
                    tool_calls = [
                        type("obj", (object,), {
                            "id": "call_test_123",
                            "function": type("obj", (object,), {
                                "name": "finance.payout.execute",
                                "arguments": '{"amount": 100, "vendor": "Vendor A"}',
                            })(),
                        })(),
                    ]

                message = Message()

            class MockResponse:
                choices = [MockChoice()]
                usage = type("obj", (object,), {"total_tokens": 50})()

            return MockResponse()

    model_client = MockModelClientWithTools()

    # Policy evaluator that forces REQUIRE_APPROVAL for payout tools
    def policy_evaluator(tool_name: str, args: dict) -> str:
        if "payout" in tool_name.lower():
            return "REQUIRE_APPROVAL"
        return "ALLOW"

    # Create kernel with mock model client
    kernel = OpenAIAgentsKernel(
        repository=repo,
        model_client=model_client,
        policy_evaluator=policy_evaluator,
    )

    spec = AgentSpec(
        id="deepseek_conformance_test_checkpoint",
        version="1.0.0",
        instructions="Financial assistant.",
        model_policy={"model": "deepseek/deepseek-chat", "temperature": 0.0},
    ).with_hash()

    request = RunRequest(
        principal="test_conformance_suite",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "Transfer $100 to Vendor A"},
        execution_mode=ExecutionMode.AUTONOMOUS,
        workspace_id="ws_conformance_test",
        metadata={},
    )

    # First call: model returns tool call, kernel creates checkpoint
    result1 = await kernel.run(request, spec)

    # Verify checkpoint was created
    assert (
        result1.status == RunStatus.WAITING_APPROVAL
    ), f"Expected WAITING_APPROVAL, got {result1.status}: {result1.errors}"
    assert len(result1.interruptions_waits) > 0, "No interruptions/waits created"

    checkpoint_ref = result1.interruptions_waits[0].checkpoint_ref
    assert checkpoint_ref, "No checkpoint_ref in wait descriptor"

    # Verify checkpoint was saved with serialized state
    saved_checkpoint = await repo.get_checkpoint(checkpoint_ref)
    assert saved_checkpoint is not None, f"Checkpoint {checkpoint_ref} not found"
    assert saved_checkpoint.serialized_state is not None, "Checkpoint state empty"

    # Mock capability executor
    def mock_executor(tool_name: str, args: dict):
        return {"status": "executed", "tool": tool_name}

    # Create new kernel (simulating process restart) with same repository
    kernel2 = OpenAIAgentsKernel(
        repository=repo,
        model_client=model_client,
        capability_executor=mock_executor,
    )

    # Resume from checkpoint with approval
    resumed = await kernel2.resume(
        run_id=result1.run_id,
        checkpoint_ref=checkpoint_ref,
        updates={"approved": True},
    )

    # Verify resume completed or continued
    assert resumed.status in (
        RunStatus.COMPLETED,
        RunStatus.WAITING_APPROVAL,
    ), f"Resume failed: {resumed.status} - {resumed.errors}"
    assert resumed.run_id == result1.run_id, "Run ID mismatch"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_openai_agents_kernel_deepseek_model_policy_honored():
    """Test: Model policy from spec is passed to provider (DeepSeek temperature, etc).

    Verify that kernel respects model_policy settings when calling the model.
    """
    from agent_core.contracts.run import RunRequest, RunStatus
    from agent_core.contracts.spec import AgentSpec
    from agent_core.governance.contracts import ExecutionMode
    from agent_core.kernel.openai_agents_kernel import OpenAIAgentsKernel
    from agent_integrations.litellm.gateway import LiteLLMModelClient

    model_client = LiteLLMModelClient(model="deepseek/deepseek-chat")
    kernel = OpenAIAgentsKernel(model_client=model_client)

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
