import pytest

from apps.cosa.assets.authoring_service import AuthoringService, WorkflowPublishDisabledError
from apps.cosa.assets.evaluation_service import EvaluationService
from packages.agent.assets.contracts import (
    AssetKind,
    AssetNotEvaluatedError,
    AssetNotFoundError,
    AssetScope,
    BuiltinAssetReadOnlyError,
    PinnedAssetIdentity,
    WorkspaceAssetDraft,
)
from packages.agent.assets.repository import InMemoryWorkspaceAssetRepository
from packages.agent.workflows.repository import InMemoryWorkflowDefinitionRepository


@pytest.fixture
def repo():
    return InMemoryWorkspaceAssetRepository()


@pytest.fixture
def evaluation_service(repo):
    return EvaluationService(repo)


@pytest.fixture
def workflow_definition_repository():
    return InMemoryWorkflowDefinitionRepository()


@pytest.fixture
def authoring_service(repo, evaluation_service, workflow_definition_repository):
    return AuthoringService(
        repo,
        evaluation_service,
        workflow_definition_repository=workflow_definition_repository,
    )


@pytest.mark.asyncio
async def test_builtin_edit_is_rejected_and_clone_preserves_origin(authoring_service, repo):
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

    # Pre-seed the source asset so clone has an immutable default to copy from
    await repo.create_draft(
        workspace_id="ws-1",
        draft=WorkspaceAssetDraft(
            asset_id=builtin_identity.asset_id,
            version=builtin_identity.version,
            name="Finance Officer",
            description="Builtin finance officer",
            kind=AssetKind.AGENT,
            content={"instructions": "finance officer instructions", "model": "gpt-4o"},
            scope=AssetScope.workspace(),
            created_by="system",
        ),
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
async def test_clone_nonexistent_source_is_rejected(authoring_service):
    nonexistent_identity = PinnedAssetIdentity(
        kind=AssetKind.AGENT,
        asset_id="nonexistent.asset",
        version="1.0.0",
        definition_hash="sha256:nonexistent",
    )
    with pytest.raises(AssetNotFoundError, match=r"not found for clone"):
        await authoring_service.clone(
            workspace_id="ws-1",
            source=nonexistent_identity,
            target_scope=AssetScope.workspace(),
            created_by="founder-1",
        )


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


@pytest.mark.asyncio
async def test_publish_resolves_latest_version_not_fixed_010(authoring_service, evaluation_service):
    # Create draft with version 2.5.0
    draft = await authoring_service.create_agent_draft(
        workspace_id="ws-1",
        asset_id="agent.analyst.v2",
        version="2.5.0",
        name="Custom Analyst V2",
        description="Analyst version 2.5.0",
        content={"instructions": "analyze financial data v2", "model": "gpt-4o"},
        scope=AssetScope.workspace(),
        created_by="founder-1",
    )

    # Evaluate the version
    eval_result = await authoring_service.evaluate_draft("ws-1", draft.asset_id, "2.5.0")
    assert eval_result["status"] == "PASS"

    # Publish without passing version: should automatically resolve 2.5.0 as latest
    published = await authoring_service.publish(
        workspace_id="ws-1",
        asset_id=draft.asset_id,
        expected_hash=draft.definition_hash,
        company_command_ref="cmd-founder-v2",
    )
    assert published.version == "2.5.0"
    assert published.lifecycle.value == "PUBLISHED"


@pytest.mark.asyncio
async def test_valid_workflow_evaluates_and_publishes_successfully(
    authoring_service,
    evaluation_service,
    workflow_definition_repository,
):
    wf_draft = await authoring_service.create_workflow_draft(
        workspace_id="ws-1",
        asset_id="wf.valid.1",
        version="1.0.0",
        name="Valid Workflow",
        description="A valid V1 workflow",
        content={
            "id": "wf.valid.1",
            "version": "1.0.0",
            "steps": [
                {
                    "id": "step_det",
                    "type": "deterministic",
                    "handler": "pass_through",
                }
            ],
        },
        scope=AssetScope.workspace(),
        created_by="founder-1",
    )

    # 1. Evaluate valid workflow
    eval_result = await authoring_service.evaluate_draft("ws-1", wf_draft.asset_id, "1.0.0")
    assert eval_result["status"] == "PASS"

    # 2. Publish with signed Company founder command
    published = await authoring_service.publish(
        workspace_id="ws-1",
        asset_id=wf_draft.asset_id,
        expected_hash=wf_draft.definition_hash,
        company_command_ref="cmd-founder-valid-wf",
    )
    assert published.lifecycle.value == "PUBLISHED"
    definition = await workflow_definition_repository.get_definition(
        wf_draft.asset_id,
        wf_draft.version,
        workspace_id="ws-1",
    )
    assert definition is not None
    assert definition.definition_hash == wf_draft.definition_hash


@pytest.mark.asyncio
async def test_invalid_workflow_fails_evaluation_and_blocks_publish(authoring_service, evaluation_service):
    wf_draft = await authoring_service.create_workflow_draft(
        workspace_id="ws-1",
        asset_id="wf.invalid.1",
        version="1.0.0",
        name="Invalid Workflow",
        description="An invalid workflow with unregistered handler",
        content={
            "id": "wf.invalid.1",
            "version": "1.0.0",
            "steps": [
                {
                    "id": "step_bad",
                    "type": "deterministic",
                    "handler": "non_existent_unregistered_handler",
                }
            ],
        },
        scope=AssetScope.workspace(),
        created_by="founder-1",
    )

    # 1. Evaluation should fail due to unregistered handler
    eval_result = await authoring_service.evaluate_draft("ws-1", wf_draft.asset_id, "1.0.0")
    assert eval_result["status"] == "FAIL"

    # 2. Publish should be rejected with WorkflowPublishDisabledError
    with pytest.raises(WorkflowPublishDisabledError):
        await authoring_service.publish(
            workspace_id="ws-1",
            asset_id=wf_draft.asset_id,
            expected_hash=wf_draft.definition_hash,
            company_command_ref="cmd-founder-invalid-wf",
        )


@pytest.mark.asyncio
async def test_workflow_kind_is_preserved_without_name_heuristics(authoring_service, evaluation_service):
    workflow = await authoring_service.create_workflow_draft(
        workspace_id="ws-1",
        asset_id="sales-flow",
        version="1.0.0",
        name="Sales Flow",
        description="A malformed workflow whose asset id has no workflow marker",
        content={"id": "sales-flow", "version": "1.0.0"},
        scope=AssetScope.workspace(),
        created_by="founder-1",
    )

    evaluation = await evaluation_service.evaluate(
        workspace_id="ws-1",
        asset_id=workflow.asset_id,
        version=workflow.version,
    )

    assert evaluation.status == "FAIL"
    assert any("workflow" in error.lower() for error in evaluation.structural_result["errors"])


@pytest.mark.asyncio
async def test_publish_uses_the_exact_evaluated_version(authoring_service, evaluation_service):
    newer = await authoring_service.create_agent_draft(
        workspace_id="ws-1",
        asset_id="agent.versioned",
        version="0.10.0",
        name="Versioned Agent",
        description="Semver ordering regression",
        content={"instructions": "version 0.10.0"},
        scope=AssetScope.workspace(),
        created_by="founder-1",
    )
    await authoring_service.create_agent_draft(
        workspace_id="ws-1",
        asset_id="agent.versioned",
        version="0.2.0",
        name="Versioned Agent",
        description="Older semver but lexically later",
        content={"instructions": "version 0.2.0"},
        scope=AssetScope.workspace(),
        created_by="founder-1",
    )
    await evaluation_service.evaluate("ws-1", newer.asset_id, newer.version)

    published = await authoring_service.publish(
        workspace_id="ws-1",
        asset_id=newer.asset_id,
        version=newer.version,
        expected_hash=newer.definition_hash,
        company_command_ref="cmd-versioned-publish",
    )

    assert published.version == "0.10.0"
