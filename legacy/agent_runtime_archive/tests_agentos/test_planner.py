from agentos.core.model_provider import ModelResponse, ToolCallRequest
from agentos.core.planner import PlanAction, Planner


def test_decide_call_tool_when_tool_call_present():
    planner = Planner()
    response = ModelResponse(tool_call=ToolCallRequest(tool_name="echo", arguments={}))
    assert planner.decide(response) == PlanAction.CALL_TOOL


def test_decide_finish_when_only_text_present():
    planner = Planner()
    response = ModelResponse(text="done")
    assert planner.decide(response) == PlanAction.FINISH
