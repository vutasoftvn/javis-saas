# backend/tests/agentos/evals/test_full_eval_integration.py
import pytest

from agentos.core.approval import ApprovalService
from agentos.core.model_provider import ModelResponse, StubModelProvider, ToolCallRequest
from agentos.core.models import TaskContext
from agentos.core.policy import PermissionClass, PolicyEngine
from agentos.core.runtime import AgentRuntime
from agentos.evals.agent_eval import evaluate_agent_run
from agentos.evals.business_outcome_eval import evaluate_business_outcome
from agentos.evals.workflow_eval import evaluate_workflow
from agentos.observability.trace_tree import build_trace_tree
from agentos.tools.registry import ToolRegistry, ToolSpec
from agentos.workflows.approval_step import ApprovalGateStep
from agentos.workflows.engine import WorkflowEngine
from agentos.workflows.steps import DeterministicStep


async def _echo(arguments: dict) -> dict:
    return {"echoed": arguments.get("text")}


async def _business_write(state: dict) -> dict:
    return {"crm_record_id": "crm-42"}


@pytest.mark.asyncio
async def test_agent_eval_reflects_a_real_agent_runtime_run_including_its_tool_call():
    registry = ToolRegistry()
    registry.register(ToolSpec(name="echo", description="d", handler=_echo))
    provider = StubModelProvider(
        [
            ModelResponse(tool_call=ToolCallRequest(tool_name="echo", arguments={"text": "hi"})),
            ModelResponse(text="Echoed: hi"),
        ]
    )
    runtime = AgentRuntime(provider, registry)
    task = TaskContext(goal="echo hi", agent_key="echo_agent", workspace_id="ws1")

    await runtime.run(task)

    assert runtime.last_trace is not None
    spans = runtime.last_trace.export()
    eval_result = evaluate_agent_run(runtime.last_run, spans, human_acceptance=True)

    assert eval_result.goal_completion is True
    assert eval_result.tool_calls_made == 1
    assert eval_result.human_acceptance is True

    # Executor doesn't pass parent_span_id yet (see Task 1's docstring), so
    # every span is still a top-level root — an honest, degenerate tree.
    tree = build_trace_tree(spans)
    assert len(tree) == len(spans)


@pytest.mark.asyncio
async def test_workflow_eval_reflects_a_denied_approval_end_to_end():
    approval_service = ApprovalService()
    engine = WorkflowEngine()
    gate = ApprovalGateStep(
        "human-approval",
        policy_engine=PolicyEngine(),
        approval_service=approval_service,
        permission=PermissionClass.MODIFY_BUSINESS_DATA,
        action="create_crm_record",
        subject_key="goal",
        requester="researcher",
    )
    steps = [gate, DeterministicStep("business-write", _business_write)]

    workflow = await engine.start("prospect-flow", steps, {"goal": "research Acme Corp"})
    approval_service.decide(workflow.pending_approval_id, reviewer="founder", approved=False, reason="not ready")
    resumed = await engine.resume(workflow, steps)

    eval_result = evaluate_workflow(resumed)

    assert eval_result.completed is False
    assert eval_result.failed_step_name == "human-approval"
    assert eval_result.reached_approval_gate is True


def test_business_outcome_eval_matches_the_blueprint_okr_example():
    result = evaluate_business_outcome("hit_10k_mrr", target=10000, actual=6500)

    assert result.achievement_ratio == 0.65
    assert result.achieved is False
