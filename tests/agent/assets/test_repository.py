import pytest

from packages.agent.assets.contracts import (
    AssetImmutableError,
    AssetKind,
    AssetScope,
    AssetScopeError,
    PinnedAssetIdentity,
    WorkspaceAssetDraft,
)
from packages.agent.assets.repository import InMemoryWorkspaceAssetRepository


@pytest.fixture
def repo():
    return InMemoryWorkspaceAssetRepository()


def make_agent_draft(scope: AssetScope | None = None) -> WorkspaceAssetDraft:
    return WorkspaceAssetDraft(
        asset_id="custom-agent-1",
        kind=AssetKind.AGENT,
        version="0.1.0",
        name="Custom Analyst Agent",
        description="Analyzes market trends",
        content={"instructions": "Be accurate and concise.", "model": "gpt-4o"},
        scope=scope or AssetScope.workspace(),
        created_by="user-123",
    )


@pytest.mark.asyncio
async def test_workspace_asset_version_cannot_be_read_from_another_workspace(repo):
    saved = await repo.create_draft(workspace_id="ws-a", draft=make_agent_draft())
    assert await repo.get_version("ws-b", saved.asset_id, saved.version) is None
    read_ws_a = await repo.get_version("ws-a", saved.asset_id, saved.version)
    assert read_ws_a is not None
    assert read_ws_a.asset_id == "custom-agent-1"


@pytest.mark.asyncio
async def test_published_version_rejects_in_place_content_change(repo):
    draft = await repo.create_draft(workspace_id="ws-a", draft=make_agent_draft())
    published = await repo.publish(workspace_id="ws-a", asset_id=draft.asset_id, expected_hash=draft.definition_hash)
    assert published.lifecycle.value == "PUBLISHED"

    with pytest.raises(AssetImmutableError):
        await repo.replace_draft_content(
            workspace_id="ws-a",
            asset_id=published.asset_id,
            version=published.version,
            content={"instructions": "tampered instructions"},
        )


@pytest.mark.asyncio
async def test_clone_to_draft_copies_content_and_records_origin(repo):
    source = PinnedAssetIdentity(
        kind=AssetKind.SKILL,
        asset_id="builtin.web_search",
        version="1.0.0",
        definition_hash="sha256:builtinwebsearchhash",
    )
    cloned = await repo.clone_to_draft(
        workspace_id="ws-a",
        source=source,
        target_scope=AssetScope.workspace(),
        source_content={"prompt": "search web query"},
        created_by="founder-1",
    )
    assert cloned.lifecycle.value == "DRAFT"
    assert cloned.origin is not None
    assert cloned.origin.asset_id == "builtin.web_search"
    assert cloned.origin.definition_hash == "sha256:builtinwebsearchhash"
    assert cloned.content_json == {"prompt": "search web query"}


@pytest.mark.asyncio
async def test_sandbox_scope_enforces_project_id(repo):
    with pytest.raises(AssetScopeError):
        # PROJECT_SANDBOX requires project_id
        AssetScope(kind="PROJECT_SANDBOX", project_id=None)

    with pytest.raises(AssetScopeError):
        # WORKSPACE scope must not have project_id
        AssetScope(kind="WORKSPACE", project_id="proj-123")
