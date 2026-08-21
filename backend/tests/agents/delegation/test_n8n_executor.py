import pytest
from fastapi import HTTPException

from core.snowflake import generate_snowflake_id
from workforce.automation.models import AutomationRun

from workforce.agents.execution.long_running.types import (
    WorkContext,
    WorkRequest,
    WorkState,
)
from workforce.automation.runtime.types import (
    AutomationHealth,
    AutomationRunStatus,
    AutomationStartResult,
)


class FakeAutomationProvider:
    def __init__(self):
        self.execute_calls = 0

    async def execute(self, request):
        self.execute_calls += 1
        return AutomationStartResult(
            execution_id=request.execution_id,
            provider_execution_id="n8n-native-1",
            status="running",
        )

    async def get_status(self, external_run_id):
        return AutomationRunStatus(status="succeeded", result={"sent": True})

    async def cancel(self, external_run_id):
        raise NotImplementedError

    async def health(self):
        return AutomationHealth(provider="n8n", status="healthy")

    async def list_capabilities(self):
        return ["sales.followup_email"]


@pytest.mark.asyncio
async def test_n8n_executor_is_idempotent_and_maps_native_status(transactional_sessions):
    from workforce.agents.execution.long_running.providers.n8n import N8nExecutor

    db, factory, workspace_id, parent_run, step = transactional_sessions
    native = FakeAutomationProvider()
    provider = N8nExecutor(provider=native, session_factory=factory)
    context = WorkContext(
        workspace_id=workspace_id,
        outcome_run_id=step.run_id,
        run_step_id=step.id,
        root_agent_run_id=parent_run.id,
        parent_agent_run_id=parent_run.id,
        profile_id="marketing",
    )
    request = WorkRequest(
        task="Send follow-up",
        permission_profile="l3_execute",
        payload={"automation_key": "sales.followup_email", "lead_id": "lead-1"},
    )

    first = await provider.start(context, request, "n8n-same")
    second = await provider.start(context, request, "n8n-same")
    status = await provider.poll(context, first)

    assert first.external_id == second.external_id
    assert native.execute_calls == 1
    assert status.state == WorkState.SUCCEEDED
    assert status.structured_result == {"sent": True}


def test_n8n_callback_replay_is_rejected_after_full_correlation_check(
    transactional_sessions,
):
    from workforce.automation.router import process_n8n_delegation_callback

    db, _factory, workspace_id, parent_run, _step = transactional_sessions
    run = AutomationRun(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        company_id=workspace_id,
        automation_key="sales.followup_email",
        provider="n8n",
        provider_execution_id="n8n-native-2",
        agent_run_id=parent_run.id,
        status="running",
        risk_level="high",
        idempotency_key="correlation-2",
        payload_jsonb={"correlation_id": "correlation-2"},
    )
    db.add(run)
    db.commit()
    payload = {
        "execution_id": str(run.id),
        "provider_execution_id": "n8n-native-2",
        "workspace_id": str(workspace_id),
        "provider": "n8n",
        "correlation_id": "correlation-2",
        "event_key": "n8n-event-2",
        "status": "succeeded",
        "result": {"sent": True},
    }

    accepted = process_n8n_delegation_callback(
        db=db,
        data=payload,
        signature="signed-event-2",
    )

    assert accepted == {"status": "accepted", "verified": True, "run_id": str(run.id)}
    with pytest.raises(HTTPException) as replay:
        process_n8n_delegation_callback(
            db=db,
            data=payload,
            signature="signed-event-2",
        )
    assert replay.value.status_code == 409
