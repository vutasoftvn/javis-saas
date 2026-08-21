from datetime import datetime, timedelta, timezone

import pytest

from core.snowflake import generate_snowflake_id
from workforce.agents.delegation.manager import DelegationProviderManager
from workforce.agents.delegation.models import DelegationJob
from workforce.agents.delegation.provider import DelegationProvider
from workforce.agents.delegation.types import (
    DelegationHandle,
    DelegationResult,
    DelegationStatus,
    ProviderHealth,
)
from workforce.agents.runtime.errors import AgentRuntimeError


class CrashAfterNativeStartOnce(DelegationProvider):
    def __init__(self):
        self.native_start_count = 0
        self.handles = {}

    @property
    def provider_name(self):
        return "crash_matrix"

    async def delegate(self, request, idempotency_key):
        if idempotency_key not in self.handles:
            self.native_start_count += 1
            self.handles[idempotency_key] = DelegationHandle(
                provider_name=self.provider_name,
                external_id=f"native-{self.native_start_count}",
            )
            raise AgentRuntimeError(
                code="SIMULATED_WORKER_CRASH",
                message="crashed after native start",
                retryable=True,
            )
        return self.handles[idempotency_key]

    async def poll(self, handle):
        return DelegationResult(
            status=DelegationStatus.SUCCEEDED,
            structured_result={"native_id": handle.external_id},
        )

    async def cancel(self, handle):
        return True

    async def health(self):
        return ProviderHealth(provider_name=self.provider_name, available=True)


@pytest.mark.asyncio
async def test_restart_reuses_idempotency_key_after_crash_post_native_start(
    transactional_sessions,
    monkeypatch,
):
    from workforce.agents.delegation import worker

    db, factory, workspace_id, parent, step = transactional_sessions
    step.status = "pending"
    step.inputs_jsonb = {"task": "Crash matrix", "user_id": parent.user_id}
    step.assigned_agent_profile_id = "marketing"
    step.assigned_runtime = "mock"
    job = DelegationJob(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        run_step_id=step.id,
        root_agent_run_id=parent.id,
        parent_agent_run_id=parent.id,
        attempt_no=1,
        provider_kind="test",
        provider_name="crash_matrix",
        profile_id="marketing",
        runtime_name="mock",
        status="queued",
        idempotency_key=f"crash:{step.id}:1",
        available_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
    )
    db.add(job)
    db.commit()
    db.query(DelegationJob).filter(DelegationJob.id != job.id).filter(
        DelegationJob.status.notin_(("denied", "succeeded", "failed", "cancelled"))
    ).update(
        {DelegationJob.lease_expires_at: datetime.now(timezone.utc) + timedelta(days=1)},
        synchronize_session=False,
    )
    db.commit()
    provider = CrashAfterNativeStartOnce()
    manager = DelegationProviderManager()
    manager.register(provider)
    monkeypatch.setattr(worker, "delegation_provider_manager", manager)

    assert worker.claim_due_job(db, "worker-a", datetime.now(timezone.utc)) == job.id
    await worker.process_delegation_job(job.id, "worker-a", session_factory=factory)
    db.expire_all()
    retrying = db.get(DelegationJob, job.id)
    assert retrying.status == "retry_scheduled"
    retrying.available_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

    assert worker.claim_due_job(db, "worker-b", datetime.now(timezone.utc)) == job.id
    await worker.process_delegation_job(job.id, "worker-b", session_factory=factory)

    db.expire_all()
    assert db.get(DelegationJob, job.id).status == "succeeded"
    assert provider.native_start_count == 1
