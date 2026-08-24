from __future__ import annotations

from typing import Any

from agent_core.contracts.capability import CapabilitySpec

__all__ = ["capability_spec_to_langchain_tool_schema"]


def capability_spec_to_langchain_tool_schema(spec: CapabilitySpec) -> dict[str, Any]:
    """Chuyển `CapabilitySpec` (agent_core) sang OpenAI function-call-style dict
    mà `BaseChatModel.bind_tools()` của LangChain chấp nhận trực tiếp (LangChain
    tự dịch sang format riêng của từng provider). Đây là adapter 1 chiều —
    CapabilitySpec vẫn là nguồn sự thật, không có business logic ở đây."""
    return {
        "type": "function",
        "function": {
            "name": spec.id,
            "description": spec.description or "",
            "parameters": spec.input_schema or {"type": "object", "properties": {}},
        },
    }
