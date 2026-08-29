from __future__ import annotations

from datetime import UTC, datetime

import pytest
from agent.contracts.run import RunRequest
from agent.contracts.spec import AgentSpec

from apps.cosa.compliance.contracts import (
    AiComplianceUnavailable,
    ComplianceDenied,
    ComplianceSnapshot,
)
from apps.cosa.compliance.resolver import ComplianceResolver


class FakeAiComplianceClient:
    def __init__(
        self,
        snapshot: ComplianceSnapshot | None = None,
        error: Exception | None = None,
    ) -> None:
        self.snapshot = snapshot
        self.error = error

    async def resolve_snapshot(
        self,
        workspace_id: str,
        run_id: str,
        system_key: str,
        policy_snapshot_hash: str | None = None,
    ) -> ComplianceSnapshot:
        if self.error:
            raise self.error
        if self.snapshot:
            return self.snapshot
        raise AiComplianceUnavailable("NOT_READY")


@pytest.fixture
def sample_spec() -> AgentSpec:
    return AgentSpec(
        id="cosa_advisory_agent",
        role="Advisory Agent",
        instructions="Advisory only",
    )


@pytest.fixture
def sample_request() -> RunRequest:
    return RunRequest(
        root_executable_ref="agent:cosa_advisory_agent",
        workspace_id="ws_1",
        principal="founder_1",
        input={"prompt": "Analyze finance"},
    )



@pytest.mark.asyncio
async def test_resolver_fails_closed_when_snapshot_is_not_ready(
    sample_request: RunRequest,
    sample_spec: AgentSpec,
) -> None:
    resolver = ComplianceResolver(FakeAiComplianceClient(error=AiComplianceUnavailable("NOT_READY")))
    with pytest.raises(ComplianceDenied, match="NOT_READY"):
        await resolver.resolve_for_run(sample_request, sample_spec)


@pytest.mark.asyncio
async def test_resolver_attaches_snapshot_hash(
    sample_request: RunRequest,
    sample_spec: AgentSpec,
) -> None:
    now = datetime.now(UTC)
    snap = ComplianceSnapshot(
        workspace_id="ws_1",
        deployment_id="dep_1",
        assessment_id="ass_1",
        mode="ADVISORY_ONLY",
        status="APPROVED_FOR_USE",
        allowed_capabilities=frozenset(["finance.read"]),
        provider_profile_version="v3",
        data_profile_version="v1",
        snapshot_hash="sha256:abc123",
        expires_at=now,
    )
    resolver = ComplianceResolver(FakeAiComplianceClient(snapshot=snap))
    metadata = await resolver.resolve_for_run(sample_request, sample_spec)
    assert metadata["compliance_snapshot_ref"] == "sha256:abc123"
    assert metadata["compliance_snapshot"]["mode"] == "ADVISORY_ONLY"
    assert metadata["compliance_snapshot_version"] == "v1"
