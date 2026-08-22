"""Addendum §6.5 / §19 Phase 3 (Runtime Convergence): AgentRuntimeAdapter
formalizes the shape any execution runtime must satisfy to drive the
governed tool-calling loop for one run. Native `Executor` is the fallback/
test adapter today; a future ADK-driven production adapter must satisfy the
same contract so AgentRuntime does not need to care which one it got."""
from agentos.core.adapters.contracts import AgentRuntimeAdapter
from agentos.core.events import InMemoryEventBus
from agentos.core.executor import Executor
from agentos.core.model_provider import StubModelProvider
from agentos.core.planner import Planner
from agentos.core.trace import TraceRecorder
from agentos.tools.registry import ToolRegistry


def test_native_executor_satisfies_the_agent_runtime_adapter_contract():
    executor = Executor(
        StubModelProvider([]),
        ToolRegistry(),
        Planner(),
        TraceRecorder(run_id="run-1", event_bus=InMemoryEventBus()),
    )
    assert isinstance(executor, AgentRuntimeAdapter)
