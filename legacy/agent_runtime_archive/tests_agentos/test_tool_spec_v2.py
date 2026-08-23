import asyncio
import pytest
from agentos.core.policy import PermissionLevel, PolicyDecision, PolicyEngine, ToolPermission, ToolRiskLevel
from agentos.tools.registry import ToolNotFoundError, ToolRegistry
from agentos.tools.spec import (
    ToolExecutionTimeoutError,
    ToolSpecV2,
    ToolValidationError,
    validate_tool_input,
    validate_tool_output,
)


@pytest.mark.asyncio
async def test_tool_spec_v2_instantiation_and_defaults():
    async def dummy_handler(args: dict) -> dict:
        return {"result": "ok"}

    spec = ToolSpecV2(
        name="operations.task.create",
        version="1.0.0",
        description="Create a task",
        input_schema={
            "type": "object",
            "properties": {"workspaceId": {"type": "number"}, "title": {"type": "string"}},
            "required": ["workspaceId", "title"],
        },
        output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
        handler=dummy_handler,
        risk_level=ToolRiskLevel.MEDIUM,
        tool_permission=ToolPermission.SCOPED_WRITE,
        write_scope="workspace",
        idempotent=False,
        reversible=True,
        approval_policy="conditional",
        audit_policy="full",
        timeout_seconds=5,
        tags=["operations", "task"],
    )

    assert spec.name == "operations.task.create"
    assert spec.version == "1.0.0"
    assert spec.risk_level == ToolRiskLevel.MEDIUM
    assert spec.tool_permission == ToolPermission.SCOPED_WRITE
    assert spec.write_scope == "workspace"
    assert spec.idempotent is False
    assert spec.reversible is True
    assert spec.approval_policy == "conditional"
    assert spec.audit_policy == "full"
    assert spec.timeout_seconds == 5
    assert "operations" in spec.tags


@pytest.mark.asyncio
async def test_tool_input_validation_success():
    schema = {
        "type": "object",
        "properties": {"workspaceId": {"type": "number"}, "title": {"type": "string"}},
        "required": ["workspaceId", "title"],
    }
    valid_input = {"workspaceId": 123, "title": "Deploy API"}
    validate_tool_input(schema, valid_input, tool_name="operations.task.create")


@pytest.mark.asyncio
async def test_tool_input_validation_rejection_missing_required():
    schema = {
        "type": "object",
        "properties": {"workspaceId": {"type": "number"}, "title": {"type": "string"}},
        "required": ["workspaceId", "title"],
    }
    invalid_input = {"workspaceId": 123}

    with pytest.raises(ToolValidationError) as exc_info:
        validate_tool_input(schema, invalid_input, tool_name="operations.task.create")
    assert "title" in str(exc_info.value)


@pytest.mark.asyncio
async def test_tool_input_validation_rejection_wrong_type():
    schema = {
        "type": "object",
        "properties": {"workspaceId": {"type": "number"}, "title": {"type": "string"}},
        "required": ["workspaceId", "title"],
    }
    invalid_input = {"workspaceId": "not-a-number", "title": "Deploy API"}

    with pytest.raises(ToolValidationError) as exc_info:
        validate_tool_input(schema, invalid_input, tool_name="operations.task.create")
    assert "is not of type" in str(exc_info.value)


@pytest.mark.asyncio
async def test_tool_output_validation_rejection():
    schema = {
        "type": "object",
        "properties": {"id": {"type": "number"}, "status": {"type": "string"}},
        "required": ["id", "status"],
    }
    invalid_output = {"id": 100}  # missing status

    with pytest.raises(ToolValidationError):
        validate_tool_output(schema, invalid_output, tool_name="operations.task.create")


@pytest.mark.asyncio
async def test_tool_execution_timeout():
    async def slow_handler(args: dict) -> dict:
        await asyncio.sleep(1.0)
        return {"done": True}

    spec = ToolSpecV2(
        name="operations.slow.run",
        description="Slow running tool",
        handler=slow_handler,
        timeout_seconds=0.1,
    )

    registry = ToolRegistry()
    registry.register(spec)

    with pytest.raises(ToolExecutionTimeoutError):
        await registry.invoke("operations.slow.run", {})


@pytest.mark.asyncio
async def test_tool_registry_alias_bidirectional_lookup():
    async def sample_handler(args: dict) -> dict:
        return {"id": args.get("id", 1), "status": "active"}

    spec = ToolSpecV2(
        name="operations.task.create",
        description="Create task",
        handler=sample_handler,
    )

    registry = ToolRegistry()
    registry.register(spec)

    # Lookup by canonical name
    assert registry.get("operations.task.create").name == "operations.task.create"
    # Lookup by legacy alias
    assert registry.get("task_create").name == "operations.task.create"

    # Invocation by alias
    res = await registry.invoke("task_create", {"id": 42})
    assert res == {"id": 42, "status": "active"}


@pytest.mark.asyncio
async def test_policy_engine_evaluates_approval_policy():
    engine = PolicyEngine()

    # approval_policy="always" requires approval even for founder on low risk read/write
    decision_always = engine.evaluate_access(
        role="founder",
        agent_permission_level=PermissionLevel.L3_EXECUTE,
        tool_risk_level=ToolRiskLevel.LOW,
        tool_permission=ToolPermission.READ_ONLY,
        approval_policy="always",
    )
    assert decision_always == PolicyDecision.REQUIRE_APPROVAL

    # approval_policy="never" allows even high risk write for founder
    decision_never = engine.evaluate_access(
        role="founder",
        agent_permission_level=PermissionLevel.L1_SUGGEST,
        tool_risk_level=ToolRiskLevel.HIGH,
        tool_permission=ToolPermission.SCOPED_WRITE,
        approval_policy="never",
    )
    assert decision_never == PolicyDecision.ALLOW

    # auditor trying to write with approval_policy="never" is still DENIED (strict safety invariant)
    decision_auditor = engine.evaluate_access(
        role="auditor",
        agent_permission_level=PermissionLevel.L3_EXECUTE,
        tool_risk_level=ToolRiskLevel.LOW,
        tool_permission=ToolPermission.SCOPED_WRITE,
        approval_policy="never",
    )
    assert decision_auditor == PolicyDecision.DENY
