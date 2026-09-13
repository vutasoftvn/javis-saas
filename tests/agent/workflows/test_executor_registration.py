from __future__ import annotations

import pytest

from agent.workflows.deterministic_handlers import (
    get_deterministic_handler,
    list_deterministic_handlers,
    register_deterministic_handler,
)
from agent.workflows.engine import UnsupportedWorkflowStepError, WorkflowEngine
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
    from agent.workflows.repository import InMemoryWorkflowDefinitionRepository
    from apps.cosa.composition.workflow_orchestration import WorkflowOrchestration

    class AuthorityResolver:
        async def resolve_authority(self, workspace_id: str, project_id: str, deployment_id: str):
            return {}

        async def resolve_skills(self, workspace_id: str, skill_refs: dict):
            return {}

    engine = WorkflowEngine(kernel=object(), resolver=AuthorityResolver())
    orchestration = WorkflowOrchestration(
        gateway=object(),
        workflow_engine=engine,
        workflow_registry=object(),
        approval_service=object(),
        workflow_definition_repository=InMemoryWorkflowDefinitionRepository(),
    )

    health = orchestration.get_executor_health()
    assert set(health.keys()) == {"agent", "tool_call", "approval_gate", "deterministic", "retry"}
    for k, v in health.items():
        assert v["registered"] is True
        assert v["status"] == "ready"


def test_workflow_health_degrades_when_pinned_skills_cannot_be_resolved():
    from agent.workflows.repository import InMemoryWorkflowDefinitionRepository
    from apps.cosa.composition.workflow_orchestration import WorkflowOrchestration

    class AuthorityOnlyResolver:
        async def resolve_authority(self, workspace_id: str, project_id: str, deployment_id: str):
            return {}

    orchestration = WorkflowOrchestration(
        gateway=object(),
        workflow_engine=WorkflowEngine(kernel=object(), resolver=AuthorityOnlyResolver()),
        workflow_registry=object(),
        approval_service=object(),
        workflow_definition_repository=InMemoryWorkflowDefinitionRepository(),
    )

    assert orchestration.get_executor_health()["agent"]["status"] == "degraded"


@pytest.mark.asyncio
async def test_workflow_orchestration_execute_manifest_runs_pure_steps():
    from agent.workflows.manifest import GovernedWorkflowRunManifest
    from agent.workflows.repository import InMemoryWorkflowDefinitionRepository
    from apps.cosa.composition.workflow_orchestration import WorkflowOrchestration

    engine = WorkflowEngine()
    definitions = InMemoryWorkflowDefinitionRepository()
    orchestration = WorkflowOrchestration(
        gateway=None,
        workflow_engine=engine,
        workflow_registry=None,
        approval_service=None,
        workflow_definition_repository=definitions,
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
        workflow_definition_hash=spec.compute_hash(),
    )
    await definitions.save_definition(spec, workspace_id="ws-1")

    result_wf = await orchestration.execute_manifest(
        manifest,
        initial_state={"raw_input": "hello-manifest"},
    )
    assert result_wf.status.value == "COMPLETED"
    assert result_wf.state.get("clean_input") == "hello-manifest"
    assert result_wf.state.get("_manifest") == manifest


def test_retry_step_without_a_registered_target_is_rejected():
    engine = WorkflowEngine()
    spec = WorkflowSpec(
        id="wf_retry_without_target",
        version="1.0.0",
        steps=[
            WorkflowStepSpec(
                id="step_retry",
                type=StepType.RETRY,
                inputs={"max_attempts": 2},
            )
        ],
    )

    with pytest.raises(UnsupportedWorkflowStepError, match="registered retry target"):
        engine.build_steps_from_spec(spec)


@pytest.mark.asyncio
async def test_execute_manifest_rejects_workflow_definition_hash_drift():
    from agent.workflows.manifest import GovernedWorkflowRunManifest
    from agent.workflows.repository import InMemoryWorkflowDefinitionRepository
    from apps.cosa.composition.workflow_orchestration import WorkflowOrchestration

    engine = WorkflowEngine()
    definitions = InMemoryWorkflowDefinitionRepository()
    orchestration = WorkflowOrchestration(
        gateway=None,
        workflow_engine=engine,
        workflow_registry=None,
        approval_service=None,
        workflow_definition_repository=definitions,
    )
    spec = WorkflowSpec(
        id="wf_manifest_hash_drift",
        version="1.0.0",
        steps=[
            WorkflowStepSpec(
                id="step_det",
                type=StepType.DETERMINISTIC,
                handler="pass_through",
            )
        ],
    )
    manifest = GovernedWorkflowRunManifest(
        run_id="run_manifest_hash_drift",
        project_id="proj-1",
        workspace_id="ws-1",
        workflow_asset_id=spec.id,
        workflow_version=spec.version,
        workflow_definition_hash="sha256:not-the-resolved-spec",
    )
    await definitions.save_definition(spec, workspace_id="ws-1")

    with pytest.raises(ValueError, match="definition hash"):
        await orchestration.execute_manifest(manifest)


@pytest.mark.asyncio
async def test_execute_manifest_rejects_unpersisted_caller_spec():
    from agent.workflows.manifest import GovernedWorkflowRunManifest
    from agent.workflows.repository import InMemoryWorkflowDefinitionRepository
    from apps.cosa.composition.workflow_orchestration import WorkflowOrchestration

    persisted_spec = WorkflowSpec(
        id="wf_durable_only",
        version="1.0.0",
        steps=[
            WorkflowStepSpec(
                id="step_persisted",
                type=StepType.DETERMINISTIC,
                handler="pass_through",
            )
        ],
    )
    unpersisted_spec = WorkflowSpec(
        id="wf_durable_only",
        version="1.0.0",
        steps=[
            WorkflowStepSpec(
                id="step_unpersisted",
                type=StepType.DETERMINISTIC,
                handler="pass_through",
            )
        ],
    )
    definitions = InMemoryWorkflowDefinitionRepository()
    await definitions.save_definition(persisted_spec, workspace_id="ws-1")
    orchestration = WorkflowOrchestration(
        gateway=None,
        workflow_engine=WorkflowEngine(),
        workflow_registry=None,
        approval_service=None,
        workflow_definition_repository=definitions,
    )
    manifest = GovernedWorkflowRunManifest(
        run_id="run_durable_only",
        project_id="proj-1",
        workspace_id="ws-1",
        workflow_asset_id=persisted_spec.id,
        workflow_version=persisted_spec.version,
        workflow_definition_hash=persisted_spec.compute_hash(),
    )

    with pytest.raises(ValueError, match="Caller-supplied workflow definition"):
        await orchestration.execute_manifest(manifest, spec=unpersisted_spec)
