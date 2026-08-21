# backend/app/tests/agents/test_adk_model_adapter.py
from unittest.mock import AsyncMock, patch

import pytest
from google.genai import types as genai_types

from app.workforce.agents.orchestration.adk.model_adapter import CosaModelGatewayLlm
from app.workforce.agents.reliability.model_gateway import ModelGatewayResult


@pytest.mark.asyncio
async def test_cosa_model_gateway_llm_maps_request_and_response():
    llm_request = genai_types_llm_request = None
    from google.adk.models.llm_request import LlmRequest

    llm_request = LlmRequest(
        model="deepseek/deepseek-reasoner",
        contents=[genai_types.Content(role="user", parts=[genai_types.Part(text="Phân tích runway")])],
        config=genai_types.GenerateContentConfig(system_instruction="Bạn là Chief of Staff."),
    )

    fake_result = ModelGatewayResult(
        content="Runway hiện tại là 12 tháng.",
        provider="deepseek",
        model="deepseek-reasoner",
        input_tokens=20,
        output_tokens=6,
        estimated_cost=0.0001,
        latency_ms=120,
        fallback_used=False,
        status="success",
    )

    llm = CosaModelGatewayLlm(model="deepseek/deepseek-reasoner", profile_name="reasoning")

    with patch(
        "app.workforce.agents.orchestration.adk.model_adapter.ModelGateway.invoke",
        new=AsyncMock(return_value=fake_result),
    ) as mock_invoke:
        responses = [resp async for resp in llm.generate_content_async(llm_request)]

    assert len(responses) == 1
    resp = responses[0]
    assert resp.content.parts[0].text == "Runway hiện tại là 12 tháng."
    assert resp.finish_reason is not None

    call_kwargs = mock_invoke.call_args.kwargs
    sent_request = call_kwargs["request"]
    assert sent_request.system_instruction == "Bạn là Chief of Staff."
    assert sent_request.messages[0].role == "user"
    assert sent_request.messages[0].content == "Phân tích runway"
    assert call_kwargs["profile_name"] == "reasoning"
    assert call_kwargs["invoker_fn"] is not None
