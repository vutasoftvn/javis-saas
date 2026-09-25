from __future__ import annotations

import os
from typing import Any

from agent.conversations.repository import InMemoryConversationRepository
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel

from apps.cosa.api.app import create_cosa_app
from apps.cosa.capabilities.client import CompanyServiceClient, CompanyServiceError
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity

__all__ = ["app"]


class _VerifiedProjectsCompanyClient(CompanyServiceClient):
    """Company giả cho subprocess test: chỉ xác nhận các Project liệt kê trong
    `COSA_TEST_VERIFIED_PROJECT_IDS` (CSV), mọi đường dẫn khác trả lỗi như
    Company thật không với tới được."""

    def __init__(self, project_ids: set[str]) -> None:
        super().__init__()
        self._project_ids = project_ids

    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        prefix = "/operations/projects/"
        project_id = path[len(prefix) :] if path.startswith(prefix) else ""
        if project_id in self._project_ids:
            return {"id": project_id}
        raise CompanyServiceError(f"not found: {path}", status_code=404)


def _verified_projects_company_client() -> CompanyServiceClient | None:
    raw = os.environ.get("COSA_TEST_VERIFIED_PROJECT_IDS", "")
    project_ids = {item.strip() for item in raw.split(",") if item.strip()}
    return _VerifiedProjectsCompanyClient(project_ids) if project_ids else None


# For test runner subprocesses where DEEPSEEK_API_KEY / DB might not be preset,
# construct appropriate plane with FakeSDKModel:
db_url = os.environ.get("AGENT_DATABASE_URL")
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
        company_client=_verified_projects_company_client(),
    )
else:
    plane = None

app = create_cosa_app(plane=plane)
override_authenticated_identity(app)
