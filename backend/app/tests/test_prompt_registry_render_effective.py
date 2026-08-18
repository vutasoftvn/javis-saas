from unittest.mock import MagicMock

import pytest

from app.workforce.ai.prompt_registry import PromptRegistry
from app.core.protected_resources.models import ProtectedResource, ProtectedResourceRevision
from app.core.snowflake import generate_snowflake_id


def test_render_effective_falls_back_to_file_default_when_no_override():
    registry = PromptRegistry.get_instance()
    registry.reload()
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    workspace_id = generate_snowflake_id()

    rendered = registry.render_effective(
        db, workspace_id, "sales", "outbound",
        {"company_name": "Acme Corp", "icp_criteria": "B2B SaaS"},
    )

    assert "Acme Corp" in rendered


def test_render_effective_uses_workspace_override_when_present():
    registry = PromptRegistry.get_instance()
    registry.reload()
    workspace_id = generate_snowflake_id()

    resource = ProtectedResource(
        id=generate_snowflake_id(), workspace_id=workspace_id,
        resource_type="domain_prompt", resource_key="cosa/system",
        active_revision_no=1, resettable=True,
    )
    override_rev = ProtectedResourceRevision(
        id=generate_snowflake_id(), resource_id=resource.id, revision_no=1,
        content_jsonb={"content": "Always answer in English."},
        is_default=False, status="ACTIVE",
    )

    resource_query = MagicMock()
    resource_query.filter.return_value.first.return_value = resource
    revision_query = MagicMock()
    revision_query.filter.return_value.first.return_value = override_rev

    db = MagicMock()

    def query_mock(model):
        if model is ProtectedResource:
            return resource_query
        if model is ProtectedResourceRevision:
            return revision_query
        return MagicMock()

    db.query.side_effect = query_mock

    rendered = registry.render_effective(db, workspace_id, "cosa", "system", None)

    assert rendered == "Always answer in English."


def test_render_effective_raises_for_unknown_domain_name():
    registry = PromptRegistry.get_instance()
    registry.reload()
    db = MagicMock()

    with pytest.raises(KeyError):
        registry.render_effective(db, 1, "unknown_domain", "missing", None)
