import pytest

from apps.cosa.assets.authoring_service import AuthoringService, WorkflowPublishDisabledError
from apps.cosa.assets.evaluation_service import EvaluationService
from packages.agent.assets.contracts import (
    AssetKind,
    AssetNotEvaluatedError,
    AssetScope,
    BuiltinAssetReadOnlyError,
    PinnedAssetIdentity,
)
from packages.agent.assets.repository import InMemoryWorkspaceAssetRepository


@pytest.fixture
def repo():
    return InMemoryWorkspaceAssetRepository()


@pytest.fixture
def evaluation_service(repo):
    return EvaluationService(repo)


@pytest.fixture
def authoring_service(repo, evaluation_service):
    return AuthoringService(repo, evaluation_service)


@pytest.mark.asyncio
async def test_builtin_edit_is_rejected_and_clone_preserves_origin(authoring_service):
    builtin_identity = PinnedAssetIdentity(
        kind=AssetKind.AGENT,
        asset_id="builtin.finance_officer",
        version="1.0.0",
        definition_hash="sha256:builtinfinancehash111111111111111111111111111111111111111111111",
    )

    with pytest.raises(BuiltinAssetReadOnlyError):
        await authoring_service.edit(
            workspace_id="ws-1",
            identity=builtin_identity,
            content={"instructions": "mutate builtin"},
        )

    clone = await authoring_service.clone(
        workspace_id="ws-1",
        source=builtin_identity,
        target_scope=AssetScope.workspace(),
        created_by="founder-1",
    )

    assert clone.origin is not None
    assert clone.origin.definition_hash == builtin_identity.definition_hash
    assert clone.origin.asset_id == builtin_identity.asset_id
    assert clone.lifecycle.value == "DRAFT"


@pytest.mark.asyncio
async def test_publish_requires_passing_evaluation_and_founder_command(authoring_service, evaluation_service):
    draft = await authoring_service.create_agent_draft(
        workspace_id="ws-1",
        asset_id="agent.analyst.1",
        version="0.1.0",
        name="Custom Analyst",
        description="Analyst agent",
        content={"instructions": "Provide accurate summaries.", "capability_refs": []},
        scope=AssetScope.workspace(),
        created_by="founder-1",
    )

    # Chưa đánh giá mà đòi publish -> phải raise AssetNotEvaluatedError
    with pytest.raises(AssetNotEvaluatedError):
        await authoring_service.publish(
            workspace_id="ws-1",
            asset_id=draft.asset_id,
            expected_hash=draft.definition_hash,
            company_command_ref="cmd-founder-1",
        )

    # Thực hiện đánh giá pass
    await evaluation_service.evaluate(
        workspace_id="ws-1",
        asset_id=draft.asset_id,
        version=draft.version,
    )

    # Sau khi có passing evaluation -> publish thành công
    published = await authoring_service.publish(
        workspace_id="ws-1",
        asset_id=draft.asset_id,
        expected_hash=draft.definition_hash,
        company_command_ref="cmd-founder-1",
    )
    assert published.lifecycle.value == "PUBLISHED"


@pytest.mark.asyncio
async def test_project_sandbox_rejects_external_capabilities(authoring_service):
    with pytest.raises(ValueError, match=r"(?i)sandbox"):
        await authoring_service.create_agent_draft(
            workspace_id="ws-1",
            asset_id="sandbox.agent.1",
            version="0.1.0",
            name="Sandbox Agent",
            description="Testing sandbox",
            content={"instructions": "do task", "capability_refs": ["system.external.io"]},
            scope=AssetScope.project_sandbox("p-1"),
            created_by="founder-1",
        )


@pytest.mark.asyncio
async def test_workflow_publish_is_disabled_in_v1_early_phase(authoring_service):
    wf_draft = await authoring_service.create_workflow_draft(
        workspace_id="ws-1",
        asset_id="wf.custom.1",
        version="0.1.0",
        name="Custom Workflow",
        description="Draft workflow",
        content={"nodes": [], "edges": []},
        scope=AssetScope.workspace(),
        created_by="founder-1",
    )

    with pytest.raises(WorkflowPublishDisabledError):
        await authoring_service.publish(
            workspace_id="ws-1",
            asset_id=wf_draft.asset_id,
            expected_hash=wf_draft.definition_hash,
            company_command_ref="cmd-wf-1",
        )
