from __future__ import annotations

import pytest

from agent_core.governance.contracts import AutonomyLevel, CapabilityRisk
from agent_core.workflows.definition_registry import (
    WorkflowDefinitionNotFoundError,
    WorkflowDefinitionRegistry,
    WorkflowVersionNotFoundError,
)
from agent_core.workflows.engine import WorkflowEngine
from agent_core.workflows.models import WorkflowStatus
from agent_core.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec
from agent_core.workflows.steps import DeterministicStep


async def _write_v1(state: dict) -> dict:
    return {"record_id": "rec-v1"}


async def _write_v2(state: dict) -> dict:
    return {"record_id": "rec-v2", "extra_step_ran": True}


async def _notify(state: dict) -> dict:
    return {"notified": True}


def _spec_v1() -> WorkflowSpec:
    return WorkflowSpec(id="send-flow", steps=[WorkflowStepSpec(id="write", type=StepType.DETERMINISTIC)])


def _spec_v2() -> WorkflowSpec:
    return WorkflowSpec(
        id="send-flow",
        steps=[
            WorkflowStepSpec(id="write", type=StepType.DETERMINISTIC),
            WorkflowStepSpec(id="notify", type=StepType.DETERMINISTIC),
        ],
    )


_BUILDERS_V1 = {"write": lambda step_spec: DeterministicStep(step_spec.id, _write_v1)}
_BUILDERS_V2 = {
    "write": lambda step_spec: DeterministicStep(step_spec.id, _write_v2),
    "notify": lambda step_spec: DeterministicStep(step_spec.id, _notify),
}


def test_register_version_assigns_sequential_version_numbers():
    registry = WorkflowDefinitionRegistry()

    v1 = registry.register_version(_spec_v1())
    v2 = registry.register_version(_spec_v2())

    assert v1.version_no == 1
    assert v2.version_no == 2
    assert v1.id != v2.id


def test_register_version_computes_a_content_addressed_definition_hash():
    registry = WorkflowDefinitionRegistry()

    v1 = registry.register_version(_spec_v1())
    v1_repeat = registry.register_version(_spec_v1())
    v2 = registry.register_version(_spec_v2())

    assert v1.definition_hash == v1_repeat.definition_hash
    assert v1.definition_hash != v2.definition_hash


def test_current_version_returns_the_most_recently_registered_version():
    registry = WorkflowDefinitionRegistry()
    registry.register_version(_spec_v1())
    v2 = registry.register_version(_spec_v2())

    assert registry.current_version("send-flow") == v2


def test_current_version_raises_when_name_never_registered():
    registry = WorkflowDefinitionRegistry()
    with pytest.raises(WorkflowDefinitionNotFoundError):
        registry.current_version("unknown-flow")


def test_get_version_returns_an_older_immutable_version():
    registry = WorkflowDefinitionRegistry()
    v1 = registry.register_version(_spec_v1())
    registry.register_version(_spec_v2())

    assert registry.get_version("send-flow", 1) == v1


def test_get_version_raises_for_unknown_version_number():
    registry = WorkflowDefinitionRegistry()
    registry.register_version(_spec_v1())

    with pytest.raises(WorkflowVersionNotFoundError):
        registry.get_version("send-flow", 99)


def test_history_returns_every_registered_version_in_order():
    registry = WorkflowDefinitionRegistry()
    v1 = registry.register_version(_spec_v1())
    v2 = registry.register_version(_spec_v2())

    assert registry.history("send-flow") == [v1, v2]


def test_registering_a_new_version_does_not_mutate_the_previous_one():
    registry = WorkflowDefinitionRegistry()
    v1 = registry.register_version(_spec_v1())
    registry.register_version(_spec_v2())

    assert registry.get_version("send-flow", 1) == v1
    assert registry.get_version("send-flow", 1).version_no == 1


def test_get_spec_returns_the_exact_workflow_spec_registered_for_that_version():
    registry = WorkflowDefinitionRegistry()
    spec_v1 = _spec_v1()
    v1 = registry.register_version(spec_v1)

    assert registry.get_spec(v1) == spec_v1


@pytest.mark.asyncio
async def test_build_steps_resolves_the_workflow_spec_for_that_specific_version():
    registry = WorkflowDefinitionRegistry()
    v1 = registry.register_version(_spec_v1())
    v2 = registry.register_version(_spec_v2())
    engine = WorkflowEngine()

    steps_v1 = registry.build_steps(v1, engine, custom_step_builders=_BUILDERS_V1)
    steps_v2 = registry.build_steps(v2, engine, custom_step_builders=_BUILDERS_V2)

    assert [s.name for s in steps_v1] == ["write"]
    assert [s.name for s in steps_v2] == ["write", "notify"]


@pytest.mark.asyncio
async def test_workflow_engine_runs_the_current_version_end_to_end():
    registry = WorkflowDefinitionRegistry()
    registry.register_version(_spec_v1())
    registry.register_version(_spec_v2())

    definition = registry.current_version("send-flow")
    engine = WorkflowEngine()
    steps = registry.build_steps(definition, engine, custom_step_builders=_BUILDERS_V2)

    workflow = await engine.start("send-flow", steps, {})

    assert workflow.status == WorkflowStatus.COMPLETED
    assert workflow.state == {"record_id": "rec-v2", "extra_step_ran": True, "notified": True}


@pytest.mark.asyncio
async def test_resume_uses_the_pinned_version_even_after_a_newer_version_is_published():
    registry = WorkflowDefinitionRegistry()
    pinned = registry.register_version(_spec_v1())
    engine = WorkflowEngine()

    steps_at_start = registry.build_steps(pinned, engine, custom_step_builders=_BUILDERS_V1)
    workflow = await engine.start("send-flow", steps_at_start, {})
    assert workflow.state == {"record_id": "rec-v1"}

    registry.register_version(_spec_v2())

    steps_for_resume = registry.build_steps(pinned, engine, custom_step_builders=_BUILDERS_V1)
    assert [s.name for s in steps_for_resume] == ["write"]


@pytest.mark.asyncio
async def test_resume_completes_the_pinned_version_end_to_end_even_after_a_newer_version_is_registered():
    class MockToolSpec:
        def __init__(self, name: str, handler, risk_level=CapabilityRisk.LOW):
            self.name = name
            self._handler = handler
            self.risk_level = risk_level

        async def execute(self, **kwargs):
            return await self._handler(kwargs)

    class MockToolRegistry:
        def __init__(self):
            self._tools = {}

        def register(self, tool):
            self._tools[tool.name] = tool

        def get(self, name: str):
            return self._tools.get(name)

    class MockApproval:
        def __init__(self, id: str):
            self.id = id
            self.status = "PENDING"
            self.reason = ""

    class MockApprovalService:
        def __init__(self):
            self._approvals = {}

        def request_approval(self, *args, **kw):
            appr = MockApproval("appr-1")
            self._approvals["appr-1"] = appr
            return appr

        def find_by_run_and_action(self, *args, **kw):
            return self._approvals.get("appr-1")

        def decide(self, approval_id: str, reviewer: str, approved: bool):
            if approval_id in self._approvals:
                self._approvals[approval_id].status = "APPROVED" if approved else "DENIED"


    class MockPolicyEngine:
        def evaluate_access(self, **kw):
            return "REQUIRE_APPROVAL"

    async def deploy_handler(args):
        return {"deployed": True}

    async def notify_handler(args):
        return {"notified": True}

    tool_registry = MockToolRegistry()
    tool_registry.register(MockToolSpec("ops.deploy.prod", deploy_handler, CapabilityRisk.HIGH))
    tool_registry.register(MockToolSpec("ops.notify", notify_handler, CapabilityRisk.LOW))

    definitions = WorkflowDefinitionRegistry()
    spec_v1 = WorkflowSpec(
        id="deploy-flow", steps=[WorkflowStepSpec(id="deploy", type=StepType.TOOL_CALL, tool="ops.deploy.prod")]
    )
    definitions.register_version(spec_v1)

    approval_svc = MockApprovalService()
    engine = WorkflowEngine(tool_registry=tool_registry, policy_engine=MockPolicyEngine(), approval_service=approval_svc)

    workflow = await engine.execute_spec(spec_v1, initial_state={"workspace_id": "ws1", "run_id": "run-drift"})
    assert workflow.status == WorkflowStatus.WAITING_APPROVAL
    approval_id = workflow.pending_approval_id

    spec_v2 = WorkflowSpec(
        id="deploy-flow",
        steps=[
            WorkflowStepSpec(id="deploy", type=StepType.TOOL_CALL, tool="ops.deploy.prod"),
            WorkflowStepSpec(id="notify", type=StepType.TOOL_CALL, tool="ops.notify"),
        ],
    )
    definitions.register_version(spec_v2)

    approval_svc.decide(approval_id, reviewer="founder-1", approved=True)

    resumed = await engine.execute_spec(spec_v1, initial_state={}, workflow=workflow)

    assert resumed.status == WorkflowStatus.COMPLETED
    assert resumed.state["deploy"] == {"deployed": True}
    assert "notify" not in resumed.completed_steps
