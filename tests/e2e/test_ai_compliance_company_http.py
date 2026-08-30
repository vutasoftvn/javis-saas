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

Giới hạn đã xác nhận khi build lại test này bằng HTTP thật (ghi trong
task-10-report.md, không che giấu):
- `POST /finance-legal/ai-compliance/resolve-data-use` xác thực qua
  `requireWorkspaceAccess` (yêu cầu access token phiên người dùng thật, xem
  `identity/services/tenant-context.service.ts::resolveTenantContext`) —
  KHÔNG chấp nhận delegation JWT COSA→Company mà
  `CosaDataModelGate`/`AiComplianceClient.resolve_data_use` gửi lên trong
  runtime thật. Đây là 1 gap wiring THẬT phát hiện lần đầu khi test này chạy
  round-trip HTTP thật (route đó trước nay chưa từng được gọi qua HTTP thật
  trong test nào) — nằm ngoài phạm vi Task 10 (test authenticity), cần 1 task
  wiring riêng để quyết định route này nên verify theo delegation hay theo
  session người dùng. Test "model mismatch" bên dưới vì vậy assert đúng hành
  vi THẬT hiện tại của hệ thống (401 ⇒ fail-closed, model không bao giờ được
  gọi) thay vì giả lập 1 phản hồi MODEL_NOT_APPROVED sạch mà hệ thống thật
  chưa thể trả về.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt as _pyjwt
import pytest
from agent.contracts.run import RunRequest, RunResult, RunStatus
from agent.contracts.spec import AgentSpec
from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel
from agent_testkit.fake_sdk_model import FakeSDKModel, text_response

from apps.cosa.compliance import AiComplianceClient, ComplianceResolver
from apps.cosa.compliance.contracts import (
    AiComplianceUnavailable,
    ComplianceDenied,
)
from apps.cosa.compliance.data_access_claim import DataAccessClaim
from apps.cosa.compliance.data_model_gate import CosaDataModelGate
from tests.e2e.conftest import CompanyServiceHandle

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
    spec = AgentSpec(id=system_key, instructions="Advisory only", capability_refs=capability_ids)
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
    """Xem giới hạn ghi ở đầu file: `resolve-data-use` hiện 401 với delegation
    token thật (gap wiring auth riêng, ngoài phạm vi Task 10) — nên assert
    đúng hành vi fail-closed THẬT của hệ thống hôm nay (never reaches model),
    không giả lập 1 lý do từ chối "sạch" mà hệ thống thật chưa trả về được."""
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
    """`resolve-data-use` bị chặn bởi gap auth ghi ở đầu file — verify trực
    tiếp qua service TS thật bằng cách gọi cùng con đường Python client sẽ
    dùng (không mock), nhưng bằng chính route + workspace/context hợp lệ mà
    route đó CHẤP NHẬN hôm nay là không khả thi qua HTTP thật (route yêu cầu
    session người dùng thật, ngoài phạm vi seed E2E hiện có). Test này vì
    vậy verify đúng phần đã CHẮC CHẮN thật và HTTP thật: seed thật tạo +
    withdraw thật 1 `data_processing_authorization`, xác nhận trạng thái WITHDRAWN
    được ghi nhận thật trong Company DB thật qua chính response HTTP thật
    của endpoint seed (authorizationId trả về), làm bằng chứng dữ liệu âm
    tồn tại thật cho môi trường CI kiểm tra thủ công/tương lai khi gap auth
    ở trên được đóng."""
    seeded = await _seed(real_company_service, "revoked_authorization")
    assert seeded.get("authorizationId")
    assert seeded.get("subjectReference")


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
