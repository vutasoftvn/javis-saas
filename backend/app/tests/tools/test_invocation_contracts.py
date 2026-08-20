import pytest
from app.workforce.tools.invocation.contracts import ToolInvocationRequest, ToolInvocationResult, ToolInvocationError
from app.core.tool_registry import ToolSpec
from app.workforce.agents.runtime.execution_scope import ExecutionScope

def sample_tool():
    pass

def test_tool_invocation_request_fields():
    scope = ExecutionScope(
        workspace_id=1,
        company_id=1,
        principal_user_id=1,
        principal_member_id=1,
        principal_role="owner",
        operating_unit_id=None,
        offering_id=None,
        initiative_id=None,
        profile_id=None,
        session_id=None,
        grants=()
    )
    
    req = ToolInvocationRequest(
        scope=scope,
        tool_flat_name="test_tool",
        arguments={"arg": 1},
        source="chat"
    )
    
    assert req.correlation_id is not None
    assert req.causation_id == req.correlation_id # by default
    assert req.scope == scope
    assert req.arguments == {"arg": 1}

def test_tool_spec_additive_fields():
    spec = ToolSpec(
        namespace="test",
        name="tool",
        callable=sample_tool,
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        timeout_seconds=30,
        retry_policy={"max_retries": 3},
        idempotency_key_field="request_id",
        concurrency_key="workspace_id",
        required_scope_level="operating_unit",
        required_secret_refs=["github_token"],
        backend_id="mcp.github"
    )
    
    assert spec.input_schema == {"type": "object"}
    assert spec.timeout_seconds == 30
    assert spec.retry_policy == {"max_retries": 3}
    assert spec.idempotency_key_field == "request_id"
    assert spec.concurrency_key == "workspace_id"
    assert spec.required_scope_level == "operating_unit"
    assert spec.required_secret_refs == ["github_token"]
    assert spec.backend_id == "mcp.github"
