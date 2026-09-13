import pytest

from packages.agent.assets.contracts import (
    AssetConflictError,
    AssetKind,
    AssetScope,
    WorkspaceAssetDraft,
)
from packages.agent.assets.repository import InMemoryWorkspaceAssetRepository
from packages.agent.assets.service import WorkspaceAssetService


@pytest.fixture
def service():
    repo = InMemoryWorkspaceAssetRepository()
    return WorkspaceAssetService(repo)


@pytest.mark.asyncio
async def test_service_computes_canonical_hash_and_creates_draft(service):
    draft = WorkspaceAssetDraft(
        asset_id="workflow.finance.custom",
        kind=AssetKind.WORKFLOW,
        version="0.1.0",
        name="Custom Finance Workflow",
        description="Processes invoices",
        content={"nodes": [{"id": "n1", "type": "APPROVAL_GATE"}], "edges": []},
        scope=AssetScope.workspace(),
        created_by="founder-1",
    )
    saved = await service.create_draft(workspace_id="ws-1", draft=draft)
    assert saved.definition_hash.startswith("sha256:")
    assert saved.version == "0.1.0"
    assert saved.lifecycle.value == "DRAFT"


@pytest.mark.asyncio
async def test_service_publish_validates_hash_mismatch(service):
    draft = WorkspaceAssetDraft(
        asset_id="skill.custom.1",
        kind=AssetKind.SKILL,
        version="0.1.0",
        name="Custom Skill",
        description=None,
        content={"instructions": "test instructions"},
        scope=AssetScope.workspace(),
        created_by="founder-1",
    )
    saved = await service.create_draft(workspace_id="ws-1", draft=draft)

    with pytest.raises(AssetConflictError, match="hash mismatch"):
        await service.publish(
            workspace_id="ws-1",
            asset_id=saved.asset_id,
            expected_hash="sha256:wronghash",
        )
