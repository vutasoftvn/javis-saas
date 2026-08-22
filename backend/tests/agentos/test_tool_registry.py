import pytest

from agentos.tools.registry import ToolNotFoundError, ToolRegistry, ToolSpec


async def _echo(arguments: dict) -> dict:
    return {"echoed": arguments.get("text")}


def test_register_and_names():
    registry = ToolRegistry()
    registry.register(ToolSpec(name="echo", description="echoes text", handler=_echo))
    assert registry.names() == ["echo"]


def test_get_missing_tool_raises():
    registry = ToolRegistry()
    with pytest.raises(ToolNotFoundError):
        registry.get("missing")


@pytest.mark.asyncio
async def test_invoke_calls_handler():
    registry = ToolRegistry()
    registry.register(ToolSpec(name="echo", description="echoes text", handler=_echo))
    result = await registry.invoke("echo", {"text": "hi"})
    assert result == {"echoed": "hi"}
