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
from apps.cosa.compliance.data_access_claim import DataAccessClaim
from apps.cosa.compliance.data_egress_context import DirectMessageDataAccess
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
        provider_key="deepseek",
        model_key="deepseek-chat",
        purpose_id="advisory",
        retention_policy_id="retain-30d",
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
        provider_key="deepseek",
        model_key="deepseek-chat",
        purpose_id="advisory",
        retention_policy_id="retain-30d",
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
        provider_key="deepseek",
        model_key="deepseek-chat",
        purpose_id="advisory",
        retention_policy_id="retain-30d",
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
async def test_resolver_deduplicates_tools_and_malformed_overlapping_input_scope(
    sample_request: RunRequest,
) -> None:
    malformed_spec = AgentSpec.model_construct(
        id="cosa_malformed_legacy_agent",
        capability_refs=[
            "finance.read",
            "finance.read",
            "model.input.direct-user-message",
            "model.input.direct-user-message",
        ],
        model_input_capability_ref="model.input.direct-user-message",
    )
    now = datetime.now(UTC)
    snapshot = ComplianceSnapshot(
        workspace_id="ws_1",
        deployment_id="dep_1",
        assessment_id="ass_1",
        mode="ADVISORY_ONLY",
        status="APPROVED_FOR_USE",
        allowed_capabilities=frozenset(
            ["finance.read", "model.input.direct-user-message"]
        ),
        provider_profile_version="v3",
        data_profile_version="v1",
        provider_key="deepseek",
        model_key="deepseek-chat",
        purpose_id="advisory",
        retention_policy_id="retain-30d",
        snapshot_hash="sha256:abc123",
        expires_at=now,
    )
    client = FakeAiComplianceClient(snapshot=snapshot)

    await ComplianceResolver(client).resolve_for_run(sample_request, malformed_spec)

    assert client.calls[0]["capability_ids"] == [
        "finance.read",
        "model.input.direct-user-message",
    ]


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
async def test_resolver_builds_data_access_claim_from_direct_message_context(
    sample_request: RunRequest,
    sample_spec: AgentSpec,
) -> None:
    """Task 4 — Data Egress Context: khi caller khai báo
    `direct_message_data_access` trong metadata, resolver phải dựng
    `DataAccessClaim` thật, LẤY provider/model/purpose/retention TỪ SNAPSHOT
    (không phải từ context caller khai báo)."""
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
        provider_key="deepseek",
        model_key="deepseek-chat",
        purpose_id="advisory",
        retention_policy_id="retain-30d",
        snapshot_hash="sha256:abc123",
        expires_at=now,
    )
    direct_access = DirectMessageDataAccess.from_message(
        message_id="msg_1",
        content="Analyze finance",
        categories=frozenset({"BUSINESS_CONFIDENTIAL"}),
        subject_reference=None,
    )
    request_with_context = sample_request.model_copy(
        update={"metadata": {"direct_message_data_access": direct_access}}
    )
    resolver = ComplianceResolver(FakeAiComplianceClient(snapshot=snap))

    metadata = await resolver.resolve_for_run(request_with_context, sample_spec)

    claim = metadata["data_access_claim"]
    assert isinstance(claim, DataAccessClaim)
    assert claim.workspace_id == "ws_1"
    assert claim.deployment_id == "dep_1"
    assert claim.capability_id == "model.input.direct-user-message"
    assert claim.source_ref == "conversation_message:msg_1"
    assert claim.categories == frozenset({"BUSINESS_CONFIDENTIAL"})
    assert claim.provider_key == "deepseek"
    assert claim.model_key == "deepseek-chat"
    assert claim.purpose_id == "advisory"
    assert claim.retention_policy_id == "retain-30d"


@pytest.mark.asyncio
async def test_resolver_builds_data_access_claim_from_plain_dict_context(
    sample_request: RunRequest,
    sample_spec: AgentSpec,
) -> None:
    """`direct_message_data_access` cũng có thể tới dưới dạng dict thô (vd.
    sau khi round-trip qua JSON) — resolver phải coerce và validate y hệt
    như khi nhận thẳng 1 `DirectMessageDataAccess`."""
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
        provider_key="deepseek",
        model_key="deepseek-chat",
        purpose_id="advisory",
        retention_policy_id="retain-30d",
        snapshot_hash="sha256:abc123",
        expires_at=now,
    )
    request_with_context = sample_request.model_copy(
        update={
            "metadata": {
                "direct_message_data_access": {
                    "categories": frozenset({"BUSINESS_CONFIDENTIAL"}),
                    "subject_reference": None,
                    "source_ref": "conversation_message:msg_2",
                    "source_hash": "abc",
                }
            }
        }
    )
    resolver = ComplianceResolver(FakeAiComplianceClient(snapshot=snap))

    metadata = await resolver.resolve_for_run(request_with_context, sample_spec)

    assert metadata["data_access_claim"].source_ref == "conversation_message:msg_2"


@pytest.mark.asyncio
async def test_resolver_denies_when_direct_message_context_is_invalid(
    sample_request: RunRequest,
    sample_spec: AgentSpec,
) -> None:
    """Category PERSONAL không có subject_reference là 1 context không hợp
    lệ — fail-closed với DATA_ACCESS_CLAIM_MISSING, không im lặng bỏ qua và
    không rơi về redactor-only."""
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
        provider_key="deepseek",
        model_key="deepseek-chat",
        purpose_id="advisory",
        retention_policy_id="retain-30d",
        snapshot_hash="sha256:abc123",
        expires_at=now,
    )
    request_with_context = sample_request.model_copy(
        update={
            "metadata": {
                "direct_message_data_access": {
                    "categories": frozenset({"PERSONAL"}),
                    "subject_reference": None,
                    "source_ref": "conversation_message:msg_3",
                    "source_hash": "abc",
                }
            }
        }
    )
    resolver = ComplianceResolver(FakeAiComplianceClient(snapshot=snap))

    with pytest.raises(ComplianceDenied, match="DATA_ACCESS_CLAIM_MISSING"):
        await resolver.resolve_for_run(request_with_context, sample_spec)


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
