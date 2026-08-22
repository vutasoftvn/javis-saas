from __future__ import annotations

from agentos.core.context import AgentContext
from agentos.core.events import EVENT_TOOL_CALL_COMPLETED, EVENT_TOOL_CALL_STARTED
from agentos.core.model_provider import ModelProvider
from agentos.core.planner import PlanAction, Planner
from agentos.core.trace import TraceRecorder
from agentos.tools.registry import ToolRegistry

MAX_TOOL_ROUNDS = 5


class ExecutorExhaustedError(Exception):
    def __init__(self, max_rounds: int) -> None:
        super().__init__(f"Executor exceeded MAX_TOOL_ROUNDS={max_rounds} without finishing")


class Executor:
    def __init__(
        self,
        model_provider: ModelProvider,
        tool_registry: ToolRegistry,
        planner: Planner,
        trace: TraceRecorder,
    ) -> None:
        self._model_provider = model_provider
        self._tool_registry = tool_registry
        self._planner = planner
        self._trace = trace

    async def run(self, context: AgentContext) -> tuple[str, int]:
        messages: list[dict] = [{"role": "user", "content": context.task.goal}]
        tool_calls_made = 0

        for _ in range(MAX_TOOL_ROUNDS):
            response = await self._model_provider.generate(
                system_prompt=context.system_policy, messages=messages
            )
            action = self._planner.decide(response)

            if action is PlanAction.FINISH:
                return response.text or "", tool_calls_made

            assert response.tool_call is not None
            self._trace.record(
                EVENT_TOOL_CALL_STARTED,
                tool_name=response.tool_call.tool_name,
                arguments=response.tool_call.arguments,
            )
            result = await self._tool_registry.invoke(
                response.tool_call.tool_name, response.tool_call.arguments
            )
            self._trace.record(
                EVENT_TOOL_CALL_COMPLETED,
                tool_name=response.tool_call.tool_name,
                result=result,
            )
            tool_calls_made += 1
            messages.append({"role": "assistant", "tool_call": response.tool_call.model_dump()})
            messages.append({"role": "tool", "content": result})

        raise ExecutorExhaustedError(MAX_TOOL_ROUNDS)
