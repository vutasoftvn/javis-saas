from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
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


class CompanyHttpObserver:
    def __init__(self) -> None:
        self.snapshot_requests = 0
        self.data_use_requests = 0
        self.last_headers: dict[str, str] = {}
        self.last_body: dict[str, Any] = {}

    def reset(self) -> None:
        self.snapshot_requests = 0
        self.data_use_requests = 0
        self.last_headers.clear()
        self.last_body.clear()


def make_company_mock_transport(observer: CompanyHttpObserver):
    """Real HTTP mock transport simulating the Company backend contract."""

    async def handle_request(request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        headers = dict(request.headers)
        observer.last_headers = headers

        body = json.loads(request.content.decode("utf-8")) if request.content else {}
        observer.last_body = body

        # Route 1: Snapshot Resolution
        if url_path == "/finance-legal/ai-compliance/runtime/snapshots/resolve":
            observer.snapshot_requests += 1

            ws_id = headers.get("x-workspace-id", "")
            auth = headers.get("authorization", "")

            # Delegation check
            if not auth.startswith("Bearer ") or len(auth.split(" ")[1]) < 10:
                return httpx.Response(403, json={"error": "Delegation denied: invalid token"})

            system_key = body.get("systemKey", "")
            capability_ids = body.get("capabilityIds", [])

            if not capability_ids:
                return httpx.Response(400, json={"error": "capabilityIds must be non-empty"})

            # Cross-workspace or non-existent deployment check
            if ws_id == "ws_foreign" or system_key == "unknown-system":
                return httpx.Response(404, json={"error": "No approved deployment for this workspace"})

            # Suspended deployment check
            if ws_id == "ws_suspended":
                return httpx.Response(409, json={"error": "Deployment is suspended"})

            # Unbound capability check
            if "operations.unbound" in capability_ids:
                return httpx.Response(404, json={"error": "Capability not bound to system version"})

            expiry = (datetime.now(UTC) + timedelta(days=1)).isoformat()
            return httpx.Response(
                200,
                json={
                    "workspaceId": ws_id,
                    "deploymentId": f"dep_{ws_id}",
                    "assessmentId": f"ass_{ws_id}",
                    "mode": "ADVISORY_ONLY",
                    "status": "APPROVED_FOR_USE",
                    "allowedCapabilities": list(capability_ids),
                    "providerProfileVersion": "v3",
                    "dataProfileVersion": "v1",
                    "snapshotHash": "sha256:" + "a" * 64,
                    "policySnapshotHash": "sha256:" + "b" * 64,
                    "evidenceHashes": ["sha256:evidence-prod-1"],
                    "legalVersionIds": ["134-2025-v1"],
                    "expiresAt": expiry,
                },
            )

        # Route 2: Resolve Data Use
        if url_path == "/finance-legal/ai-compliance/resolve-data-use":
            observer.data_use_requests += 1
            ws_id = headers.get("x-workspace-id", "")
            model_key = body.get("modelKey", "")
            data_categories = body.get("dataCategories", [])
            subject_ref = body.get("subjectReference")

            if ws_id == "ws_foreign":
                return httpx.Response(200, json={"allowed": False, "denialCode": "DEPLOYMENT_NOT_FOUND"})

            if model_key and model_key != "deepseek-chat":
                return httpx.Response(200, json={"allowed": False, "denialCode": "MODEL_NOT_APPROVED"})

            is_personal = any(c in ("PERSONAL", "SENSITIVE_PERSONAL") for c in data_categories)
            if is_personal and not subject_ref:
                return httpx.Response(
                    200, json={"allowed": False, "denialCode": "PROCESSING_AUTHORIZATION_MISSING"}
                )

            return httpx.Response(
                200,
                json={
                    "allowed": True,
                    "denialCode": None,
                    "providerProfileVersion": "v3",
                    "dataProfileVersion": "v1",
                    "retentionPolicyId": "retention-30d",
                    "minimizationRequired": True,
                },
            )

        return httpx.Response(404, text="Not Found")

    return httpx.MockTransport(handle_request)


@pytest.fixture
def company_http_setup(monkeypatch: pytest.MonkeyPatch):
    observer = CompanyHttpObserver()
    transport = make_company_mock_transport(observer)

    real_async_client_init = httpx.AsyncClient.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = transport
        real_async_client_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)
    return observer


@pytest.mark.asyncio
async def test_approved_run_reaches_company_then_model_once(company_http_setup: CompanyHttpObserver) -> None:
    observer = company_http_setup
    fake_model = FakeSDKModel(responses=[text_response("Advisory report generated successfully.")])
    client = AiComplianceClient(base_url="http://company.internal")
    resolver = ComplianceResolver(client=client)
    gate = CosaDataModelGate(client=client)

    kernel = RealOpenAIAgentsSDKKernel(
        model=fake_model,
        compliance_resolver=resolver,
        model_input_guard=gate,
    )

    async def submit_real_run(
        workspace_id: str,
        capability_ids: list[str] | None = None,
        claim: DataAccessClaim | None = None,
    ) -> RunResult:
        caps = capability_ids or ["operations.task.list"]
        spec = AgentSpec(
            id="task_advisor",
            instructions="Advisory only",
            capability_refs=caps,
        )
        metadata: dict[str, Any] = {"capability_ids": caps}
        if claim is not None:
            metadata["data_access_claim"] = claim

        req = RunRequest(
            root_executable_ref="agent:task_advisor",
            workspace_id=workspace_id,
            principal="founder_1",
            input={"prompt": "Plan tasks for current quarter"},
            metadata=metadata,
        )
        try:
            return await kernel.run(req, spec)
        except ComplianceDenied:
            return RunResult(run_id=req.run_id or "run", status=RunStatus.FAILED)

    approved_claim = DataAccessClaim(
        workspace_id="ws_approved",
        deployment_id="dep_ws_approved",
        capability_id="operations.task.list",
        source_ref="doc://quarter/q3",
        source_hash="sha256:source123",
        categories=frozenset(["BUSINESS_CONFIDENTIAL"]),
        purpose_id="advisory",
        provider_key="deepseek",
        model_key="deepseek-chat",
    )

    result = await submit_real_run(
        "ws_approved",
        capability_ids=["operations.task.list"],
        claim=approved_claim,
    )
    assert result.status == RunStatus.COMPLETED
    assert observer.snapshot_requests == 1
    assert fake_model.call_count == 1


@pytest.mark.asyncio
async def test_suspended_or_cross_workspace_run_never_reaches_model(
    company_http_setup: CompanyHttpObserver,
) -> None:
    observer = company_http_setup
    fake_model = FakeSDKModel(responses=[text_response("unreachable")])
    client = AiComplianceClient(base_url="http://company.internal")
    resolver = ComplianceResolver(client=client)
    gate = CosaDataModelGate(client=client)

    kernel = RealOpenAIAgentsSDKKernel(
        model=fake_model,
        compliance_resolver=resolver,
        model_input_guard=gate,
    )

    async def submit_real_run(workspace_id: str) -> RunResult:
        spec = AgentSpec(
            id="task_advisor",
            instructions="Advisory only",
            capability_refs=["operations.task.list"],
        )
        req = RunRequest(
            root_executable_ref="agent:task_advisor",
            workspace_id=workspace_id,
            principal="founder_1",
            input={"prompt": "Should fail before model"},
            metadata={"capability_ids": ["operations.task.list"]},
        )
        try:
            return await kernel.run(req, spec)
        except ComplianceDenied:
            return RunResult(run_id=req.run_id or "run", status=RunStatus.FAILED)

    # 1. Suspended workspace
    res_suspended = await submit_real_run("ws_suspended")
    assert res_suspended.status == RunStatus.FAILED
    assert fake_model.call_count == 0

    # 2. Foreign cross-workspace tenant
    res_foreign = await submit_real_run("ws_foreign")
    assert res_foreign.status == RunStatus.FAILED
    assert fake_model.call_count == 0


@pytest.mark.asyncio
async def test_negative_matrix_over_http(company_http_setup: CompanyHttpObserver) -> None:
    observer = company_http_setup
    fake_model = FakeSDKModel(responses=[text_response("unreachable")])
    client = AiComplianceClient(base_url="http://company.internal")
    resolver = ComplianceResolver(client=client)
    gate = CosaDataModelGate(client=client)

    kernel = RealOpenAIAgentsSDKKernel(
        model=fake_model,
        compliance_resolver=resolver,
        model_input_guard=gate,
    )

    async def submit_run(
        spec_id: str,
        caps: list[str],
        claim: DataAccessClaim | None = None,
    ) -> RunResult:
        spec = AgentSpec(
            id=spec_id,
            instructions="Advisory only",
            capability_refs=caps,
        )
        metadata: dict[str, Any] = {"capability_ids": caps}
        if claim is not None:
            metadata["data_access_claim"] = claim

        req = RunRequest(
            root_executable_ref=f"agent:{spec_id}",
            workspace_id="ws_approved",
            principal="founder_1",
            input={"prompt": "Negative test prompt"},
            metadata=metadata,
        )
        try:
            return await kernel.run(req, spec)
        except ComplianceDenied:
            return RunResult(run_id=req.run_id or "run", status=RunStatus.FAILED)

    # Negative 1: Unbound capability
    res_unbound = await submit_run("task_advisor_unbound", ["operations.unbound"])
    assert res_unbound.status == RunStatus.FAILED
    assert fake_model.call_count == 0

    # Negative 2: Model mismatch at gate
    claim_mismatch = DataAccessClaim(
        workspace_id="ws_approved",
        deployment_id="dep_ws_approved",
        capability_id="operations.task.list",
        source_ref="doc://test/1",
        source_hash="sha256:abc",
        categories=frozenset(["BUSINESS_CONFIDENTIAL"]),
        purpose_id="advisory",
        provider_key="deepseek",
        model_key="unapproved-model-coder",
    )
    res_mismatch = await submit_run("task_advisor_mismatch", ["operations.task.list"], claim_mismatch)
    assert res_mismatch.status == RunStatus.FAILED
    assert fake_model.call_count == 0

    # Negative 3: Personal data without subject reference
    claim_personal = DataAccessClaim(
        workspace_id="ws_approved",
        deployment_id="dep_ws_approved",
        capability_id="operations.task.list",
        source_ref="doc://customer/1",
        source_hash="sha256:cust1",
        categories=frozenset(["PERSONAL"]),
        purpose_id="advisory",
        subject_reference=None,
        provider_key="deepseek",
        model_key="deepseek-chat",
    )
    res_personal = await submit_run("task_advisor_personal", ["operations.task.list"], claim_personal)
    assert res_personal.status == RunStatus.FAILED
    assert fake_model.call_count == 0
