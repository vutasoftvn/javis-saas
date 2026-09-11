from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
from agent.conversations.repository import InMemoryConversationRepository
from agent.coordination.scheduler import RunScheduler
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.leases import RunLeaseManager
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel

from apps.cosa.agents.seed import seed_cosa_agent_specs
from apps.cosa.api.app import create_cosa_app
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from apps.cosa.policies.profile_locale_client import (
    ProfileLocaleClient,
    ProfileLocaleSnapshot,
    ProfileLocaleUnavailable,
)
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity
from tests.apps.cosa.policy_test_helpers import (
    configure_mock_client_allows_data_use,
    configure_mock_client_project_access,
    fake_active_tenant_policy_client,
)


class FakeProfileLocaleClient(ProfileLocaleClient):
    def __init__(self, preferred_locale: str = "vi-VN", should_fail: bool = False) -> None:
        self.preferred_locale = preferred_locale
        self.should_fail = should_fail
        self.calls: list[dict[str, str]] = []

    async def get_snapshot(self, bearer_token: str, workspace_id: str) -> ProfileLocaleSnapshot:
        self.calls.append({"bearer_token": bearer_token, "workspace_id": workspace_id})
        if self.should_fail:
            raise ProfileLocaleUnavailable("Simulated profile locale client failure")
        return ProfileLocaleSnapshot(
            workspace_id=workspace_id,
            preferred_locale=self.preferred_locale,
        )


def valid_access() -> dict[str, Any]:
    return {
        "categories": ["general_business_data"],
        "subject_reference": "workspace:ws-test",
    }


@pytest.fixture
def test_setup():
    mock_client = AsyncMock(spec=CompanyServiceClient)
    configure_mock_client_allows_data_use(mock_client)
    configure_mock_client_project_access(mock_client)
    locale_client = FakeProfileLocaleClient(preferred_locale="en-US")
    plane = build_cosa_agent_plane(
        company_client=mock_client,
        tenant_policy_client=fake_active_tenant_policy_client(),
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
        profile_locale_client=locale_client,
    )
    asyncio.run(seed_cosa_agent_specs(plane.spec_registry))
    app = create_cosa_app(plane=plane)
    override_authenticated_identity(app)
    return app, plane, locale_client


def queued_payload(plane: Any, run_id: str) -> dict[str, Any]:
    for task in plane.scheduler._tasks.values():
        if task.input_payload.get("run_id") == run_id:
            return task.input_payload
    raise AssertionError(f"Run {run_id} not found in scheduler tasks")


@pytest.mark.asyncio
async def test_message_uses_profile_en_us_when_content_is_vietnamese(test_setup):
    app, plane, locale_client = test_setup
    locale_client.preferred_locale = "en-US"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Create conversation c1
        conv_res = await client.post(
            "/agent/conversations",
            json={"title": "Test Locale", "active_agent_profile": "operations"},
        )
        c1 = conv_res.json()["id"]

        response = await client.post(
            f"/agent/conversations/{c1}/messages",
            json={
                "content": "Hãy tóm tắt",
                "role": "user",
                "data_access": valid_access(),
            },
        )
        assert response.status_code == 202
        run_id = response.json()["run_id"]
        payload = queued_payload(plane, run_id)
        assert payload.get("locale_source") == "profile"
        assert payload.get("locale") == "en-US"


@pytest.mark.asyncio
async def test_structured_turn_override_does_not_change_profile(test_setup):
    app, plane, locale_client = test_setup
    locale_client.preferred_locale = "en-US"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        conv_res = await client.post(
            "/agent/conversations",
            json={"title": "Test Override", "active_agent_profile": "operations"},
        )
        c1 = conv_res.json()["id"]

        response = await client.post(
            f"/agent/conversations/{c1}/messages",
            json={
                "content": "xin chào",
                "response_locale_override": "vi-VN",
                "role": "user",
                "data_access": valid_access(),
            },
        )
        assert response.status_code == 202
        run_id = response.json()["run_id"]
        payload = queued_payload(plane, run_id)
        assert payload.get("locale") == "vi-VN"
        assert payload.get("locale_source") == "turn_override"
        assert locale_client.preferred_locale == "en-US"


@pytest.mark.asyncio
async def test_unknown_override_is_rejected_before_message_persistence(test_setup):
    app, plane, _ = test_setup

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        conv_res = await client.post(
            "/agent/conversations",
            json={
                "title": "Test Reject",
                "active_agent_profile": "operations",
                "project_id": "proj_locale_1",
            },
        )
        c1 = conv_res.json()["id"]

        response = await client.post(
            f"/agent/conversations/{c1}/messages",
            json={
                "content": "hello",
                "project_id": "proj_locale_1",
                "response_locale_override": "fr-FR",
                "role": "user",
                "data_access": valid_access(),
            },
        )
        assert response.status_code == 422
        messages = await plane.conversation_repository.list_messages(c1)
        assert len(messages) == 0


@pytest.mark.asyncio
async def test_profile_locale_snapshot_failure_is_side_effect_free(test_setup):
    app, plane, locale_client = test_setup
    locale_client.should_fail = True

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        conv_res = await client.post(
            "/agent/conversations",
            json={"title": "Test 503", "active_agent_profile": "operations"},
        )
        c1 = conv_res.json()["id"]

        response = await client.post(
            f"/agent/conversations/{c1}/messages",
            json={
                "content": "hello",
                "role": "user",
                "data_access": valid_access(),
            },
        )
        assert response.status_code == 503
        messages = await plane.conversation_repository.list_messages(c1)
        assert len(messages) == 0
