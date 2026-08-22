import asyncio
from pathlib import Path
import pytest
from agentos.core.approval import ApprovalService
from agentos.core.audit_sink import SqliteAuditSink
from agentos.core.model_provider import ModelResponse, ToolCallRequest
from agentos.core.models import TaskContext
from agentos.core.policy import PermissionLevel, PolicyEngine, ToolPermission, ToolRiskLevel
from agentos.core.runtime import AgentRuntime
from agentos.core.trace_sink import SqliteTraceSink
from agentos.tools.registry import ToolRegistry
from agentos.tools.spec import ToolSpecV2


class StubModel:
    def __init__(self, responses: list[ModelResponse]) -> None:
        self._responses = list(responses)
        self.call_count = 0

    async def generate(self, system_prompt: str, messages: list[dict]) -> ModelResponse:
        resp = self._responses[self.call_count]
        self.call_count += 1
        return resp


@pytest.mark.asyncio
async def test_full_chain_correlation_id_and_audit_propagation(tmp_path: Path):
    audit_db = tmp_path / "audit.sqlite3"
    trace_db = tmp_path / "trace.sqlite3"

    audit_sink = SqliteAuditSink(db_path=audit_db)
    trace_sink = SqliteTraceSink(db_path=trace_db)
    policy_engine = PolicyEngine(audit_sink=audit_sink)
    approval_service = ApprovalService(audit_sink=audit_sink)

    tool_registry = ToolRegistry()

    async def create_task_handler(args: dict) -> dict:
        return {"id": 999, "title": args.get("title"), "status": "created"}

    spec = ToolSpecV2(
        name="operations.task.create",
        description="Create task",
        input_schema={
            "type": "object",
            "properties": {
                "workspaceId": {"type": "number"},
                "title": {"type": "string"},
                "apiKey": {"type": "string"},
            },
            "required": ["workspaceId", "title"],
        },
        output_schema={"type": "object"},
        handler=create_task_handler,
        risk_level=ToolRiskLevel.LOW,
        tool_permission=ToolPermission.SCOPED_WRITE,
        approval_policy="conditional",
        audit_policy="full",
    )
    tool_registry.register(spec)

    responses = [
        ModelResponse(
            text=None,
            tool_call=ToolCallRequest(
                tool_name="operations.task.create",
                arguments={"workspaceId": 123, "title": "Launch Phase 3", "apiKey": "super_secret_token_123"},
            ),
        ),
        ModelResponse(
            text="Task Launch Phase 3 created successfully.",
            tool_call=None,
        ),
    ]
    model_provider = StubModel(responses)

    runtime = AgentRuntime(
        model_provider=model_provider,
        tool_registry=tool_registry,
        policy_engine=policy_engine,
        approval_service=approval_service,
        trace_sink=trace_sink,
    )

    correlation_id = "corr-test-trace-9999"
    task = TaskContext(
        goal="Tạo task Launch Phase 3",
        agent_key="copilot_agent",
        workspace_id="123",
        company_id="comp-456",
        user_id="user-789",
        workforce_member_id="wf-101",
        correlation_id=correlation_id,
        role="founder",
        agent_permission_level=PermissionLevel.L3_EXECUTE,
    )

    result = await runtime.run(task)
    assert result.status.value == "COMPLETED"
    assert result.tool_calls_made == 1

    # 1. Verify Trace Sink events have correlation_id, workspace_id, company_id
    trace_events = trace_sink.export_by_correlation_id(correlation_id)
    assert len(trace_events) >= 2
    for ev in trace_events:
        assert ev["correlation_id"] == correlation_id
        assert ev["workspace_id"] == "123"
        assert ev["company_id"] == "comp-456"

    # 2. Verify Governance Audit Sink records have correlation_id, principal, redacted payload, and outcome
    audit_records = audit_sink.export_by_correlation_id(correlation_id)
    assert len(audit_records) >= 1

    tool_audit = next(r for r in audit_records if r["event_type"] == "tool.executed")
    assert tool_audit["correlation_id"] == correlation_id
    assert tool_audit["workspace_id"] == "123"
    assert tool_audit["company_id"] == "comp-456"
    assert tool_audit["tool_name"] == "operations.task.create"
    assert tool_audit["principal"] == "user:user-789"
    assert tool_audit["decision"] == "ALLOW"

    # Verify input_payload was REDACTED (apiKey masked)
    assert "super_secret_token_123" not in tool_audit["input_payload"]
    assert "***REDACTED***" in tool_audit["input_payload"]
    assert "Launch Phase 3" in tool_audit["input_payload"]

    audit_sink.close()
    trace_sink.close()
