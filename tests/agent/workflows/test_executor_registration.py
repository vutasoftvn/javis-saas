from __future__ import annotations

import pytest

from agent.workflows.deterministic_handlers import (
    get_deterministic_handler,
    list_deterministic_handlers,
    register_deterministic_handler,
)
from agent.workflows.engine import UnsupportedWorkflowStepError, WorkflowEngine
from agent.workflows.models import StepOutcome, StepStatus
from agent.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec


@pytest.mark.asyncio
async def test_all_v1_step_types_are_registered_in_engine():
    engine = WorkflowEngine()

    spec = WorkflowSpec(
        id="wf_all_v1",
        version="1.0.0",
        steps=[
            WorkflowStepSpec(
                id="step_det",
                type=StepType.DETERMINISTIC,
                handler="pass_through",
            ),
            WorkflowStepSpec(
                id="step_retry",
                type=StepType.RETRY,
                inputs={"max_attempts": 3, "handler": "pass_through"},
            ),
            WorkflowStepSpec(
                id="step_agent",
                type=StepType.AGENT,
                project_agent_deployment_id="dep-1",
            ),
        ],
    )

    compiled = engine.build_steps_from_spec(spec)
    assert len(compiled) == 3
    assert compiled[0].name == "step_det"
    assert compiled[1].name == "step_retry"
    assert compiled[2].name == "step_agent"


@pytest.mark.asyncio
async def test_deterministic_handler_registry_allows_custom_pure_function():
    def custom_uppercase(state: dict, params: dict | None = None) -> dict:
        text = state.get("text", "")
        return {"upper_text": text.upper()}

    register_deterministic_handler("custom_upper", custom_uppercase)
    assert get_deterministic_handler("custom_upper") is not None
    assert "custom_upper" in list_deterministic_handlers()

    engine = WorkflowEngine(registered_handlers={"custom_upper": custom_uppercase})
    spec = WorkflowSpec(
        id="wf_custom_det",
        version="1.0.0",
        steps=[
            WorkflowStepSpec(
                id="step_upper",
                type=StepType.DETERMINISTIC,
                handler="custom_upper",
            )
        ],
    )
    result_wf = await engine.execute_spec(spec, initial_state={"text": "hello world"})
    assert result_wf.status.value == "COMPLETED"
    assert result_wf.state.get("upper_text") == "HELLO WORLD"


@pytest.mark.asyncio
async def test_unknown_deterministic_handler_raises_error():
    engine = WorkflowEngine()
    spec = WorkflowSpec(
        id="wf_unknown_handler",
        version="1.0.0",
        steps=[
            WorkflowStepSpec(
                id="step_bad",
                type=StepType.DETERMINISTIC,
                handler="completely_unknown_fn_xyz",
            )
        ],
    )
    with pytest.raises(UnsupportedWorkflowStepError, match="no registered handler"):
        engine.build_steps_from_spec(spec)


@pytest.mark.asyncio
async def test_workflow_orchestration_reports_executor_health():
    from apps.cosa.composition.workflow_orchestration import WorkflowOrchestration

    engine = WorkflowEngine(kernel=object())
    orchestration = WorkflowOrchestration(
        gateway=object(),
        workflow_engine=engine,
        workflow_registry=object(),
        approval_service=object(),
    )

    health = orchestration.get_executor_health()
    assert set(health.keys()) == {"agent", "tool_call", "approval_gate", "deterministic", "retry"}
    for k, v in health.items():
        assert v["registered"] is True
        assert v["status"] == "ready"


@pytest.mark.asyncio
async def test_workflow_orchestration_execute_manifest_runs_pure_steps():
    from agent.workflows.manifest import GovernedWorkflowRunManifest
    from apps.cosa.composition.workflow_orchestration import WorkflowOrchestration

    engine = WorkflowEngine()
    orchestration = WorkflowOrchestration(
        gateway=None,
        workflow_engine=engine,
        workflow_registry=None,
        approval_service=None,
    )

    spec = WorkflowSpec(
        id="wf_manifest_test",
        version="1.0.0",
        steps=[
            WorkflowStepSpec(
                id="step_det",
                type=StepType.DETERMINISTIC,
                handler="pass_through",
                params={"source_key": "raw_input", "output_key": "clean_input"},
            ),
            WorkflowStepSpec(
                id="step_retry",
                type=StepType.RETRY,
                inputs={"max_attempts": 2, "handler": "pass_through"},
                depends_on=["step_det"],
            ),
        ],
    )

    manifest = GovernedWorkflowRunManifest(
        run_id="run_test_001",
        project_id="proj-1",
        workspace_id="ws-1",
        workflow_asset_id="wf_manifest_test",
        workflow_version="1.0.0",
        workflow_definition_hash="sha256:dummy",
    )

    result_wf = await orchestration.execute_manifest(
        manifest,
        spec=spec,
        initial_state={"raw_input": "hello-manifest"},
    )
    assert result_wf.status.value == "COMPLETED"
    assert result_wf.state.get("clean_input") == "hello-manifest"
    assert result_wf.state.get("_manifest") == manifest
