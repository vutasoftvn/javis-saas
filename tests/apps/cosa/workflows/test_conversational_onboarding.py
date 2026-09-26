"""Unit tests for Conversational Onboarding Workflow and Event-Driven Trigger Detector."""

from __future__ import annotations

import httpx
import pytest

from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.workflows.conversational_onboarding import (
    FULL_ONBOARD_STEPS,
    CadenceCategory,
    ConversationalOnboardingWorkflow,
    EventTriggerDetector,
    OnboardingSessionType,
)
from apps.cosa.workflows.onboarding_dimensions import (
    ONBOARD_DIMENSION_FIELDS,
    OnboardDimensionDataError,
)


def _make_mock_client(handler_fn) -> CompanyServiceClient:
    transport = httpx.MockTransport(handler_fn)
    client = CompanyServiceClient(base_url="http://mock-company-service")

    async def _mock_request(
        method: str,
        path: str,
        params: dict | None = None,
        json: dict | None = None,
        headers: dict | None = None,
    ) -> dict:
        url = f"{client.base_url}/{path.lstrip('/')}"
        req_headers = dict(client.default_headers)
        if headers:
            req_headers.update(headers)
        async with httpx.AsyncClient(transport=transport) as hc:
            resp = await hc.request(method, url, params=params, json=json, headers=req_headers)
            return resp.json()

    client._request = _mock_request
    return client


def test_steps_initial_session():
    wf = ConversationalOnboardingWorkflow("ws-init", OnboardingSessionType.INITIAL)
    steps = wf.get_steps()

    assert len(steps) == 7
    dims = [s.dimension for s in steps]
    assert dims == [
        "stage_scale",
        "challenges",
        "goals_ambition",
        "market",
        "team_culture",
        "identity",
        "founder",
    ]

    # Check cadences
    assert steps[0].cadence == CadenceCategory.FAST
    assert steps[1].cadence == CadenceCategory.FAST
    assert steps[2].cadence == CadenceCategory.MEDIUM
    assert steps[3].cadence == CadenceCategory.MEDIUM
    assert steps[4].cadence == CadenceCategory.MEDIUM
    assert steps[5].cadence == CadenceCategory.SLOW
    assert steps[6].cadence == CadenceCategory.SLOW


def test_steps_partial_update_micro_intake():
    wf = ConversationalOnboardingWorkflow("ws-partial", OnboardingSessionType.PARTIAL_UPDATE)
    steps = wf.get_steps()

    assert len(steps) == 2
    assert [s.dimension for s in steps] == ["stage_scale", "challenges"]
    assert all(s.cadence == CadenceCategory.FAST for s in steps)


@pytest.mark.asyncio
async def test_workflow_session_lifecycle():
    recorded_calls = []

    def mock_service(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        body = request.read().decode("utf-8")
        recorded_calls.append((request.method, path, body))

        if path.endswith("/operations/onboard/sessions"):
            return httpx.Response(200, json={"sessionId": "sess-xyz-123", "status": "active"})
        elif "/operations/onboard/dimensions/" in path:
            return httpx.Response(200, json={"status": "recorded", "version": 2})
        elif path.endswith("/operations/onboard/snapshots"):
            return httpx.Response(200, json={"snapshotId": "snap-999", "status": "frozen"})
        return httpx.Response(404, json={"error": "not found"})

    client = _make_mock_client(mock_service)
    wf = ConversationalOnboardingWorkflow(
        "ws-life-1", OnboardingSessionType.PARTIAL_UPDATE, client=client
    )

    # 1. Start Session
    start_resp = await wf.start_session("Cập nhật nhanh 2 phút tuần 6")
    assert start_resp["sessionId"] == "sess-xyz-123"
    assert wf.active_session_id == "sess-xyz-123"

    # 2. Submit dimension
    dim_resp = await wf.submit_dimension(
        "stage_scale",
        {"revenueArr": 150000, "runwayMonths": 8, "headcountFt": 8, "stage": "pre_pmf"},
    )
    assert dim_resp["status"] == "recorded"

    # 3. Complete and create snapshot
    snap_resp = await wf.complete_and_create_snapshot("Hoàn tất rà soát nhanh 2 phút")
    assert snap_resp["snapshotId"] == "snap-999"

    assert len(recorded_calls) == 3
    assert recorded_calls[0][1] == "/operations/onboard/sessions"
    assert "/operations/onboard/dimensions/stage_scale" in recorded_calls[1][1]
    assert recorded_calls[2][1] == "/operations/onboard/snapshots"


def test_event_trigger_detector():
    # 1. Fundraising trigger
    r1 = EventTriggerDetector.detect(
        "Chúng tôi vừa nhận được term sheet vòng Seed 500k USD từ quỹ đầu tư mạo hiểm."
    )
    assert r1.triggered is True
    assert r1.event_type == "fundraising"
    assert r1.suggested_dimension == "stage_scale"
    assert "Runway" in (r1.advisory_prompt or "")

    # 2. Key personnel change
    r2 = EventTriggerDetector.detect(
        "Tuần tới công ty vừa tuyển một CTO mới để lead đội ngũ engineering."
    )
    assert r2.triggered is True
    assert r2.event_type == "key_personnel_change"
    assert r2.suggested_dimension == "team_culture"

    # 3. Competitor move
    r3 = EventTriggerDetector.detect(
        "Đối thủ cạnh tranh lớn vừa tung sản phẩm mới và hạ giá 30% để chiếm thị phần."
    )
    assert r3.triggered is True
    assert r3.event_type == "competitor_move"
    assert r3.suggested_dimension == "market"

    # 4. Strategic pivot
    r4 = EventTriggerDetector.detect(
        "Sau khi test thị trường, ban giám đốc quyết định pivot sang B2B SaaS doanh nghiệp."
    )
    assert r4.triggered is True
    assert r4.event_type == "strategic_pivot"
    assert r4.suggested_dimension == "goals_ambition"

    # 5. Normal non-trigger message
    r5 = EventTriggerDetector.detect("Chào buổi sáng, hôm nay chúng ta có lịch họp lúc 10h không?")
    assert r5.triggered is False
    assert r5.event_type is None


def test_interview_steps_only_ask_for_fields_company_stores():
    # Trước đây catalog dùng `arr`/`burn_rate_weekly`… — Company bỏ âm thầm.
    for step in FULL_ONBOARD_STEPS:
        allowed = set(ONBOARD_DIMENSION_FIELDS[step.dimension])
        assert set(step.expected_schema_keys) <= allowed, step.dimension
        assert step.expected_schema_keys, step.dimension


@pytest.mark.asyncio
async def test_submit_dimension_rejects_legacy_keys_before_calling_company():
    calls: list[str] = []

    def mock_service(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json={"sessionId": "sess-1"})

    wf = ConversationalOnboardingWorkflow(
        "ws-1", OnboardingSessionType.PARTIAL_UPDATE, client=_make_mock_client(mock_service)
    )
    await wf.start_session()
    with pytest.raises(OnboardDimensionDataError, match="unknown field"):
        await wf.submit_dimension("stage_scale", {"arr": 150000, "burn_rate_weekly": 5000})
    assert calls == ["/operations/onboard/sessions"]
