from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from agent.governance.contracts import CapabilityRisk

from apps.cosa.capabilities.okr_write import (
    OKR_KEY_RESULT_CHECKIN_SPEC,
    OKR_KEY_RESULT_CREATE_SPEC,
    OKR_KEY_RESULT_UPDATE_SPEC,
    OKR_OBJECTIVE_LIST_SPEC,
    create_okr_key_result_checkin_handler,
    create_okr_key_result_create_handler,
    create_okr_key_result_update_handler,
    create_okr_objective_list_handler,
)

CTX = {"workspace_id": "ws-1", "locale": "vi-VN"}
HEADERS = {"X-Workspace-Id": "ws-1"}


def test_specs_ids_and_risk() -> None:
    assert OKR_OBJECTIVE_LIST_SPEC.id == "okr.objective.list"
    assert OKR_KEY_RESULT_CREATE_SPEC.id == "okr.key_result.create"
    assert OKR_KEY_RESULT_CHECKIN_SPEC.id == "okr.key_result.checkin"
    assert OKR_KEY_RESULT_UPDATE_SPEC.id == "okr.key_result.update"
    assert OKR_OBJECTIVE_LIST_SPEC.risk is CapabilityRisk.LOW
    assert OKR_KEY_RESULT_CREATE_SPEC.risk is CapabilityRisk.MEDIUM
    assert OKR_KEY_RESULT_CHECKIN_SPEC.risk is CapabilityRisk.MEDIUM
    assert OKR_KEY_RESULT_UPDATE_SPEC.risk is CapabilityRisk.MEDIUM


@pytest.mark.asyncio
async def test_objective_list_nests_key_results_with_labels() -> None:
    client = AsyncMock()
    client.get.side_effect = [
        {
            "data": [
                {
                    "id": "o1",
                    "title": "Tăng trưởng",
                    "status": "published",
                    "projectId": "p1",
                    "scope": "project",
                    "goalId": None,
                    "parentObjectiveId": "c1",
                }
            ]
        },
        {
            "data": [
                {
                    "id": "k1",
                    "objectiveId": "o1",
                    "title": "MRR",
                    "currentValue": 5,
                    "targetValue": 10,
                    "unit": "M",
                    "status": "draft",
                },
                {"id": "k2", "objectiveId": "o9", "title": "Khác", "status": "weird"},
            ]
        },
    ]
    out = await create_okr_objective_list_handler(client)({}, CTX)
    assert client.get.await_args_list[0].args == ("/operations/objectives",)
    assert client.get.await_args_list[0].kwargs == {"headers": HEADERS}
    assert client.get.await_args_list[1].args == ("/operations/key-results",)
    [obj] = out["objectives"]
    assert obj["title"] == "Tăng trưởng" and obj["statusLabel"] == "Đã công bố"
    assert [kr["title"] for kr in obj["keyResults"]] == ["MRR"]
    assert obj["keyResults"][0]["statusLabel"] == "Nháp"
    assert "status" not in obj  # không trả enum thô
    assert obj["scope"] == "project"
    assert obj["parentObjectiveId"] == "c1"
    assert "goalId" in obj


@pytest.mark.asyncio
async def test_key_result_create_posts_company_field_names() -> None:
    client = AsyncMock()
    client.post.return_value = {"id": "k1", "title": "MRR", "targetValue": 10, "status": "draft"}
    out = await create_okr_key_result_create_handler(client)(
        {
            "objective_id": "o1",
            "title": " MRR ",
            "target_value": 10,
            "unit": "M",
            "baseline_value": 2,
            "scoring_type": "LINEAR_INCREASE",
        },
        CTX,
    )
    client.post.assert_awaited_once_with(
        "/operations/objectives/o1/key-results",
        json={
            "title": "MRR",
            "targetValue": 10,
            "baselineValue": 2,
            "unit": "M",
            "scoringType": "LINEAR_INCREASE",
        },
        headers=HEADERS,
    )
    assert out["key_result"]["title"] == "MRR"


@pytest.mark.asyncio
async def test_key_result_create_requires_objective() -> None:
    with pytest.raises(KeyError):
        await create_okr_key_result_create_handler(AsyncMock())({"title": "x"}, CTX)


@pytest.mark.asyncio
async def test_key_result_checkin_posts_value() -> None:
    client = AsyncMock()
    client.post.return_value = {"id": "kr1", "title": "MRR", "currentValue": 12}
    out = await create_okr_key_result_checkin_handler(client)(
        {"key_result_id": "kr1", "value": 12}, CTX
    )
    client.post.assert_awaited_once_with(
        "/operations/key-results/kr1/checkin", json={"value": 12}, headers=HEADERS
    )
    assert out["key_result"]["currentValue"] == 12


@pytest.mark.asyncio
async def test_missing_workspace_fails_closed() -> None:
    with pytest.raises(ValueError, match="workspace_id"):
        await create_okr_objective_list_handler(AsyncMock())({}, {})

@pytest.mark.asyncio
async def test_key_result_update_puts_fields() -> None:
    client = AsyncMock()
    client.put.return_value = {
        "id": "kr1",
        "title": "MRR",
        "targetValue": 20,
        "currentValue": 5,
        "status": "active",
        "unit": "USD",
    }
    out = await create_okr_key_result_update_handler(client)(
        {
            "key_result_id": "kr1",
            "status": "active",
            "target_value": 20,
            "current_value": 5,
            "unit": "USD",
        },
        CTX,
    )
    client.put.assert_awaited_once_with(
        "/operations/key-results/kr1",
        json={
            "status": "active",
            "targetValue": 20,
            "currentValue": 5,
            "unit": "USD",
        },
        headers=HEADERS,
    )
    assert out["key_result"]["statusLabel"] == "Đang thực hiện"


@pytest.mark.asyncio
async def test_key_result_update_requires_id() -> None:
    with pytest.raises(KeyError):
        await create_okr_key_result_update_handler(AsyncMock())({"status": "active"}, CTX)

