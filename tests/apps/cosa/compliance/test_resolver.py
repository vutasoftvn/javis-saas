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
        # Spy — capture đúng kwargs resolver truyền xuống client, để test
        # xác nhận capability_ids/delegation_token thật sự được truyền
        # (Task 4: resolver phải mint delegation và khai báo capability_ids,
        # không còn gọi client với policy_snapshot_hash rời rạc như cũ).
        self.calls: list[dict] = []

    async def resolve_snapshot(
        self,
        workspace_id: str,
        run_id: str,
        system_key: str,
        capability_ids: list[str],
        delegation_token: str,
        policy_snapshot_hash: str = "",
    ) -> ComplianceSnapshot:
        self.calls.append(
            {
                "workspace_id": workspace_id,
                "run_id": run_id,
                "system_key": system_key,
                "capability_ids": capability_ids,
                "delegation_token": delegation_token,
                "policy_snapshot_hash": policy_snapshot_hash,
            }
        )
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
        capability_refs=["finance.read"],
        model_input_capability_ref="model.input.direct-user-message",
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


@pytest.mark.asyncio
async def test_resolver_scopes_direct_model_input_when_spec_declares_no_tools(
    sample_request: RunRequest,
) -> None:
    """A chat-only agent still has a governed non-tool input scope."""
    spec_without_tools = AgentSpec(
        id="cosa_chat_only_agent",
        instructions="Advisory only",
        model_input_capability_ref="model.input.direct-user-message",
    )
    now = datetime.now(UTC)
    snapshot = ComplianceSnapshot(
        workspace_id="ws_1",
        deployment_id="dep_1",
        assessment_id="ass_1",
        mode="ADVISORY_ONLY",
        status="APPROVED_FOR_USE",
        allowed_capabilities=frozenset(["model.input.direct-user-message"]),
        provider_profile_version="v3",
        data_profile_version="v1",
        snapshot_hash="sha256:abc123",
        expires_at=now,
    )
    client = FakeAiComplianceClient(snapshot=snapshot)
    resolver = ComplianceResolver(client)

    await resolver.resolve_for_run(sample_request, spec_without_tools)

    assert client.calls[0]["capability_ids"] == ["model.input.direct-user-message"]


@pytest.mark.asyncio
async def test_resolver_mints_a_scoped_delegation_and_forwards_capability_ids(
    sample_request: RunRequest,
    sample_spec: AgentSpec,
) -> None:
    """Task 4 wiring: resolver phải mint 1 delegation JWT có cấu trúc (Task
    3) và truyền đúng capability_ids khai báo trong spec xuống client —
    trước Task 4, verifyCosaDelegation tồn tại nhưng zero call site thật."""
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
    client = FakeAiComplianceClient(snapshot=snap)
    resolver = ComplianceResolver(client)

    await resolver.resolve_for_run(sample_request, sample_spec)

    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["capability_ids"] == [
        "finance.read",
        "model.input.direct-user-message",
    ]
    assert call["capability_ids"].count("model.input.direct-user-message") == 1
    assert call["workspace_id"] == "ws_1"
    assert isinstance(call["delegation_token"], str) and call["delegation_token"]


@pytest.mark.asyncio
async def test_resolver_denies_when_company_rejects_delegation_scope(
    sample_request: RunRequest,
    sample_spec: AgentSpec,
) -> None:
    """Company trả 403 (delegation scope failure) -> client raise
    AiComplianceUnavailable("DELEGATION_DENIED", ...) -> resolver phải fail
    closed qua ComplianceDenied, không lộ ra như một lỗi khác."""
    resolver = ComplianceResolver(
        FakeAiComplianceClient(error=AiComplianceUnavailable("DELEGATION_DENIED"))
    )
    with pytest.raises(ComplianceDenied, match="DELEGATION_DENIED"):
        await resolver.resolve_for_run(sample_request, sample_spec)


@pytest.mark.asyncio
async def test_resolver_denies_when_approval_incomplete_or_expired(
    sample_request: RunRequest,
    sample_spec: AgentSpec,
) -> None:
    """Company trả 409 (approval incomplete/expired) -> fail closed, không
    bao giờ coi im lặng/lỗi là "đã approved"."""
    resolver = ComplianceResolver(
        FakeAiComplianceClient(error=AiComplianceUnavailable("APPROVAL_INCOMPLETE_OR_EXPIRED"))
    )
    with pytest.raises(ComplianceDenied, match="APPROVAL_INCOMPLETE_OR_EXPIRED"):
        await resolver.resolve_for_run(sample_request, sample_spec)
