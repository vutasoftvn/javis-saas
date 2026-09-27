from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from agent.capabilities.registry import CapabilityRegistry

from apps.cosa.capabilities.access_matrix import MATRIX, Tier
from apps.cosa.capabilities.business_read import (
    BUSINESS_READ_SPEC,
    DOMAIN_TO_CAPABILITY,
    _compact,
    create_business_read_handler,
    delegated_capability_ids,
)
from apps.cosa.composition.capability_registration import register_cosa_capabilities


def test_every_domain_maps_to_a_t0_capability_with_company_cap() -> None:
    for domain, cap in DOMAIN_TO_CAPABILITY.items():
        assert MATRIX[cap].tier is Tier.T0_READ, (domain, cap)
        assert MATRIX[cap].company_agent_cap == cap, (domain, cap)
    assert BUSINESS_READ_SPEC.input_schema["properties"]["domain"]["enum"] == sorted(
        DOMAIN_TO_CAPABILITY
    )


@pytest.mark.asyncio
async def test_dispatches_with_run_scope_not_model_ids() -> None:
    calls: list[tuple[str, dict, object]] = []

    async def dispatch(cap_id: str, payload: dict, context: object) -> dict:
        calls.append((cap_id, payload, context))
        return {"items": [1]}

    ctx = {"workspace_id": "w1", "project_id": "p1"}
    out = await create_business_read_handler(dispatch)(
        {"domain": "finance", "project_id": "p-bịa"}, ctx
    )
    assert calls == [("finance.transaction.read", {"workspace_id": "w1", "project_id": "p1"}, ctx)]
    assert out == {"domain": "finance", "data": {"items": [1]}}


@pytest.mark.asyncio
async def test_unknown_domain_raises() -> None:
    handler = create_business_read_handler(AsyncMock())
    with pytest.raises(ValueError, match="domain"):
        await handler({"domain": "nope"}, {})


def test_compact_truncates_long_lists() -> None:
    out = _compact({"items": list(range(50))})
    assert out["items"]["truncated"] is True and out["items"]["total"] == 50
    assert len(out["items"]["items"]) == 20
    assert _compact([1, 2]) == [1, 2]


def test_delegated_capabilities_only_when_business_read_is_referenced() -> None:
    assert delegated_capability_ids(["operations.task.list"]) == []
    assert set(delegated_capability_ids(["business.read"])) == set(DOMAIN_TO_CAPABILITY.values())


def _registry(client: Any) -> CapabilityRegistry:
    registry = CapabilityRegistry()
    register_cosa_capabilities(
        registry,
        client=client,
        tenant_policy=MagicMock(),
        search_budget=MagicMock(),
        artifact_repo=MagicMock(),
        web_search_provider=MagicMock(),
        knowledge_ingestion_service=MagicMock(),
    )
    return registry


@pytest.mark.asyncio
async def test_registered_business_read_reaches_real_read_handler() -> None:
    client = AsyncMock()
    client.get.return_value = {"tree": [{"title": "Vision"}]}
    handler = _registry(client).get("business.read").handler
    out = await handler({"domain": "goals"}, {"workspace_id": "ws-7", "project_id": "p1"})
    client.get.assert_awaited_once_with("/operations/goals/tree", params={"workspaceId": "ws-7"})
    assert out["data"] == {"tree": [{"title": "Vision"}]}


@pytest.mark.asyncio
async def test_registered_business_read_reports_missing_project_scope() -> None:
    client = AsyncMock()
    handler = _registry(client).get("business.read").handler
    out = await handler({"domain": "legal"}, {"workspace_id": "ws-7"})
    assert out["data"]["ok"] is False and out["data"]["error_code"] == "scope_missing"
    client.get.assert_not_awaited()
