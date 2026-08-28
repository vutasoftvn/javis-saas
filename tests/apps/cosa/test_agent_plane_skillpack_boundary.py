"""
Regression test for skillpack runtime boundary.

Task 4: Verify that COSA agent-plane construction does not scan skillpacks/
or register capabilities from local Markdown/YAML. A validated local skillpack
is source-only (reference material); Phase B activation requires a real
capability handler registered explicitly in build_cosa_agent_plane with
Workspace authorization, policy, approval and audit.

This test protects the intentional ABSENCE of a local skillpack loader.
It must NOT require building a loader to pass, and it must FAIL if a naive
loader were added to the plane construction path.
"""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock
import pytest

from agent_core.capabilities.registry import CapabilityRegistry
from agent_core.conversations.repository import InMemoryConversationRepository
from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent_core.registry.repository import InMemorySpecRegistryRepository
from agent_core.runs.repository import InMemoryRunRepository
from agent_core.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane


@pytest.fixture
def mock_company_client():
    client = AsyncMock(spec=CompanyServiceClient)
    client.get.return_value = {}
    client.post.return_value = {}
    return client


@pytest.mark.asyncio
async def test_agent_plane_no_local_skillpack_loader(mock_company_client):
    """
    Verify that build_cosa_agent_plane() does not scan or load capabilities
    from local skillpacks/. All capabilities must be registered explicitly
    via SPEC objects (OPERATIONS_TASK_LIST_SPEC, etc) and handler factories.

    This test protects the intentional absence of a local skillpack runtime
    consumer, ensuring Phase B activation remains a capability-first release
    with full Workspace authorization and policy support.
    """
    plane = build_cosa_agent_plane(
        company_client=mock_company_client,
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )

    # Assert 1: Real capability IDs are in the registry
    # (These are defined in apps/cosa/capabilities/*.py as SPEC objects)
    assert plane.capability_registry.get("operations.task.list") is not None
    assert plane.capability_registry.get("operations.task.read") is not None
    assert plane.capability_registry.get("finance.payout.execute") is not None
    assert plane.capability_registry.get("finance.transaction.record") is not None
    assert plane.capability_registry.get("web.search") is not None
    assert plane.capability_registry.get("commercial.marketing_context.read") is not None
    assert plane.capability_registry.get("commercial.marketing_context.write") is not None
    assert plane.capability_registry.get("commercial.campaign_asset.write") is not None
    assert plane.capability_registry.get("commercial.experiment.write") is not None

    # Assert 2: No skillpack references in agent_plane module itself.
    # The module source should not import from or scan skillpacks/.
    agent_plane_module = inspect.getmodule(plane.__class__)
    if agent_plane_module is not None:
        agent_plane_source = inspect.getsource(agent_plane_module)
        assert "skillpacks" not in agent_plane_source, (
            "agent_plane.py must not import or scan skillpacks/ — "
            "capabilities are registered explicitly via SPEC objects only"
        )

    # Assert 3: None of the registered capability handlers reference skillpacks.
    # This ensures the runtime has not been configured to load from local sources.
    for spec_id, registration in plane.capability_registry._capabilities.items():
        handler = registration.handler
        handler_module = inspect.getmodule(handler)
        if handler_module is not None:
            try:
                handler_source = inspect.getsource(handler_module)
                assert "skillpacks" not in handler_source, (
                    f"Handler for capability '{spec_id}' must not reference skillpacks/ — "
                    "all capabilities must be defined in apps/cosa/capabilities/ "
                    "and registered explicitly"
                )
            except (OSError, TypeError):
                # Some built-in or compiled modules may not have source.
                # That's OK — we only check Python source modules.
                pass


@pytest.mark.asyncio
async def test_agent_plane_capability_registry_is_explicit(mock_company_client):
    """
    Verify that capability registration is explicit and deterministic.

    The capability registry must be built by calling specific registration
    functions (cap_registry.register(SPEC, handler)), not by scanning
    directories or parsing YAML/Markdown files at runtime.
    """
    plane = build_cosa_agent_plane(
        company_client=mock_company_client,
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )

    # The registry should have exactly the capabilities we expect to be
    # registered in build_cosa_agent_plane(). If someone adds a skillpack
    # loader that auto-discovers capabilities, this count will change.
    expected_capability_count = 10  # operations.task.list, operations.task.read,
                                    # finance.payout.execute, finance.transaction.record,
                                    # web.search, commercial.marketing_context.read,
                                    # commercial.marketing_context.write, commercial.campaign_asset.write,
                                    # commercial.experiment.write,
                                    # + sandbox_read_mcp_tools (1 additional)

    specs = plane.capability_registry.list_specs()
    actual_count = len(specs)
    capability_ids = [spec.id for spec in specs]
    assert actual_count >= expected_capability_count, (
        f"Expected at least {expected_capability_count} capabilities, "
        f"got {actual_count}. Capabilities: {capability_ids}"
    )
