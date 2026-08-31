"""E2E thật cho production path AI compliance (Task 10, plan
`2026-08-30-ai-compliance-production-hardening-reconciled.md`).

Audit Critical đã xác nhận: bản trước dùng `make_company_mock_transport()`
(một `httpx.MockTransport` tự viết JSON giả lập response Company) monkeypatch
vào `httpx.AsyncClient.__init__` toàn cục — chính là "fake snapshot client"
plan cấm, chỉ chuyển xuống 1 lớp sâu hơn (fake transport thay vì fake client
object). 35 test chạy trong 0.22s là bằng chứng không có network round trip
thật.

File này gọi HTTP THẬT vào 1 Company service (Encore/TypeScript) THẬT đang
chạy (`encore run`, xem `tests/e2e/conftest.py::real_company_service`), với
dữ liệu THẬT được seed qua đúng service function governance thật (không
insert tắt qua HTTP giả). Không còn `httpx.MockTransport`, không còn
monkeypatch `httpx.AsyncClient.__init__` ở bất kỳ đâu trong file này.

Phát hiện + sửa trong lúc build lại test này bằng HTTP thật (ghi chi tiết
trong task-10-report.md): `POST /finance-legal/ai-compliance/resolve-data-use`
trước đây CHỈ xác thực qua `requireWorkspaceAccess` (session người dùng thật)
— nhưng caller thật duy nhất của route (`CosaDataModelGate`/
`AiComplianceClient.resolve_data_use`, gọi từ runtime kernel) luôn gửi
delegation JWT COSA→Company, nên route luôn 401 trên đường thật (gap phát
hiện lần đầu khi test này chạy round-trip HTTP thật — route đó trước nay
chưa từng được gọi qua HTTP thật trong test nào). Đã sửa: route giờ chấp
nhận delegation JWT hợp lệ trước (`verifyCosaDelegationForCapability`, xem
`services/company/shared/auth/cosa-delegation.service.ts`), rơi về session
người dùng nếu không áp dụng được. Các test bên dưới ("model mismatch",
"revoked authorization") vì vậy verify được round-trip đầy đủ qua HTTP thật
với delegation JWT thật — không còn giới hạn nào ở route này.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt as _pyjwt
import pytest
from agent.artifacts import InMemoryArtifactRepository
from agent.contracts.run import RunRequest, RunResult, RunStatus
from agent.contracts.spec import AgentSpec
from agent.conversations.repository import InMemoryConversationRepository
from agent.coordination.scheduler import RunScheduler
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.leases import RunLeaseManager
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel
from agent_testkit.fake_sdk_model import FakeSDKModel, text_response
from fastapi.testclient import TestClient

from apps.cosa.agents.seed import seed_cosa_runtime_specs
from apps.cosa.api.app import create_cosa_app
from apps.cosa.auth.jwt import mint_company_delegation
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.compliance import AiComplianceClient, ComplianceResolver
from apps.cosa.compliance.contracts import (
    AiComplianceUnavailable,
    ComplianceDenied,
)
from apps.cosa.compliance.data_access_claim import DataAccessClaim
from apps.cosa.compliance.data_model_gate import CosaDataModelGate
from apps.cosa.composition.agent_plane import CosaAgentPlane, build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity
from tests.apps.cosa.policy_test_helpers import fake_active_tenant_policy_client
from tests.apps.cosa.worker_test_helpers import drain_worker_queue
from tests.e2e.conftest import CompanyServiceHandle

# system_key CỐ ĐỊNH khớp `COSA_OPERATIONS_AGENT_SPEC.id` sản xuất thật
# (apps/cosa/agents/specs.py) — 2 test dưới đây (`test_approved_direct_
# business_input_reaches_model_once`, `test_withdrawn_personal_authorization_
# never_reaches_model`) đi qua ĐÚNG route HTTP thật `POST /agent/
# conversations/{id}/messages`, nên `SpecResolver` trong worker luôn dùng
# spec cố định này, không phải 1 systemKey random do test tự đặt (khác các
# test phía trên vốn tự dựng `AgentSpec(id=seeded["systemKey"], ...)`).
_PRODUCTION_OPERATIONS_SYSTEM_KEY = "cosa.agents.operations"
_PRODUCTION_OPERATIONS_EXTRA_CAPABILITIES = ["operations.task.read"]

# Cùng dev-default secret với
# `apps/cosa/auth/jwt.py::_COMPANY_DELEGATION_DEV_DEFAULT_SECRET` /
# `services/company/shared/auth/cosa-delegation.service.ts::DEV_DELEGATION_SECRET`
# — dùng để tự dựng token MALFORMED (thiếu/hết hạn/sai audience) cho ma trận
# âm. Chỉ hợp lệ khi ENVIRONMENT không phải staging/production (mặc định
# trong test).
_DEV_DELEGATION_SECRET = "cosa-company-delegation-dev-secret-change-in-prod"


async def _seed(handle: CompanyServiceHandle, scenario: str) -> dict[str, Any]:
    """Seed dữ liệu AI compliance THẬT qua endpoint E2E-only (chính nó gọi
    đúng service function governance thật — xem
    ai-compliance-e2e-seed.service.ts). KHÔNG phải mock: đây là 1 request
    HTTP thật ghi dữ liệu thật vào Postgres thật."""
    import httpx as _httpx

    async with _httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{handle.base_url}/finance-legal/ai-compliance/_e2e/seed",
            json={"scenario": scenario},
        )
    resp.raise_for_status()
    return resp.json()


async def _seed_for_direct_message_pipeline(
    handle: CompanyServiceHandle, scenario: str
) -> dict[str, Any]:
    """Như `_seed()` nhưng ép `system_key` khớp `COSA_OPERATIONS_AGENT_SPEC.id`
    sản xuất thật + bind thêm capability `operations.task.read` mà spec đó
    khai báo — bắt buộc cho 2 test round-trip HTTP đầy đủ (route → worker →
    SpecResolver → ComplianceResolver) bên dưới, vì `SpecResolver` trong
    worker luôn dùng spec cố định này, không thể tham số hoá theo test (xem
    `services/company/finance-legal/services/ai-compliance-e2e-seed.service.ts::
    E2eSeedOptions`)."""
    import httpx as _httpx

    async with _httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{handle.base_url}/finance-legal/ai-compliance/_e2e/seed",
            json={
                "scenario": scenario,
                "systemKey": _PRODUCTION_OPERATIONS_SYSTEM_KEY,
                "additionalBoundCapabilityIds": _PRODUCTION_OPERATIONS_EXTRA_CAPABILITIES,
            },
        )
    resp.raise_for_status()
    return resp.json()


async def _build_real_pipeline_plane(base_url: str, fake_model: FakeSDKModel) -> CosaAgentPlane:
    """Dựng 1 `CosaAgentPlane` thật (đúng `build_cosa_agent_plane()` sản
    xuất, KHÔNG viết lại composition) cho 2 test round-trip HTTP đầy đủ bên
    dưới — repository/scheduler/lease in-memory (test không cần durable qua
    restart), nhưng `company_client` trỏ THẬT vào `real_company_service`.

    `build_cosa_agent_plane()` tự chuyển sang `AiComplianceClient` MOCK khi
    `model=` được truyền tay (tín hiệu "đây là test" — xem
    `apps/cosa/composition/agent_plane.py::use_mock_compliance_client`), hợp
    lý cho phần lớn test không kiểm thử compliance nhưng SAI ở đây vì mục
    đích của 2 test này chính là chứng minh Company THẬT allow/deny qua HTTP
    thật. Ghi đè `plane.compliance_resolver` bằng bản thật trỏ vào
    `base_url` NGAY SAU khi build — `model_input_guard` (`CosaDataModelGate`)
    không bị ảnh hưởng bởi nhánh mock đó (nó luôn dùng `company_client` thật
    truyền vào bên dưới), nên không cần ghi đè lại."""
    plane = build_cosa_agent_plane(
        company_client=CompanyServiceClient(base_url=base_url),
        tenant_policy_client=fake_active_tenant_policy_client(),
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        artifact_repository=InMemoryArtifactRepository(),
        model=fake_model,
    )
    plane.compliance_resolver = ComplianceResolver(AiComplianceClient(base_url=base_url))
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
    )
    return plane


def _build_kernel(
    base_url: str, fake_model: FakeSDKModel
) -> tuple[RealOpenAIAgentsSDKKernel, AiComplianceClient]:
    client = AiComplianceClient(base_url=base_url)
    resolver = ComplianceResolver(client=client)
    gate = CosaDataModelGate(client=client)
    kernel = RealOpenAIAgentsSDKKernel(
        model=fake_model,
        compliance_resolver=resolver,
        model_input_guard=gate,
    )
    return kernel, client


async def _submit_run(
    kernel: RealOpenAIAgentsSDKKernel,
    *,
    workspace_id: str,
    system_key: str,
    capability_ids: list[str],
    claim: DataAccessClaim | None = None,
    prompt: str = "Plan tasks for current quarter",
) -> RunResult:
    spec = AgentSpec(
        id=system_key,
        instructions="Advisory only",
        capability_refs=capability_ids,
        model_input_capability_ref="model.input.direct-user-message",
    )
    metadata: dict[str, Any] = {"capability_ids": capability_ids}
    if claim is not None:
        metadata["data_access_claim"] = claim
    req = RunRequest(
        root_executable_ref=f"agent:{system_key}",
        workspace_id=workspace_id,
        principal="founder_1",
        input={"prompt": prompt},
        metadata=metadata,
    )
    try:
        return await kernel.run(req, spec)
    except ComplianceDenied:
        return RunResult(run_id=req.run_id or "run", status=RunStatus.FAILED)


@pytest.mark.asyncio
async def test_approved_run_reaches_company_then_model_once(
    real_company_service: CompanyServiceHandle,
) -> None:
    seeded = await _seed(real_company_service, "approved")
    fake_model = FakeSDKModel(responses=[text_response("Advisory report generated successfully.")])
    kernel, _client = _build_kernel(real_company_service.base_url, fake_model)

    claim = DataAccessClaim(
        workspace_id=seeded["workspaceId"],
        deployment_id=seeded["deploymentId"],
        capability_id="operations.task.list",
        source_ref="doc://quarter/q3",
        source_hash="sha256:source123",
        categories=frozenset(["BUSINESS_CONFIDENTIAL"]),
        purpose_id="advisory",
        provider_key="deepseek",
        model_key="deepseek-chat",
    )

    result = await _submit_run(
        kernel,
        workspace_id=seeded["workspaceId"],
        system_key=seeded["systemKey"],
        capability_ids=["operations.task.list"],
        claim=claim,
    )

    assert result.status == RunStatus.COMPLETED
    assert fake_model.call_count == 1


@pytest.mark.asyncio
async def test_suspended_deployment_never_reaches_model(
    real_company_service: CompanyServiceHandle,
) -> None:
    seeded = await _seed(real_company_service, "suspended")
    fake_model = FakeSDKModel(responses=[text_response("unreachable")])
    kernel, _client = _build_kernel(real_company_service.base_url, fake_model)

    result = await _submit_run(
        kernel,
        workspace_id=seeded["workspaceId"],
        system_key=seeded["systemKey"],
        capability_ids=["operations.task.list"],
    )

    assert result.status == RunStatus.FAILED
    assert fake_model.call_count == 0


@pytest.mark.asyncio
async def test_cross_workspace_run_never_reaches_model(
    real_company_service: CompanyServiceHandle,
) -> None:
    """Ma trận âm: workspace khác gọi vào systemKey đã APPROVED_FOR_USE ở
    workspace khác — deployment thật tồn tại (không phải "chưa từng seed"),
    nhưng thuộc workspace khác, nên phải fail-closed 404 ở tầng Company."""
    seeded = await _seed(real_company_service, "approved")
    foreign_workspace_id = str(int(seeded["workspaceId"]) + 1)
    fake_model = FakeSDKModel(responses=[text_response("unreachable")])
    kernel, _client = _build_kernel(real_company_service.base_url, fake_model)

    result = await _submit_run(
        kernel,
        workspace_id=foreign_workspace_id,
        system_key=seeded["systemKey"],
        capability_ids=["operations.task.list"],
    )

    assert result.status == RunStatus.FAILED
    assert fake_model.call_count == 0


@pytest.mark.asyncio
async def test_unbound_capability_never_reaches_model(
    real_company_service: CompanyServiceHandle,
) -> None:
    seeded = await _seed(real_company_service, "approved")
    fake_model = FakeSDKModel(responses=[text_response("unreachable")])
    kernel, _client = _build_kernel(real_company_service.base_url, fake_model)

    result = await _submit_run(
        kernel,
        workspace_id=seeded["workspaceId"],
        system_key=seeded["systemKey"],
        capability_ids=["operations.unbound.capability"],
    )

    assert result.status == RunStatus.FAILED
    assert fake_model.call_count == 0


@pytest.mark.asyncio
async def test_expired_assessment_never_reaches_model(
    real_company_service: CompanyServiceHandle,
) -> None:
    """Assessment đã APPROVED thật qua service thật, sau đó hết hạn (thời
    gian trôi qua) — xem ai-compliance-e2e-seed.service.ts scenario
    'expired_assessment'. Route runtime phải fail-closed 409
    ASSESSMENT_EXPIRED, không coi approval quá khứ là còn hiệu lực."""
    seeded = await _seed(real_company_service, "expired_assessment")
    fake_model = FakeSDKModel(responses=[text_response("unreachable")])
    kernel, _client = _build_kernel(real_company_service.base_url, fake_model)

    result = await _submit_run(
        kernel,
        workspace_id=seeded["workspaceId"],
        system_key=seeded["systemKey"],
        capability_ids=["operations.task.list"],
    )

    assert result.status == RunStatus.FAILED
    assert fake_model.call_count == 0


@pytest.mark.asyncio
async def test_personal_data_without_subject_reference_never_reaches_model(
    real_company_service: CompanyServiceHandle,
) -> None:
    """Guard này chạy hoàn toàn phía client (CosaDataModelGate) TRƯỚC khi có
    bất kỳ HTTP call nào tới Company — vẫn là hành vi thật (code thật, không
    mock), chỉ không cần round-trip HTTP cho riêng case này."""
    seeded = await _seed(real_company_service, "approved")
    fake_model = FakeSDKModel(responses=[text_response("unreachable")])
    kernel, _client = _build_kernel(real_company_service.base_url, fake_model)

    claim_personal = DataAccessClaim(
        workspace_id=seeded["workspaceId"],
        deployment_id=seeded["deploymentId"],
        capability_id="operations.task.list",
        source_ref="doc://customer/1",
        source_hash="sha256:cust1",
        categories=frozenset(["PERSONAL"]),
        purpose_id="advisory",
        subject_reference=None,
        provider_key="deepseek",
        model_key="deepseek-chat",
    )

    result = await _submit_run(
        kernel,
        workspace_id=seeded["workspaceId"],
        system_key=seeded["systemKey"],
        capability_ids=["operations.task.list"],
        claim=claim_personal,
    )

    assert result.status == RunStatus.FAILED
    assert fake_model.call_count == 0


@pytest.mark.asyncio
async def test_model_mismatch_claim_never_reaches_model(
    real_company_service: CompanyServiceHandle,
) -> None:
    """Round-trip đầy đủ qua `resolve-data-use` thật (delegation JWT thật,
    xem fix ở đầu file) — Company trả `MODEL_NOT_APPROVED` thật vì
    `model_key` không khớp provider profile đã seed, kernel fail-closed
    trước khi gọi model."""
    seeded = await _seed(real_company_service, "approved")
    fake_model = FakeSDKModel(responses=[text_response("unreachable")])
    kernel, _client = _build_kernel(real_company_service.base_url, fake_model)

    claim_mismatch = DataAccessClaim(
        workspace_id=seeded["workspaceId"],
        deployment_id=seeded["deploymentId"],
        capability_id="operations.task.list",
        source_ref="doc://test/1",
        source_hash="sha256:abc",
        categories=frozenset(["BUSINESS_CONFIDENTIAL"]),
        purpose_id="advisory",
        provider_key="deepseek",
        model_key="unapproved-model-coder",
    )

    result = await _submit_run(
        kernel,
        workspace_id=seeded["workspaceId"],
        system_key=seeded["systemKey"],
        capability_ids=["operations.task.list"],
        claim=claim_mismatch,
    )

    assert result.status == RunStatus.FAILED
    assert fake_model.call_count == 0


@pytest.mark.asyncio
async def test_revoked_authorization_denies_personal_data_use(
    real_company_service: CompanyServiceHandle,
) -> None:
    """Round-trip đầy đủ qua `resolve-data-use` thật: seed thật grant rồi
    withdraw thật 1 `data_processing_authorization` cho `subjectReference`,
    sau đó mint đúng delegation JWT thật mà `ComplianceResolver` dùng trong
    production (`mint_company_delegation`) và gọi
    `AiComplianceClient.resolve_data_use` trực tiếp — Company phải trả
    `allowed=False, denialCode=PROCESSING_AUTHORIZATION_WITHDRAWN` thật, qua
    HTTP thật, không giả lập."""
    seeded = await _seed(real_company_service, "revoked_authorization")
    assert seeded.get("authorizationId")
    assert seeded.get("subjectReference")

    client = AiComplianceClient(base_url=real_company_service.base_url)
    delegation_token = mint_company_delegation(
        sub="founder_1",
        workspace_id=seeded["workspaceId"],
        run_id="run_revoked_auth",
        capability_ids=["operations.task.list"],
    )

    decision = await client.resolve_data_use(
        workspace_id=seeded["workspaceId"],
        deployment_id=seeded["deploymentId"],
        capability_id="operations.task.list",
        purpose_id="advisory",
        data_categories=["PERSONAL"],
        provider_key="deepseek",
        model_key="deepseek-chat",
        subject_reference=seeded["subjectReference"],
        delegation_token=delegation_token,
    )

    assert decision.allowed is False
    assert decision.denial_code == "PROCESSING_AUTHORIZATION_WITHDRAWN"


@pytest.mark.asyncio
async def test_delegation_missing_bearer_prefix_rejected(
    real_company_service: CompanyServiceHandle,
) -> None:
    seeded = await _seed(real_company_service, "approved")
    client = AiComplianceClient(base_url=real_company_service.base_url)

    with pytest.raises(AiComplianceUnavailable) as exc_info:
        await client.resolve_snapshot(
            workspace_id=seeded["workspaceId"],
            run_id="run_missing_bearer",
            system_key=seeded["systemKey"],
            capability_ids=["operations.task.list"],
            delegation_token="not-a-bearer-token-just-garbage",
        )
    # AiComplianceClient gửi "Bearer <delegation_token>" — token không hợp lệ
    # sẽ bị Company từ chối 403 (verifyCosaDelegation/extractBearerToken).
    assert exc_info.value.code == "DELEGATION_DENIED"


@pytest.mark.asyncio
async def test_delegation_expired_rejected(real_company_service: CompanyServiceHandle) -> None:
    seeded = await _seed(real_company_service, "approved")
    client = AiComplianceClient(base_url=real_company_service.base_url)

    expired_token = _pyjwt.encode(
        {
            "sub": "founder_1",
            "principal_id": "user:founder_1",
            "workspace_id": seeded["workspaceId"],
            "run_id": "run_expired",
            "capability_ids": ["operations.task.list"],
            "jti": "expired-jti-1",
            "iss": "cosa",
            "aud": "company",
            "exp": int((datetime.now(UTC) - timedelta(minutes=5)).timestamp()),
        },
        _DEV_DELEGATION_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(AiComplianceUnavailable) as exc_info:
        await client.resolve_snapshot(
            workspace_id=seeded["workspaceId"],
            run_id="run_expired",
            system_key=seeded["systemKey"],
            capability_ids=["operations.task.list"],
            delegation_token=expired_token,
        )
    assert exc_info.value.code == "DELEGATION_DENIED"


@pytest.mark.asyncio
async def test_delegation_wrong_audience_rejected(
    real_company_service: CompanyServiceHandle,
) -> None:
    seeded = await _seed(real_company_service, "approved")
    client = AiComplianceClient(base_url=real_company_service.base_url)

    wrong_audience_token = _pyjwt.encode(
        {
            "sub": "founder_1",
            "principal_id": "user:founder_1",
            "workspace_id": seeded["workspaceId"],
            "run_id": "run_wrong_aud",
            "capability_ids": ["operations.task.list"],
            "jti": "wrong-aud-jti-1",
            "iss": "cosa",
            "aud": "not-company",
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
        },
        _DEV_DELEGATION_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(AiComplianceUnavailable) as exc_info:
        await client.resolve_snapshot(
            workspace_id=seeded["workspaceId"],
            run_id="run_wrong_aud",
            system_key=seeded["systemKey"],
            capability_ids=["operations.task.list"],
            delegation_token=wrong_audience_token,
        )
    assert exc_info.value.code == "DELEGATION_DENIED"


@pytest.mark.asyncio
async def test_delegation_wrong_workspace_scope_rejected(
    real_company_service: CompanyServiceHandle,
) -> None:
    """Token hợp lệ (đúng issuer/audience/exp) nhưng scope sang workspace
    khác — verifyCosaDelegation phải so khớp workspace_id claim với header
    X-Workspace-Id thật gửi lên, không chỉ verify chữ ký."""
    seeded = await _seed(real_company_service, "approved")
    client = AiComplianceClient(base_url=real_company_service.base_url)

    other_workspace_token = _pyjwt.encode(
        {
            "sub": "founder_1",
            "principal_id": "user:founder_1",
            "workspace_id": "some-other-workspace-id",
            "run_id": "run_wrong_ws",
            "capability_ids": ["operations.task.list"],
            "jti": "wrong-ws-jti-1",
            "iss": "cosa",
            "aud": "company",
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
        },
        _DEV_DELEGATION_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(AiComplianceUnavailable) as exc_info:
        await client.resolve_snapshot(
            workspace_id=seeded["workspaceId"],
            run_id="run_wrong_ws",
            system_key=seeded["systemKey"],
            capability_ids=["operations.task.list"],
            delegation_token=other_workspace_token,
        )
    assert exc_info.value.code == "DELEGATION_DENIED"


@pytest.mark.asyncio
async def test_approved_direct_business_input_reaches_model_once(
    real_company_service: CompanyServiceHandle,
) -> None:
    """Task 7 (2026-08-30) — round-trip HTTP THẬT hết pipeline sản xuất:
    `POST /agent/conversations/{id}/messages` (Task 5) → durable scheduler →
    worker (`apps/cosa/worker/handlers.py`) → `SpecResolver` (spec cố định
    `COSA_OPERATIONS_AGENT_SPEC`) → `ComplianceResolver.resolve_for_run`
    (Task 4, đọc `direct_message_data_access` từ payload đã forward) →
    Company thật (`resolve-snapshot` + `resolve-data-use`) → `CosaDataModelGate`
    → kernel gọi model giả lập đúng 1 lần.

    Trước Task 4-6, gap thật là: dù từng bước (resolver, gate, route) đã có
    test riêng, CHƯA có test nào tự gửi 1 message qua đúng route HTTP tạo
    message thật rồi chạy hết worker để chứng minh toàn bộ dây chuyền nối
    đúng với nhau bằng Company thật."""
    seeded = await _seed_for_direct_message_pipeline(real_company_service, "approved")
    fake_model = FakeSDKModel(responses=[text_response("Q3 roadmap summary generated.")])
    plane = await _build_real_pipeline_plane(real_company_service.base_url, fake_model)

    app = create_cosa_app(plane=plane)
    override_authenticated_identity(
        app,
        principal_id="user:e2e_direct_msg_approved",
        platform_user_id="e2e_direct_msg_approved",
        workspace_id=seeded["workspaceId"],
    )
    client = TestClient(app)

    conv_res = client.post("/agent/conversations", json={"title": "Direct message E2E — approved"})
    assert conv_res.status_code == 201, conv_res.text
    conversation_id = conv_res.json()["id"]

    msg_res = client.post(
        f"/agent/conversations/{conversation_id}/messages",
        json={
            "content": "Summarize our confidential Q3 roadmap for the founder review.",
            "data_access": {"categories": ["BUSINESS_CONFIDENTIAL"]},
        },
    )
    assert msg_res.status_code == 202, msg_res.text
    run_id = msg_res.json()["run_id"]

    dispatched = await drain_worker_queue(plane)
    assert dispatched == 1

    run_record = await plane.repository.get_scoped_run(
        run_id=run_id, workspace_id=seeded["workspaceId"]
    )
    assert run_record is not None
    assert run_record.status == RunStatus.COMPLETED
    assert fake_model.call_count == 1


@pytest.mark.asyncio
async def test_withdrawn_personal_authorization_never_reaches_model(
    real_company_service: CompanyServiceHandle,
) -> None:
    """Task 7 (2026-08-30) — ma trận âm cùng round-trip HTTP thật: subject đã
    `withdrawProcessingAuthorization` thật ở Company (scenario
    `revoked_authorization`, tái dùng nguyên vẹn) gửi 1 message khai báo
    category `PERSONAL` + đúng `subject_reference` đã bị thu hồi. Company phải
    trả `PROCESSING_AUTHORIZATION_WITHDRAWN` thật qua `resolve-data-use`
    (`CosaDataModelGate.prepare_initial_input`), kernel fail-closed TRƯỚC khi
    gọi model — không phải suy diễn từ đâu khác."""
    seeded = await _seed_for_direct_message_pipeline(real_company_service, "revoked_authorization")
    assert seeded.get("subjectReference")
    fake_model = FakeSDKModel(responses=[text_response("unreachable")])
    plane = await _build_real_pipeline_plane(real_company_service.base_url, fake_model)

    app = create_cosa_app(plane=plane)
    override_authenticated_identity(
        app,
        principal_id="user:e2e_direct_msg_withdrawn",
        platform_user_id="e2e_direct_msg_withdrawn",
        workspace_id=seeded["workspaceId"],
    )
    client = TestClient(app)

    conv_res = client.post("/agent/conversations", json={"title": "Direct message E2E — withdrawn"})
    assert conv_res.status_code == 201, conv_res.text
    conversation_id = conv_res.json()["id"]

    msg_res = client.post(
        f"/agent/conversations/{conversation_id}/messages",
        json={
            "content": "What is this customer's personal billing history?",
            "data_access": {
                "categories": ["PERSONAL"],
                "subject_reference": seeded["subjectReference"],
            },
        },
    )
    assert msg_res.status_code == 202, msg_res.text
    run_id = msg_res.json()["run_id"]

    dispatched = await drain_worker_queue(plane)
    assert dispatched == 1

    run_record = await plane.repository.get_scoped_run(
        run_id=run_id, workspace_id=seeded["workspaceId"]
    )
    assert run_record is not None
    assert run_record.status == RunStatus.FAILED
    assert fake_model.call_count == 0
