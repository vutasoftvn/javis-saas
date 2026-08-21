import pytest

from workforce.agents.delegation.types import (
    DelegationRequest,
    DelegationStatus,
)


class FakeLongRunningProvider:
    def __init__(self):
        self._handles = {}

    @property
    def provider_name(self):
        return "fake_long"

    async def start(self, context, request, idempotency_key):
        from workforce.agents.execution.long_running.types import WorkHandle

        return self._handles.setdefault(
            idempotency_key,
            WorkHandle(provider_name=self.provider_name, external_id=f"work:{idempotency_key}"),
        )

    async def poll(self, context, handle):
        from workforce.agents.execution.long_running.types import WorkState, WorkStatus

        return WorkStatus(
            state=WorkState.RUNNING,
            progress=0.5,
            structured_result={"phase": "testing"},
            next_poll_after_seconds=3,
        )

    async def cancel(self, context, handle):
        from workforce.agents.execution.long_running.types import CancelResult, WorkState

        return CancelResult(accepted=True, state=WorkState.CANCELLED)

    async def health(self):
        from workforce.agents.execution.long_running.types import WorkProviderHealth

        return WorkProviderHealth(provider_name=self.provider_name, available=True)

    async def capabilities(self):
        from workforce.agents.execution.long_running.types import WorkProviderCapabilities

        return WorkProviderCapabilities()


def _request():
    return DelegationRequest(
        workspace_id=1,
        outcome_run_id=2,
        run_step_id=3,
        root_agent_run_id=4,
        parent_agent_run_id=4,
        profile_id="tech",
        provider_name="fake_long",
        task="Implement and test the change",
        permission_profile="l3_execute",
        context={"project_id": "project-1"},
    )


def test_unknown_long_running_provider_is_rejected():
    from workforce.agents.execution.long_running.manager import (
        LongRunningProviderUnknown,
        LongRunningWorkProviderManager,
    )

    manager = LongRunningWorkProviderManager()
    with pytest.raises(LongRunningProviderUnknown, match="missing"):
        manager.get("missing")


@pytest.mark.asyncio
async def test_bridge_preserves_idempotency_and_normalizes_poll_status():
    from workforce.agents.delegation.providers.executor_bridge import (
        LongRunningExecutorBridge,
    )
    from workforce.agents.execution.long_running.manager import (
        LongRunningWorkProviderManager,
    )

    manager = LongRunningWorkProviderManager()
    manager.register(FakeLongRunningProvider())
    bridge = LongRunningExecutorBridge("fake_long", manager)

    first = await bridge.delegate(_request(), "same-key")
    second = await bridge.delegate(_request(), "same-key")
    status = await bridge.poll(first)

    assert first.external_id == second.external_id
    assert status.status == DelegationStatus.RUNNING
    assert status.structured_result == {"phase": "testing"}
    assert status.next_poll_at is not None
    assert await bridge.cancel(first) is True


@pytest.mark.asyncio
async def test_bridge_health_and_capabilities_remain_provider_neutral():
    from workforce.agents.delegation.providers.executor_bridge import (
        LongRunningExecutorBridge,
    )
    from workforce.agents.execution.long_running.manager import (
        LongRunningWorkProviderManager,
    )

    manager = LongRunningWorkProviderManager()
    manager.register(FakeLongRunningProvider())
    bridge = LongRunningExecutorBridge("fake_long", manager)

    health = await bridge.health()
    assert health.provider_name == "fake_long"
    assert health.available is True
