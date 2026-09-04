from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from apps.cosa.compliance.contracts import ComplianceDenied
from apps.cosa.worker.run_core import RunCoreError, prepare_request, resolve_spec, run_kernel


class _Snapshot:
    def model_dump(self) -> dict:
        return {"gate": "ok"}


def _spec():
    return SimpleNamespace(
        to_pinned_identity=lambda: "cosa.agents.operations@1.1.0#hash",
        spec_id="cosa.agents.operations",
    )


@pytest.mark.asyncio
async def test_prepare_request_omits_policy_snapshot_when_none():
    resolver = AsyncMock()
    resolver.resolve_for_run.return_value = {"_company_delegation_token": "jwt-123"}
    plane = SimpleNamespace(compliance_resolver=resolver)

    prep = await prepare_request(
        plane,
        spec=_spec(),
        run_id="r1",
        prompt="do the thing",
        principal="system:wga",
        workspace_id="ws1",
        conversation_id="c1",
        policy_snapshot=None,
    )
    assert prep.company_delegation_token == "jwt-123"
    assert "policy_snapshot" not in prep.req.metadata
    assert prep.req.metadata["_company_delegation_token"] == "jwt-123"


@pytest.mark.asyncio
async def test_prepare_request_includes_policy_snapshot_and_extra_metadata():
    resolver = AsyncMock()
    resolver.resolve_for_run.return_value = {"_company_delegation_token": "jwt-9"}
    plane = SimpleNamespace(compliance_resolver=resolver)

    prep = await prepare_request(
        plane,
        spec=_spec(),
        run_id="r2",
        prompt="p",
        principal="u",
        workspace_id="ws1",
        conversation_id="c1",
        policy_snapshot=_Snapshot(),
        extra_metadata={"direct_message_data_access": {"hash": "abc"}},
    )
    assert prep.req.metadata["policy_snapshot"] == {"gate": "ok"}
    assert prep.req.metadata["direct_message_data_access"] == {"hash": "abc"}


@pytest.mark.asyncio
async def test_prepare_request_raises_when_no_compliance_resolver():
    plane = SimpleNamespace(compliance_resolver=None)
    with pytest.raises(RunCoreError) as ei:
        await prepare_request(
            plane,
            spec=_spec(),
            run_id="r",
            prompt="p",
            principal="u",
            workspace_id="w",
            conversation_id="c",
            policy_snapshot=None,
        )
    assert ei.value.reason_code == "compliance_resolver_unavailable"


@pytest.mark.asyncio
async def test_prepare_request_maps_compliance_denied_to_code():
    resolver = AsyncMock()
    resolver.resolve_for_run.side_effect = ComplianceDenied("DATA_EGRESS_BLOCKED")
    plane = SimpleNamespace(compliance_resolver=resolver)
    with pytest.raises(RunCoreError) as ei:
        await prepare_request(
            plane,
            spec=_spec(),
            run_id="r",
            prompt="p",
            principal="u",
            workspace_id="w",
            conversation_id="c",
            policy_snapshot=None,
        )
    assert ei.value.reason_code == "compliance_denied"
    assert ei.value.compliance_code == "DATA_EGRESS_BLOCKED"


@pytest.mark.asyncio
async def test_prepare_request_raises_when_delegation_token_missing():
    resolver = AsyncMock()
    resolver.resolve_for_run.return_value = {"something_else": True}
    plane = SimpleNamespace(compliance_resolver=resolver)
    with pytest.raises(RunCoreError) as ei:
        await prepare_request(
            plane,
            spec=_spec(),
            run_id="r",
            prompt="p",
            principal="u",
            workspace_id="w",
            conversation_id="c",
            policy_snapshot=None,
        )
    assert ei.value.compliance_code == "MISSING_DELEGATION_TOKEN"


@pytest.mark.asyncio
async def test_resolve_spec_maps_missing_dependency_to_stable_code():
    from agent.registry.repository import SpecDependencyMissingError

    async def _raise(*_a, **_k):
        raise SpecDependencyMissingError("prompt", "secret-detail", "v1", "not_found")

    plane = SimpleNamespace(spec_registry=object())
    import apps.cosa.worker.run_core as rc

    orig = rc.SpecResolver.resolve_agent_spec_dependencies
    rc.SpecResolver.resolve_agent_spec_dependencies = _raise  # type: ignore[method-assign]
    try:
        with pytest.raises(RunCoreError) as ei:
            await resolve_spec(plane, run_id="r", local_spec=_spec())
        assert ei.value.reason_code == "spec_resolution_unavailable"
        assert "secret-detail" not in str(ei.value)
    finally:
        rc.SpecResolver.resolve_agent_spec_dependencies = orig  # type: ignore[method-assign]


@pytest.mark.asyncio
async def test_run_kernel_invokes_plane_kernel_and_times_it():
    kernel = AsyncMock()
    kernel.run.return_value = SimpleNamespace(status="completed")
    plane = SimpleNamespace(kernel=kernel)
    prep = SimpleNamespace(spec=_spec(), req=SimpleNamespace())
    result, duration = await run_kernel(plane, prep, workspace_id="w", run_id="r")
    assert result.status == "completed"
    assert duration >= 0.0
    kernel.run.assert_awaited_once()
