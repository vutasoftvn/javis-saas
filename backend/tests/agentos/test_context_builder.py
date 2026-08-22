from agentos.core.context_builder import ContextBuilder, DEFAULT_SYSTEM_POLICY
from agentos.core.models import TaskContext
from agentos.tools.registry import ToolRegistry, ToolSpec


async def _noop(arguments: dict) -> dict:
    return {}


def test_build_includes_registered_tool_names_and_default_policy():
    registry = ToolRegistry()
    registry.register(ToolSpec(name="echo", description="d", handler=_noop))
    builder = ContextBuilder(registry)
    task = TaskContext(goal="say hi", agent_key="fake", workspace_id="ws1")

    context = builder.build(task)

    assert context.task == task
    assert context.tool_names == ["echo"]
    assert context.system_policy == DEFAULT_SYSTEM_POLICY
