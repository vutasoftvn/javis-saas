"""Contract and smoke tests for LangChain adapter (LangChainKernel & tool schema adapter).

Gated by importorskip if langchain_core / langchain is not installed.
"""

from __future__ import annotations

import importlib.util

import pytest

# Skip if langchain or langchain_core is not installed in current environment
if importlib.util.find_spec("langchain_core") is None:
    pytest.skip(
        "langchain_core is not installed — skipping LangChain contract tests",
        allow_module_level=True,
    )

from agent.contracts.capability import CapabilitySpec
from agent_integrations.langchain.kernel import LangChainKernel, LangChainKernelRunState
from agent_integrations.langchain.tool_schema_adapter import (
    capability_spec_to_langchain_tool_schema,
)
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


def test_tool_schema_adapter_conversion():
    """capability_spec_to_langchain_tool_schema correctly formats CapabilitySpec as function dict."""
    cap = CapabilitySpec(
        id="finance.balance.check",
        description="Check bank account balance",
        input_schema={
            "type": "object",
            "properties": {"account_id": {"type": "string"}},
            "required": ["account_id"],
        },
    )
    schema = capability_spec_to_langchain_tool_schema(cap)

    assert schema["type"] == "function"
    assert schema["function"]["name"] == "finance.balance.check"
    assert schema["function"]["description"] == "Check bank account balance"
    assert "account_id" in schema["function"]["parameters"]["properties"]


def test_langchain_kernel_run_state_serialization():
    """LangChainKernelRunState preserves messages across to_dict / from_dict."""
    messages = [
        SystemMessage(content="system instructions"),
        HumanMessage(content="user question"),
        AIMessage(content="assistant reply"),
    ]
    state = LangChainKernelRunState(
        run_id="run_lc_123",
        messages=messages,
        pending_tool_calls=[{"id": "c1", "name": "t1"}],
        completed_tool_calls=[],
        context={"foo": "bar"},
        step_index=2,
    )

    data = state.to_dict()
    assert data["run_id"] == "run_lc_123"
    assert data["step_index"] == 2
    assert len(data["messages"]) == 3

    restored = LangChainKernelRunState.from_dict(data)
    assert restored.run_id == "run_lc_123"
    assert restored.step_index == 2
    assert len(restored.messages) == 3
    assert isinstance(restored.messages[0], SystemMessage)
    assert isinstance(restored.messages[1], HumanMessage)
    assert isinstance(restored.messages[2], AIMessage)


@pytest.mark.asyncio
async def test_langchain_kernel_initialization():
    """LangChainKernel initializes cleanly with in-memory repositories."""
    kernel = LangChainKernel()
    assert kernel._repo is not None
    assert kernel._spec_registry is not None
    assert kernel._cancelled_runs == set()
