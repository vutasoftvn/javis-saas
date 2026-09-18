"""Unit tests for Startup OS Onboard Cadence Advisory capability and handler."""

from __future__ import annotations

import httpx
import pytest

from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.startup_os_onboard import (
    STARTUP_OS_ONBOARD_CADENCE_ADVISORY_SPEC,
    create_startup_os_cadence_advisory_handler,
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


def test_cadence_advisory_spec_metadata():
    assert STARTUP_OS_ONBOARD_CADENCE_ADVISORY_SPEC.id == "startup_os.onboard.cadence_advisory"
    assert STARTUP_OS_ONBOARD_CADENCE_ADVISORY_SPEC.risk.value == "low"
    assert "workspace_id" in STARTUP_OS_ONBOARD_CADENCE_ADVISORY_SPEC.input_schema["required"]


@pytest.mark.asyncio
async def test_cadence_advisory_all_fresh():
    def mock_service(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert "/operations/onboard/cadence/status" in str(request.url)
        assert request.url.params.get("workspaceId") == "ws-test-1"
        return httpx.Response(
            200,
            json={
                "cadences": [
                    {"dimension": "stage_scale", "daysSinceLastReview": 3, "intervalDays": 14, "urgency": "fresh", "cadence": "fast"},
                    {"dimension": "challenges", "daysSinceLastReview": 5, "intervalDays": 14, "urgency": "fresh", "cadence": "fast"},
                    {"dimension": "market", "daysSinceLastReview": 20, "intervalDays": 60, "urgency": "fresh", "cadence": "medium"},
                ]
            },
        )

    client = _make_mock_client(mock_service)
    handler = create_startup_os_cadence_advisory_handler(client)

    result = await handler({"workspace_id": "ws-test-1"})

    assert result["workspace_id"] == "ws-test-1"
    assert result["freshness_score"] == 100.0
    assert result["status"] == "fresh"
    assert len(result["recommendations"]) == 0
    assert "Founder toàn quyền quyết định" in result["founder_authority"]


@pytest.mark.asyncio
async def test_cadence_advisory_with_stale_dimensions_and_nudges():
    def mock_service(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "cadences": [
                    {
                        "dimension": "stage_scale",
                        "daysSinceLastReview": 28,  # 4 weeks (interval: 14d = 2 weeks -> ratio 2.0)
                        "intervalDays": 14,
                        "urgency": "critical",
                        "cadence": "fast",
                    },
                    {
                        "dimension": "challenges",
                        "daysSinceLastReview": 21,  # 3 weeks (interval: 14d = 2 weeks -> ratio 1.5)
                        "intervalDays": 14,
                        "urgency": "recommended",
                        "cadence": "fast",
                    },
                    {
                        "dimension": "market",
                        "daysSinceLastReview": 10,
                        "intervalDays": 60,
                        "urgency": "fresh",
                        "cadence": "medium",
                    },
                ]
            },
        )

    client = _make_mock_client(mock_service)
    handler = create_startup_os_cadence_advisory_handler(client)

    result = await handler({"workspace_id": "ws-test-2"})

    assert result["workspace_id"] == "ws-test-2"
    assert result["freshness_score"] < 100.0
    assert len(result["recommendations"]) == 2

    # Check stage_scale recommendation details
    rec_stage = next(r for r in result["recommendations"] if r["dimension"] == "stage_scale")
    assert rec_stage["cadence_type"] == "fast"
    assert rec_stage["weeks_since_last_review"] == 4
    assert rec_stage["recommended_interval_weeks"] == 2
    assert rec_stage["urgency"] == "critical"
    assert "4 tuần chưa rà soát" in rec_stage["advisory_nudge"]
    assert "update_now_2min" in rec_stage["available_actions"]
    assert "snooze_1w" in rec_stage["available_actions"]
    assert "ignore" in rec_stage["available_actions"]
