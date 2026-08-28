from __future__ import annotations

import os
from typing import Any

from agent_core.conversations.repository import InMemoryConversationRepository
from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent_core.registry.repository import InMemorySpecRegistryRepository
from agent_core.runs.repository import InMemoryRunRepository
from agent_core.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel

from apps.cosa.api.app import create_cosa_app
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity

__all__ = ["app"]

# For test runner subprocesses where DEEPSEEK_API_KEY / DB might not be preset,
# construct appropriate plane with FakeSDKModel:
db_url = os.environ.get("AGENT_CORE_DATABASE_URL")
plane: Any = None
if not db_url:
    plane = build_cosa_agent_plane(
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )
elif not os.environ.get("DEEPSEEK_API_KEY"):
    plane = build_cosa_agent_plane(
        database_url=db_url,
        model=FakeSDKModel(),
    )
else:
    plane = None

app = create_cosa_app(plane=plane)
override_authenticated_identity(app)
