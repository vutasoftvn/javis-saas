from __future__ import annotations

from unittest.mock import AsyncMock
import pytest

from apps.cosa.capabilities.project_lifecycle import (
    ANALYTICS_METRIC_CONTRACT_GET_SPEC,
    ANALYTICS_PMF_SCOREBOARD_GET_SPEC,
    ANALYTICS_PMF_SCOREBOARD_PROPOSE_SPEC,
    create_analytics_metric_contract_get_handler,
    create_analytics_pmf_scoreboard_get_handler,
    create_analytics_pmf_scoreboard_propose_handler,
)
from agent.capabilities.registry import CapabilityRegistry
from agent.artifacts import InMemoryArtifactRepository
from agent.conversations.repository import InMemoryConversationRepository
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from apps.cosa.composition.agent_plane import build_cosa_agent_plane


@pytest.mark.asyncio
async def test_analytics_metric_contract_get_handler():
    client = AsyncMock()
    client.get.return_value = {
        "items": [
            {
                "id": "101",
                "metricKey": "activation_rate",
                "displayName": "Activation Rate",
                "status": "ACTIVE",
            }
        ]
    }

    handler = create_analytics_metric_contract_get_handler(client)
    res = await handler({"project_id": "100"}, context={"workspace_id": "ws-123"})

    client.get.assert_awaited_once_with(
        "/operations/strategy/metric-contracts",
        params={"projectId": "100"},
        headers={"X-Workspace-Id": "ws-123"},
    )
    assert len(res["contracts"]) == 1
    assert res["advisory"]["label"] == "insight"


@pytest.mark.asyncio
async def test_analytics_pmf_scoreboard_get_handler():
    client = AsyncMock()
    client.get.return_value = {
        "items": [
            {
                "id": "201",
                "result": "PROMISING",
                "calculationHash": "hash123",
            }
        ]
    }

    handler = create_analytics_pmf_scoreboard_get_handler(client)
    res = await handler({"project_id": "100"}, context={"workspace_id": "ws-123"})

    client.get.assert_awaited_once_with(
        "/operations/strategy/pmf-scoreboards",
        params={"projectId": "100"},
        headers={"X-Workspace-Id": "ws-123"},
    )
    assert len(res["runs"]) == 1
    assert res["advisory"]["label"] == "insight"


@pytest.mark.asyncio
async def test_analytics_pmf_scoreboard_propose_handler():
    client = AsyncMock()
    client.get.return_value = {
        "items": [
            {
                "id": "201",
                "result": "PROMISING",
                "calculationHash": "sha256_abcdef1234567890",
                "missingDataFlags": [],
                "reliabilityFlags": [],
                "inputSnapshotIds": ["snap-1", "snap-2"],
            }
        ]
    }

    handler = create_analytics_pmf_scoreboard_propose_handler(client)
    res = await handler({"project_id": "100"}, context={"workspace_id": "ws-123"})

    assert res["status"] == "completed"
    assert res["classification"] == "PROMISING"
    assert res["memo"]["decision"].startswith("Tín hiệu PMF khả quan")
    assert res["memo"]["source_ids"] == ["snap-1", "snap-2"]
    assert res["memo"]["human_owner"] == "Founder / Product DRI"
    assert res["advisory"]["label"] == "proposal"


@pytest.mark.asyncio
async def test_analytics_pmf_scoreboard_propose_insufficient_data():
    client = AsyncMock()
    client.get.return_value = {"items": []}

    handler = create_analytics_pmf_scoreboard_propose_handler(client)
    res = await handler({"project_id": "100"}, context={"workspace_id": "ws-123"})

    assert res["status"] == "completed"
    assert res["classification"] == "INSUFFICIENT_DATA"
    assert "Chưa đủ dữ liệu" in res["memo"]["decision"]
    assert res["memo"]["source_ids"] == []


def test_pmf_capability_registry_boundaries():
    """Verify capabilities boundary: advisory only, no auto-decision / mutator capabilities."""
    plane = build_cosa_agent_plane(
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        artifact_repository=InMemoryArtifactRepository(),
        runtime="manual_tool_loop",
    )

    cap_ids = {spec.id for spec in plane.capability_registry.list_specs()}

    # Registered advisory capabilities
    assert "analytics.metric_contract.get" in cap_ids
    assert "analytics.pmf_scoreboard.get" in cap_ids
    assert "analytics.pmf_scoreboard.propose" in cap_ids

    # STRICT Invariant: Mutator / decision executing tools MUST NOT be registered
    assert "strategy.pivot.execute" not in cap_ids
    assert "analytics.metric_snapshot.ingest" not in cap_ids
    assert "strategy.gate.pass" not in cap_ids
    assert "strategy.lifecycle.auto_transition" not in cap_ids
