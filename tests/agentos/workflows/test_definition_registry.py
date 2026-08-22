import pytest

from agentos.workflows.definition_registry import (
    WorkflowDefinitionNotFoundError,
    WorkflowDefinitionRegistry,
    WorkflowVersionNotFoundError,
)
from agentos.workflows.engine import WorkflowEngine
from agentos.workflows.models import WorkflowStatus
from agentos.workflows.steps import DeterministicStep


async def _write_v1(state: dict) -> dict:
    return {"record_id": "rec-v1"}


async def _write_v2(state: dict) -> dict:
    return {"record_id": "rec-v2", "extra_step_ran": True}


async def _notify(state: dict) -> dict:
    return {"notified": True}


def _steps_v1() -> list:
    return [DeterministicStep("write", _write_v1)]


def _steps_v2() -> list:
    return [DeterministicStep("write", _write_v2), DeterministicStep("notify", _notify)]


def test_register_version_assigns_sequential_version_numbers():
    registry = WorkflowDefinitionRegistry()

    v1 = registry.register_version("send-flow", _steps_v1)
    v2 = registry.register_version("send-flow", _steps_v2)

    assert v1.version_no == 1
    assert v2.version_no == 2
    assert v1.id != v2.id


def test_current_version_returns_the_most_recently_registered_version():
    registry = WorkflowDefinitionRegistry()
    registry.register_version("send-flow", _steps_v1)
    v2 = registry.register_version("send-flow", _steps_v2)

    assert registry.current_version("send-flow") == v2


def test_current_version_raises_when_name_never_registered():
    registry = WorkflowDefinitionRegistry()
    with pytest.raises(WorkflowDefinitionNotFoundError):
        registry.current_version("unknown-flow")


def test_get_version_returns_an_older_immutable_version():
    registry = WorkflowDefinitionRegistry()
    v1 = registry.register_version("send-flow", _steps_v1)
    registry.register_version("send-flow", _steps_v2)

    assert registry.get_version("send-flow", 1) == v1


def test_get_version_raises_for_unknown_version_number():
    registry = WorkflowDefinitionRegistry()
    registry.register_version("send-flow", _steps_v1)

    with pytest.raises(WorkflowVersionNotFoundError):
        registry.get_version("send-flow", 99)


def test_history_returns_every_registered_version_in_order():
    registry = WorkflowDefinitionRegistry()
    v1 = registry.register_version("send-flow", _steps_v1)
    v2 = registry.register_version("send-flow", _steps_v2)

    assert registry.history("send-flow") == [v1, v2]


def test_registering_a_new_version_does_not_mutate_the_previous_one():
    registry = WorkflowDefinitionRegistry()
    v1 = registry.register_version("send-flow", _steps_v1)
    registry.register_version("send-flow", _steps_v2)

    # v1 vẫn nguyên vẹn, không bị "current" mới ghi đè lên (bất biến).
    assert registry.get_version("send-flow", 1) == v1
    assert registry.get_version("send-flow", 1).version_no == 1


@pytest.mark.asyncio
async def test_build_steps_resolves_the_step_factory_for_that_specific_version():
    registry = WorkflowDefinitionRegistry()
    v1 = registry.register_version("send-flow", _steps_v1)
    v2 = registry.register_version("send-flow", _steps_v2)

    steps_v1 = registry.build_steps(v1)
    steps_v2 = registry.build_steps(v2)

    assert [s.name for s in steps_v1] == ["write"]
    assert [s.name for s in steps_v2] == ["write", "notify"]


@pytest.mark.asyncio
async def test_workflow_engine_runs_the_current_version_end_to_end():
    registry = WorkflowDefinitionRegistry()
    registry.register_version("send-flow", _steps_v1)
    registry.register_version("send-flow", _steps_v2)

    definition = registry.current_version("send-flow")
    steps = registry.build_steps(definition)
    engine = WorkflowEngine()

    workflow = await engine.start("send-flow", steps, {})

    assert workflow.status == WorkflowStatus.COMPLETED
    assert workflow.state == {"record_id": "rec-v2", "extra_step_ran": True, "notified": True}
