"""Contract and smoke tests for PydanticAI adapter (PydanticAIKernel).

Gated by skipif when pydantic_ai is not installed.
"""

from __future__ import annotations

import importlib.util

import pytest

if importlib.util.find_spec("pydantic_ai") is None:
    pytest.skip(
        "pydantic_ai is not installed — skipping PydanticAI contract tests", allow_module_level=True
    )

from agent_integrations.pydantic_ai.kernel import (
    PydanticAIKernel,
    _deferred_requests_from_dict,
    _deferred_requests_to_dict,
)
from pydantic_ai import DeferredToolRequests
from pydantic_ai.messages import ToolCallPart


def test_pydantic_ai_deferred_requests_roundtrip():
    """DeferredToolRequests serialization and deserialization roundtrip."""
    original = DeferredToolRequests(
        calls=[ToolCallPart(tool_name="tool_a", args={"x": 1}, tool_call_id="call_a")],
        approvals=[ToolCallPart(tool_name="tool_b", args={"y": 2}, tool_call_id="call_b")],
    )

    data = _deferred_requests_to_dict(original)
    assert len(data["calls"]) == 1
    assert len(data["approvals"]) == 1
    assert data["calls"][0]["tool_call_id"] == "call_a"

    restored = _deferred_requests_from_dict(data)
    assert len(restored.calls) == 1
    assert len(restored.approvals) == 1
    assert restored.calls[0].tool_name == "tool_a"
    assert restored.approvals[0].tool_call_id == "call_b"


@pytest.mark.asyncio
async def test_pydantic_ai_kernel_initialization():
    """PydanticAIKernel initializes with default repositories."""
    kernel = PydanticAIKernel()
    assert kernel._repo is not None
    assert kernel._spec_registry is not None
    assert kernel._cancelled_runs == set()
