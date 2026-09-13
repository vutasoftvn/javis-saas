import pytest

from apps.cosa.assets.authoring_service import AuthoringService
from apps.cosa.assets.evaluation_service import EvaluationService
from packages.agent.assets.contracts import (
    AssetLifecycle,
    AssetScope,
)
from packages.agent.assets.repository import InMemoryWorkspaceAssetRepository


@pytest.mark.asyncio
async def test_full_publish_lifecycle_transition():
    repo = InMemoryWorkspaceAssetRepository()
    eval_svc = EvaluationService(repo)
    auth_svc = AuthoringService(repo, eval_svc)

    draft = await auth_svc.create_agent_draft(
        workspace_id="ws-1",
        asset_id="agent.writer.1",
        version="0.1.0",
        name="Content Writer",
        description="Writes content",
        content={"instructions": "Write clearly."},
        scope=AssetScope.workspace(),
        created_by="founder-1",
    )
    assert draft.lifecycle == AssetLifecycle.DRAFT

    # Transition to EVALUATING -> REVIEW_REQUIRED via evaluation
    eval_res = await eval_svc.evaluate(
        workspace_id="ws-1",
        asset_id=draft.asset_id,
        version=draft.version,
    )
    assert eval_res.status == "PASS"

    version_state = await repo.get_version("ws-1", draft.asset_id, draft.version)
    assert version_state is not None
    assert version_state.lifecycle == AssetLifecycle.REVIEW_REQUIRED

    # Publish with company command ref -> PUBLISHED
    published = await auth_svc.publish(
        workspace_id="ws-1",
        asset_id=draft.asset_id,
        expected_hash=draft.definition_hash,
        company_command_ref="company-cmd-123",
    )
    assert published.lifecycle == AssetLifecycle.PUBLISHED
