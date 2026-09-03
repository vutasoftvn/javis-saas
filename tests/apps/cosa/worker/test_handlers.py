from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from agent.conversations.repository import InMemoryConversationRepository
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository, SpecDependencyMissingError
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel

from apps.cosa.agents.seed import seed_cosa_runtime_specs
from apps.cosa.api.event_stream import CosaEventStreamManager
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from apps.cosa.policies.company_policy_client import CosaTenantPolicyError
from apps.cosa.worker.handlers import execute_resume_task, execute_run_task
from tests.apps.cosa.policy_test_helpers import (
    configure_mock_client_allows_data_use,
    fake_active_tenant_policy_client,
)


def _plane():
    # Task 7 (2026-08-30) — CosaDataModelGate.prepare_initial_input giờ gọi
    # thật self._client.resolve_data_use(...) khi có DataAccessClaim (mock
    # compliance resolver trong build_cosa_agent_plane tự gắn 1 claim mặc
    # định tối thiểu — xem _MockComplianceResolverWithDefaultClaim). Không
    # truyền company_client= ở đây sẽ khiến gate dùng CompanyServiceClient()
    # thật và cố gọi network ra http://localhost:4000 — mock rõ ràng để test
    # này không phụ thuộc 1 server Company thật đang chạy.
    mock_client = AsyncMock(spec=CompanyServiceClient)
    configure_mock_client_allows_data_use(mock_client)
    return build_cosa_agent_plane(
        company_client=mock_client,
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        tenant_policy_client=fake_active_tenant_policy_client(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )


def _payload(**overrides) -> dict:
    base = {
        "run_id": "run_handler_test_1",
        "conversation_id": "conv_1",
        "user_prompt": "hello",
        "agent_profile": "operations",
        "principal": "user_1",
        "workspace_id": "ws_1",
        "company_id": "test_company_1",
        "delegation_token": "fake-token",
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_execute_run_task_fails_gracefully_when_registry_not_seeded():
    plane = _plane()
    stream_mgr = CosaEventStreamManager()

    await execute_run_task(plane, stream_mgr, _payload())

    messages = await plane.conversation_repository.list_messages("conv_1")
    assert any(m.status == "failed" for m in messages)


@pytest.mark.asyncio
async def test_execute_run_task_resolves_exact_spec_after_seeding():
    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
    )
    stream_mgr = CosaEventStreamManager()

    await execute_run_task(plane, stream_mgr, _payload())

    messages = await plane.conversation_repository.list_messages("conv_1")
    assert not any(m.status == "failed" for m in messages)
    assert any(m.role == "assistant" and m.status == "completed" for m in messages)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("agent_profile", "expected_spec_id"),
    [
        ("operations", "cosa.agents.operations"),
        ("finance", "cosa.agents.finance"),
        ("marketing", "cosa.agents.marketing"),
        # Default thật hiện tại của Flutter (chat_controller.dart
        # createNewConversation() không truyền agentProfile) — phải tiếp tục
        # map sang Operations, không được coi là "unknown".
        ("founder_assistant", "cosa.agents.operations"),
        # Profile lạ chưa từng dùng — fallback an toàn về Operations thay vì
        # âm thầm rơi vào đó qua so khớp chuỗi "finance" in agent_profile như
        # trước đây (bug: "marketing" cũng rơi vào Operations do "finance"
        # not in "marketing").
        ("some_never_used_profile", "cosa.agents.operations"),
    ],
)
async def test_execute_run_task_dispatches_correct_spec_per_agent_profile(
    agent_profile: str, expected_spec_id: str
) -> None:
    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
    )
    stream_mgr = CosaEventStreamManager()

    await execute_run_task(
        plane,
        stream_mgr,
        _payload(agent_profile=agent_profile),
    )

    run = await plane.run_repository.get_run("run_handler_test_1")
    assert run is not None
    assert run.root_executable_id == expected_spec_id


class _SpyComplianceResolver:
    """Ghi lại `RunRequest` thật đã được truyền vào
    `ComplianceResolver.resolve_for_run` (Task 4) — dùng để chứng minh Task 5
    forward đúng `direct_message_data_access` (server-generated
    source_ref/source_hash, không phải nội dung message thô) từ payload đã
    schedule vào `RunRequest.metadata`, mà không cần mock lại toàn bộ resolver
    thật."""

    def __init__(self, inner) -> None:
        self._inner = inner
        self.request = None

    async def resolve_for_run(self, request, spec):
        self.request = request
        return await self._inner.resolve_for_run(request, spec)


async def _all_client_visible_text(plane, *, run_id: str, conversation_id: str) -> str:
    """Gom mọi text mà client CÓ THỂ nhìn thấy — conversation message content
    + payload của mọi stream event đã emit cho run này. Dùng để chứng minh
    lỗi runtime không bị leak ra ngoài (không chỉ kiểm tra 1 chỗ)."""
    messages = await plane.conversation_repository.list_messages(conversation_id)
    events = await plane.stream_event_repository.list_since(run_id)
    parts = [m.content or "" for m in messages]
    parts.extend(str(event.payload) for event in events)
    return " ".join(parts)


@pytest.mark.asyncio
async def test_unexpected_worker_error_is_not_sent_to_client():
    """Task 6 — lỗi runtime bất ngờ (vd. exception nội bộ có thể chứa pin/
    secret) KHÔNG được forward nguyên văn cho client qua message hay stream
    event; chỉ log server-side kèm run_id."""
    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
    )
    stream_mgr = CosaEventStreamManager()
    plane.kernel.run = AsyncMock(side_effect=RuntimeError("internal-pin-and-secret"))

    payload = _payload()
    await execute_run_task(plane, stream_mgr, payload)

    visible_text = await _all_client_visible_text(
        plane, run_id=payload["run_id"], conversation_id=payload["conversation_id"]
    )
    assert "internal-pin-and-secret" not in visible_text
    assert "internal_error" in visible_text


@pytest.mark.asyncio
async def test_tenant_policy_error_is_not_sent_to_client():
    """Task 6 review finding — CosaTenantPolicyError (thất bại resolve
    PolicySnapshot từ Company) trước đây bị interpolate nguyên văn `{exc}`
    vào message/event client-facing. Giờ chỉ mã lỗi ổn định
    `policy_snapshot_unavailable` được forward, exception thật chỉ log
    server-side."""
    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
    )
    stream_mgr = CosaEventStreamManager()
    secret_detail = "internal-policy-store-dsn-leak-detail"
    plane.tenant_policy_client.get_snapshot = AsyncMock(
        side_effect=CosaTenantPolicyError(secret_detail)
    )

    payload = _payload()
    await execute_run_task(plane, stream_mgr, payload)

    visible_text = await _all_client_visible_text(
        plane, run_id=payload["run_id"], conversation_id=payload["conversation_id"]
    )
    assert secret_detail not in visible_text
    assert "policy_snapshot_unavailable" in visible_text


@pytest.mark.asyncio
async def test_resume_tenant_policy_error_is_not_sent_to_client():
    """Final-review Finding 2 — second, structurally identical
    `CosaTenantPolicyError` branch in `execute_resume_task` (resume-after-
    approval flow) had the same raw-exception-interpolation bug as the
    already-fixed branch in `_execute_run_task_inner`. Only the stable code
    `policy_snapshot_unavailable_on_resume` may reach the client."""
    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
    )
    stream_mgr = CosaEventStreamManager()
    secret_detail = "internal-policy-store-dsn-leak-detail-resume"
    plane.tenant_policy_client.get_snapshot = AsyncMock(
        side_effect=CosaTenantPolicyError(secret_detail)
    )

    payload = {
        "run_id": "run_resume_test_1",
        "checkpoint_ref": "checkpoint_1",
        "conversation_id": "conv_1",
        "workspace_id": "ws_1",
        "agent_profile": "operations",
        "delegation_token": "fake-token",
    }
    await execute_resume_task(plane, stream_mgr, payload)

    visible_text = await _all_client_visible_text(
        plane, run_id=payload["run_id"], conversation_id=payload["conversation_id"]
    )
    assert secret_detail not in visible_text
    assert "policy_snapshot_unavailable_on_resume" in visible_text


@pytest.mark.asyncio
async def test_spec_resolution_error_is_not_sent_to_client():
    """Task 6 review finding — SpecDependencyMissingError (registry chưa
    seed / dependency drift) trước đây leak nguyên văn exception — đúng ví dụ
    "internal pinned-skill detail" constraint plan nêu — ra client. Giờ chỉ
    mã lỗi ổn định `spec_resolution_unavailable` được forward."""
    plane = _plane()
    stream_mgr = CosaEventStreamManager()
    secret_detail = "pinned-skill-internal-fingerprint-detail"

    async def _raise_missing(*_args, **_kwargs):
        raise SpecDependencyMissingError("prompt", secret_detail, "v1", "not_found")

    with patch(
        "apps.cosa.worker.handlers.SpecResolver.resolve_agent_spec_dependencies",
        _raise_missing,
    ):
        payload = _payload()
        await execute_run_task(plane, stream_mgr, payload)

    visible_text = await _all_client_visible_text(
        plane, run_id=payload["run_id"], conversation_id=payload["conversation_id"]
    )
    assert secret_detail not in visible_text
    assert "spec_resolution_unavailable" in visible_text


@pytest.mark.asyncio
async def test_worker_forwards_server_provenance():
    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
    )
    stream_mgr = CosaEventStreamManager()

    resolver = _SpyComplianceResolver(plane.compliance_resolver)
    plane.compliance_resolver = resolver

    payload = _payload(
        direct_message_data_access={
            "categories": ["NON_PERSONAL"],
            "subject_reference": None,
            "source_ref": "conversation_message:msg_123",
            "source_hash": "deadbeef",
        }
    )

    await execute_run_task(plane, stream_mgr, payload)

    assert resolver.request is not None
    context = resolver.request.metadata["direct_message_data_access"]
    assert context["source_ref"] == "conversation_message:msg_123"
    assert context["source_hash"] != "plan next quarter"
    assert "content" not in context
