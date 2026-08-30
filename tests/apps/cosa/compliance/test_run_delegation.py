"""Task 5 — kiểm chứng end-to-end: delegation/compliance state được carry
xuyên suốt 1 real agent run của apps/cosa worker.

Trước Task 5:
- `ComplianceResolver.resolve_for_run` được gọi ẩn bên trong
  `RealOpenAIAgentsSDKKernel.run()` — SAU KHI worker đã handoff cho kernel,
  không có cách nào chặn 1 run trước khi tốn 1 lệnh gọi kernel.
- `InvocationContext.delegation_identity` tồn tại nhưng chưa ai gán.
- Company capability calls (CompanyServiceClient) không mang Authorization
  header nào — không forward delegation.

Test này xác nhận:
1. Worker resolve compliance TRƯỚC khi gọi `plane.kernel.run()`, với đúng
   run_id của run đang thực thi.
2. Run bị từ chối (không bao giờ gọi kernel) khi resolver raise
   ComplianceDenied hoặc plane không cấu hình compliance_resolver — không
   fallback về "chạy tiếp không compliance".
3. Không có raw delegation token nào rò rỉ vào conversation message hay
   stream event payload (chỉ reason code, không phải message thô).
4. `InvocationContext` nhận đúng `delegation_identity` (fingerprint an toàn,
   không phải raw token) và loại raw token khỏi `.metadata`.
"""

from __future__ import annotations

from typing import Any

import pytest
from agent.conversations.repository import InMemoryConversationRepository
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel
from agent_testkit.fake_sdk_model import FakeSDKModel

from apps.cosa.agents.seed import seed_cosa_agent_specs
from apps.cosa.agents.specs import COSA_OPERATIONS_AGENT_SPEC
from apps.cosa.api.event_stream import CosaEventStreamManager
from apps.cosa.compliance.contracts import ComplianceDenied
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from apps.cosa.worker.handlers import execute_run_task
from tests.apps.cosa.policy_test_helpers import fake_active_tenant_policy_client

_RAW_SECRET_TOKEN = "eyJ.super-secret-company-delegation-jwt.body"  # nosec - test fixture chuỗi giả


class FakeComplianceResolver:
    """Spy resolver — thay hoàn toàn resolver thật để test kiểm soát chính
    xác request/spec worker truyền xuống và giá trị trả về, không phụ thuộc
    hành vi mint JWT thật."""

    def __init__(
        self,
        *,
        raise_denied: ComplianceDenied | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> None:
        self.calls: list[tuple[Any, Any]] = []
        self._raise_denied = raise_denied
        self._extra_metadata = extra_metadata or {}

    async def resolve_for_run(self, request, spec):
        self.calls.append((request, spec))
        if self._raise_denied:
            raise self._raise_denied
        base = {
            "compliance_snapshot": {"status": "APPROVED_FOR_USE", "mode": "ADVISORY_ONLY"},
            "compliance_snapshot_ref": "sha256:fake",
            "compliance_snapshot_version": "v1",
            "company_delegation_ref": "jti-fake-0001",
            "_company_delegation_token": _RAW_SECRET_TOKEN,
        }
        base.update(self._extra_metadata)
        return base


def _plane():
    return build_cosa_agent_plane(
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
        "run_id": "run_delegation_test_1",
        "conversation_id": "conv_1",
        "user_prompt": "hello",
        "agent_profile": "operations",
        "principal": "user_1",
        "workspace_id": "ws_1",
        "delegation_token": "fake-policy-token",
    }
    base.update(overrides)
    return base


async def _all_event_payload_text(plane, run_id: str) -> str:
    events = await plane.stream_event_repository.list_since_for_conversation(
        conversation_id="conv_1"
    )
    return " ".join(str(ev.payload) for ev in events if ev.run_id == run_id)


@pytest.mark.asyncio
async def test_worker_resolves_compliance_before_kernel_run_with_bound_run_id():
    plane = _plane()
    await seed_cosa_agent_specs(plane.spec_registry)
    fake_resolver = FakeComplianceResolver()
    plane.compliance_resolver = fake_resolver

    kernel_run_calls: list[Any] = []
    original_run = plane.kernel.run

    async def _spy_run(request, spec):
        kernel_run_calls.append(request)
        return await original_run(request, spec)

    plane.kernel.run = _spy_run  # type: ignore[method-assign]

    stream_mgr = CosaEventStreamManager()
    payload = _payload()
    await execute_run_task(plane, stream_mgr, payload)

    # 1. Resolver được gọi đúng 1 lần, TRƯỚC kernel.run, với đúng run_id.
    assert len(fake_resolver.calls) == 1
    resolved_request, resolved_spec = fake_resolver.calls[0]
    assert resolved_request.run_id == payload["run_id"]
    assert resolved_spec.id == COSA_OPERATIONS_AGENT_SPEC.id

    # 2. kernel.run được gọi SAU compliance resolve, với metadata đã merge.
    assert len(kernel_run_calls) == 1
    kernel_request = kernel_run_calls[0]
    assert kernel_request.metadata["company_delegation_ref"] == "jti-fake-0001"
    assert kernel_request.metadata["compliance_snapshot_ref"] == "sha256:fake"

    # 3. Raw token không bao giờ rò vào event/audit payload.
    all_events_text = await _all_event_payload_text(plane, payload["run_id"])
    assert _RAW_SECRET_TOKEN not in all_events_text

    messages = await plane.conversation_repository.list_messages("conv_1")
    for m in messages:
        assert _RAW_SECRET_TOKEN not in (m.content or "")


@pytest.mark.asyncio
async def test_run_rejected_when_compliance_denied_kernel_never_called():
    plane = _plane()
    await seed_cosa_agent_specs(plane.spec_registry)
    fake_resolver = FakeComplianceResolver(
        raise_denied=ComplianceDenied("APPROVAL_INCOMPLETE_OR_EXPIRED", "leaked-secret-detail-xyz")
    )
    plane.compliance_resolver = fake_resolver

    kernel_run_calls: list[Any] = []
    original_run = plane.kernel.run

    async def _spy_run(request, spec):
        kernel_run_calls.append(request)
        return await original_run(request, spec)

    plane.kernel.run = _spy_run  # type: ignore[method-assign]

    stream_mgr = CosaEventStreamManager()
    payload = _payload(run_id="run_delegation_test_denied")
    await execute_run_task(plane, stream_mgr, payload)

    # kernel.run KHÔNG BAO GIỜ được gọi khi compliance denied — không có
    # đường "chạy tiếp không compliance".
    assert kernel_run_calls == []

    events = await plane.stream_event_repository.list_since_for_conversation(
        conversation_id="conv_1"
    )
    failed_events = [e for e in events if e.event_type == "run.failed"]
    assert len(failed_events) == 1
    assert failed_events[0].payload["reason_code"] == "APPROVAL_INCOMPLETE_OR_EXPIRED"

    all_events_text = await _all_event_payload_text(plane, payload["run_id"])
    assert "leaked-secret-detail-xyz" not in all_events_text


@pytest.mark.asyncio
async def test_run_rejected_when_compliance_resolver_not_configured():
    plane = _plane()
    await seed_cosa_agent_specs(plane.spec_registry)
    plane.compliance_resolver = None

    kernel_run_calls: list[Any] = []
    original_run = plane.kernel.run

    async def _spy_run(request, spec):
        kernel_run_calls.append(request)
        return await original_run(request, spec)

    plane.kernel.run = _spy_run  # type: ignore[method-assign]

    stream_mgr = CosaEventStreamManager()
    payload = _payload(run_id="run_delegation_test_no_resolver")
    await execute_run_task(plane, stream_mgr, payload)

    assert kernel_run_calls == []
    events = await plane.stream_event_repository.list_since_for_conversation(
        conversation_id="conv_1"
    )
    failed_events = [e for e in events if e.event_type == "run.failed"]
    assert len(failed_events) == 1
    assert failed_events[0].payload["error"] == "compliance_resolver_unavailable"


@pytest.mark.asyncio
async def test_kernel_populates_delegation_identity_and_strips_raw_token_from_context():
    """Kernel-level: `_execute_tool` phải gán `InvocationContext.delegation_identity`
    từ `company_delegation_ref` (fingerprint an toàn), loại bỏ hoàn toàn
    `_company_delegation_token` khỏi `InvocationContext.metadata`, và dựng
    header Company chỉ từ InvocationContext — bỏ qua mọi khoá "authorization"
    do model/tool argument cố tình gửi lên."""
    captured_contexts: list[Any] = []
    captured_headers: list[dict[str, str]] = []

    async def _capability_executor(tool_name, args, inv_ctx):
        captured_contexts.append(inv_ctx)
        from agent.capabilities.outbound_headers import get_outbound_headers

        captured_headers.append(get_outbound_headers())
        return {"ok": True}

    kernel = RealOpenAIAgentsSDKKernel(
        model=FakeSDKModel(),
        capability_executor=_capability_executor,
    )

    context = {
        "workspace_id": "ws_1",
        "principal": "user_1",
        "company_delegation_ref": "jti-fake-9999",
        "_company_delegation_token": _RAW_SECRET_TOKEN,
        # Kẻ tấn công qua model/tool args cố gắng tự set Authorization —
        # phải bị bỏ qua hoàn toàn vì header chỉ dựng từ InvocationContext.
        "authorization": "Bearer attacker-supplied-token",
    }

    await kernel._execute_tool(
        "operations.task.list",
        {"authorization": "Bearer attacker-from-args"},
        run_id="run_ctx_test",
        tool_call_id="call_1",
        context=context,
    )

    assert len(captured_contexts) == 1
    inv_ctx = captured_contexts[0]
    assert inv_ctx.delegation_identity == "jti-fake-9999"
    assert "_company_delegation_token" not in inv_ctx.metadata

    assert len(captured_headers) == 1
    headers = captured_headers[0]
    assert headers["Authorization"] == f"Bearer {_RAW_SECRET_TOKEN}"
    assert headers["X-Workspace-Id"] == "ws_1"
    assert headers["X-COSA-Run-Id"] == "run_ctx_test"
    assert headers["X-COSA-Capability-Id"] == "operations.task.list"
    # Header KHÔNG được xây từ tool args — không có dấu vết nào của
    # "attacker-supplied-token"/"attacker-from-args" trong header thật.
    assert "attacker" not in headers["Authorization"]

    # Ambient header phải được reset sau khi tool call kết thúc — không rò
    # sang lệnh gọi Company khác chạy sau đó ngoài phạm vi tool call này.
    from agent.capabilities.outbound_headers import get_outbound_headers

    assert get_outbound_headers() == {}


@pytest.mark.asyncio
async def test_worker_passes_bound_delegation_to_snapshot_and_capability_clients(monkeypatch):
    """Step 1 & Step 4: Worker thực thi scheduled run mang delegation:
    1. Snapshot / resolver nhận đúng run_id bound theo run.
    2. Company capability client (CompanyServiceClient) gửi outbound headers
       dựng từ InvocationContext: X-Workspace-Id, X-COSA-Run-Id,
       X-COSA-Capability-Id, Authorization: Bearer <delegation_token>.
    3. Raw token / 'Bearer ' KHÔNG BAO GIỜ xuất hiện trong stream events hay messages.
    """
    import httpx
    from agent_testkit.fake_sdk_model import text_response, tool_call_response
    from apps.cosa.capabilities.client import CompanyServiceClient

    plane = _plane()
    await seed_cosa_agent_specs(plane.spec_registry)
    fake_resolver = FakeComplianceResolver()
    plane.compliance_resolver = fake_resolver

    company_client_calls: list[dict[str, Any]] = []

    async def fake_httpx_send(client_self, request, **kwargs):
        company_client_calls.append({
            "url": str(request.url),
            "headers": dict(request.headers),
        })
        return httpx.Response(200, json={"tasks": []}, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "send", fake_httpx_send)

    async def _capability_executor(tool_name, args, inv_ctx):
        company_client = CompanyServiceClient(base_url="http://company.internal")
        await company_client.list_tasks(workspace_id=inv_ctx.workspace_id)
        return {"tasks": []}

    plane.kernel._capability_executor = _capability_executor

    fake_model = FakeSDKModel(
        responses=[
            tool_call_response("call_1", "operations.task.list", "{}"),
            text_response("Task list retrieved successfully."),
        ]
    )
    plane.kernel._model = fake_model

    stream_mgr = CosaEventStreamManager()
    payload = _payload(run_id="run_bound_delegation_e2e")
    await execute_run_task(plane, stream_mgr, payload)

    # 1. Snapshot / resolver nhận đúng run_id bound
    assert len(fake_resolver.calls) == 1
    req, spec = fake_resolver.calls[0]
    assert req.run_id == "run_bound_delegation_e2e"

    # 2. Company capability client forwarded đúng các headers từ InvocationContext
    assert len(company_client_calls) == 1
    call_headers = company_client_calls[0]["headers"]
    assert call_headers["x-workspace-id"] == "ws_1"
    assert call_headers["x-cosa-run-id"] == "run_bound_delegation_e2e"
    assert call_headers["x-cosa-capability-id"] == "operations.task.list"
    assert call_headers["authorization"] == f"Bearer {_RAW_SECRET_TOKEN}"

    # 3. Raw bearer token never appears in serialized run stream events or messages
    all_events_text = await _all_event_payload_text(plane, "run_bound_delegation_e2e")
    assert "Bearer " not in all_events_text
    assert _RAW_SECRET_TOKEN not in all_events_text

    messages = await plane.conversation_repository.list_messages("conv_1")
    for m in messages:
        assert "Bearer " not in (m.content or "")
        assert _RAW_SECRET_TOKEN not in (m.content or "")


@pytest.mark.asyncio
async def test_worker_rejects_task_missing_delegation_token():
    """Worker rejects a task that lacks delegation token, without calling kernel or tenant policy."""
    plane = _plane()
    await seed_cosa_agent_specs(plane.spec_registry)
    fake_resolver = FakeComplianceResolver()
    plane.compliance_resolver = fake_resolver

    kernel_called = []
    plane.kernel.run = lambda *args, **kwargs: kernel_called.append(True)  # type: ignore[method-assign]

    stream_mgr = CosaEventStreamManager()
    payload = _payload(run_id="run_missing_delegation", delegation_token=None)
    await execute_run_task(plane, stream_mgr, payload)

    assert kernel_called == []
    assert len(fake_resolver.calls) == 0

    events = await plane.stream_event_repository.list_since_for_conversation(
        conversation_id="conv_1"
    )
    failed_events = [e for e in events if e.event_type == "run.failed"]
    assert len(failed_events) == 1
    assert failed_events[0].payload["error"] == "missing_delegation_token"

