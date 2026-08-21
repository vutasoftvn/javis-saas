# backend/app/tests/agents/test_adk_synthesis_node.py
from types import SimpleNamespace

import pytest
from google.adk.models.llm_response import LlmResponse
from google.genai import types as genai_types

from app.workforce.agents.orchestration.adk.nodes import synthesis_node as node_module


async def _fake_generate(self, llm_request, stream: bool = False):
    yield LlmResponse(
        content=genai_types.Content(role="model", parts=[genai_types.Part(text='{"diagnosis": "Runway ổn định 12 tháng."}')]),
        finish_reason=genai_types.FinishReason.STOP,
    )


@pytest.mark.asyncio
async def test_synthesis_fn_parses_structured_diagnosis(monkeypatch):
    monkeypatch.setattr(node_module.CosaModelGatewayLlm, "generate_content_async", _fake_generate)

    ctx = SimpleNamespace(state={
        "goal": "Đánh giá runway",
        "specialist_reports": {"finance": {"status": "success", "runway_months": 12}},
    })
    result = await node_module.synthesis_fn(ctx)

    assert result["status"] == "completed"
    assert ctx.state["diagnosis"] == "Runway ổn định 12 tháng."
    assert ctx.state["synthesis_status"] == "completed"


def test_build_synthesis_node_shape():
    node = node_module.build_synthesis_node()
    assert node.name == "synthesis_node"
