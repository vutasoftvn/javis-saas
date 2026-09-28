"""C1 — clone agent built-in thành agent workspace + luật evaluation AGENT.

Spec: docs/superpowers/specs/2026-09-27-agent-clone-executor-design.md §2-§3.
"""

from __future__ import annotations

import pytest
from agent.assets.contracts import (
    AssetKind,
    AssetLifecycle,
    AssetScope,
    PinnedAssetIdentity,
)
from agent.assets.repository import InMemoryWorkspaceAssetRepository
from agent.contracts.spec import AgentSpec
from agent.registry.repository import InMemorySpecRegistryRepository

from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS
from apps.cosa.assets.authoring_service import AuthoringService
from apps.cosa.assets.evaluation_service import EvaluationService
from apps.cosa.assets.workspace_agent import (
    WorkspaceAgentContent,
    WorkspaceAgentError,
    build_effective_spec,
    resolve_builtin_origin,
)

WS = "ws-c1"
OPS = AGENT_PROFILE_SPECS["operations"]


@pytest.fixture
def repo() -> InMemoryWorkspaceAssetRepository:
    return InMemoryWorkspaceAssetRepository()


@pytest.fixture
def registry() -> InMemorySpecRegistryRepository:
    return InMemorySpecRegistryRepository()


@pytest.fixture
def evaluation(repo, registry) -> EvaluationService:
    return EvaluationService(repo, spec_registry=registry)


@pytest.fixture
def authoring(repo, evaluation, registry) -> AuthoringService:
    return AuthoringService(repo, evaluation, spec_registry=registry)


def _builtin_ref(spec: AgentSpec = OPS, *, version: str = "", definition_hash: str = ""):
    return PinnedAssetIdentity(
        kind=AssetKind.AGENT,
        asset_id=spec.id,
        version=version,
        definition_hash=definition_hash,
    )


async def _clone(authoring: AuthoringService, command_id: str = "cmd-1", **kw):
    return await authoring.clone(
        workspace_id=WS,
        source=_builtin_ref(**kw),
        target_scope=AssetScope.workspace(),
        created_by="founder-1",
        command_id=command_id,
        name="Vận hành Sao Mai",
        description="Agent vận hành riêng",
    )


async def _edit(authoring: AuthoringService, draft, **changes):
    content = {**draft.content_json, **changes}
    return await authoring.edit(
        WS,
        PinnedAssetIdentity(
            kind=AssetKind.AGENT,
            asset_id=draft.asset_id,
            version=draft.version,
            definition_hash=draft.definition_hash,
        ),
        content,
    )


async def _codes(evaluation: EvaluationService, draft) -> tuple[str, list[str]]:
    res = await evaluation.evaluate(WS, draft.asset_id, draft.version)
    return res.status, res.structural_result["reason_codes"]


# --- Bước 2: clone built-in ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_clone_builtin_pins_current_origin_with_lineage(authoring) -> None:
    draft = await _clone(authoring)

    assert draft.asset_id == "custom.operations.cmd-1"
    assert draft.version == "0.1.0"
    assert draft.kind == AssetKind.AGENT
    assert draft.lifecycle == AssetLifecycle.DRAFT
    assert draft.scope == AssetScope.workspace()
    assert draft.origin is not None
    assert (draft.origin.asset_id, draft.origin.version, draft.origin.definition_hash) == (
        OPS.id,
        OPS.version,
        OPS.compute_hash(),
    )
    content = draft.content_json
    assert content["schema"] == "workspace_agent.v1"
    assert content["origin"] == {
        "profile_key": "operations",
        "spec_id": OPS.id,
        "version": OPS.version,
        "definition_hash": OPS.compute_hash(),
    }
    assert content["name"] == "Vận hành Sao Mai"
    assert content["capability_refs"] == list(OPS.capability_refs)
    # Override manifest không mang model policy / tier / instructions gốc.
    assert not {"model_policy", "autonomy_level", "instructions"} & set(content)


@pytest.mark.asyncio
async def test_clone_is_idempotent_per_command_and_distinct_per_command(authoring) -> None:
    first = await _clone(authoring, "cmd-1")
    again = await _clone(authoring, "cmd-1")
    other = await _clone(authoring, "cmd-2")

    assert again.definition_hash == first.definition_hash
    assert again.asset_id == first.asset_id
    assert other.asset_id == "custom.operations.cmd-2"


@pytest.mark.asyncio
async def test_clone_rejects_wrong_pin_and_non_cloneable_builtin(authoring) -> None:
    with pytest.raises(WorkspaceAgentError) as wrong_hash:
        await _clone(authoring, version=OPS.version, definition_hash="sha256:not-the-builtin")
    assert wrong_hash.value.reason_code == "AGENT_ORIGIN_UNAVAILABLE"

    # founder_assistant / customer_support không phải agent vận hành clone được → không đi nhánh
    # built-in, rơi về clone asset workspace và không tìm thấy nguồn.
    with pytest.raises(Exception, match="not found for clone"):
        await _clone(authoring, spec=AGENT_PROFILE_SPECS["customer_support"])


@pytest.mark.asyncio
async def test_origin_pin_resolves_older_version_from_registry(registry) -> None:
    older = OPS.model_copy(
        update={
            "version": "0.9.0",
            "instructions": "phiên bản cũ",
            "prompt_ref": None,
            "model_policy_ref": None,
        }
    )
    from agent.registry.publisher import publish_agent_spec

    record = await publish_agent_spec(older.with_hash(), repository=registry, publisher="test")
    profile, spec, pinned_hash = await resolve_builtin_origin(
        registry, OPS.id, "0.9.0", record.definition_hash
    )
    assert profile == "operations"
    assert spec.version == "0.9.0" and spec.instructions == "phiên bản cũ"
    assert pinned_hash == record.definition_hash


# --- Bước 3: evaluation AGENT ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_narrowed_clone_with_addendum_passes(authoring, evaluation) -> None:
    draft = await _clone(authoring)
    edited = await _edit(
        authoring,
        draft,
        name="Vận hành gọn",
        instructions_addendum="Luôn trả lời ngắn gọn, ưu tiên việc tuần này.",
        capability_refs=[c for c in OPS.capability_refs if c != "operations.task.advance"],
    )
    assert await _codes(evaluation, edited) == ("PASS", [])
    stored = await authoring._repository.get_version(WS, edited.asset_id, edited.version)
    assert stored.lifecycle == AssetLifecycle.REVIEW_REQUIRED


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        (
            {"capability_refs": [*OPS.capability_refs, "finance.transaction.record"]},
            "AGENT_CAPABILITY_ESCALATION",
        ),
        ({"model_policy": {"model": "gpt-5"}}, "AGENT_MANIFEST_INVALID"),
        ({"autonomy_level": "L3"}, "AGENT_MANIFEST_INVALID"),
        ({"instructions": "thay toàn bộ instructions"}, "AGENT_MANIFEST_INVALID"),
        ({"name": ""}, "AGENT_NAME_INVALID"),
        ({"name": "x" * 81}, "AGENT_NAME_INVALID"),
        ({"description": "d" * 501}, "AGENT_DESCRIPTION_TOO_LONG"),
        ({"instructions_addendum": "a" * 4001}, "AGENT_ADDENDUM_TOO_LONG"),
        (
            {"instructions_addendum": "dùng key sk-abcdefghijklmnopqrstuvwxyz0123"},
            "AGENT_SECRET_DETECTED",
        ),
        ({"description": "Authorization: Bearer abc"}, "AGENT_SECRET_DETECTED"),
    ],
)
@pytest.mark.asyncio
async def test_each_agent_rule_rejects_with_its_code(authoring, evaluation, changes, code) -> None:
    draft = await _clone(authoring)
    edited = await _edit(authoring, draft, **changes)
    status, codes = await _codes(evaluation, edited)
    assert status == "FAIL"
    assert code in codes


@pytest.mark.asyncio
async def test_origin_cannot_be_swapped_by_edit(authoring, evaluation) -> None:
    draft = await _clone(authoring)
    finance = AGENT_PROFILE_SPECS["finance"]
    edited = await _edit(
        authoring,
        draft,
        origin={
            "profile_key": "finance",
            "spec_id": finance.id,
            "version": finance.version,
            "definition_hash": finance.compute_hash(),
        },
        capability_refs=list(finance.capability_refs),
    )
    status, codes = await _codes(evaluation, edited)
    assert status == "FAIL"
    assert "AGENT_ORIGIN_MISMATCH" in codes


@pytest.mark.asyncio
async def test_origin_builtin_must_still_exist(authoring, evaluation, repo) -> None:
    draft = await _clone(authoring)
    # Built-in đã nâng version và bản pin không còn trong registry → không resolve được gốc.
    stored = repo._versions[(WS, draft.asset_id, draft.version)]
    stored.origin = type(stored.origin)(
        kind="CLONE", asset_id=OPS.id, version="0.0.1", definition_hash="sha256:gone"
    )
    stored.content_json = {
        **stored.content_json,
        "origin": {
            **stored.content_json["origin"],
            "version": "0.0.1",
            "definition_hash": "sha256:gone",
        },
    }
    status, codes = await _codes(evaluation, stored)
    assert status == "FAIL"
    assert "AGENT_ORIGIN_UNAVAILABLE" in codes


@pytest.mark.asyncio
async def test_scratch_agent_without_builtin_lineage_is_rejected(authoring, evaluation) -> None:
    draft = await authoring.create_agent_draft(
        workspace_id=WS,
        asset_id="agent.scratch",
        version="0.1.0",
        name="Scratch",
        description=None,
        content={"instructions": "làm mọi thứ", "capability_refs": []},
        scope=AssetScope.workspace(),
        created_by="founder-1",
    )
    assert await _codes(evaluation, draft) == ("FAIL", ["AGENT_ORIGIN_REQUIRED"])


@pytest.mark.asyncio
async def test_publish_requires_pass_for_the_exact_hash(authoring, evaluation) -> None:
    draft = await _clone(authoring)
    await _codes(evaluation, draft)
    published = await authoring.publish(
        WS, draft.asset_id, draft.definition_hash, company_command_ref="cmd-pub", version="0.1.0"
    )
    assert published.lifecycle == AssetLifecycle.PUBLISHED


# --- Spec hiệu lực ---------------------------------------------------------------------------


def test_effective_spec_only_overrides_allowed_fields() -> None:
    kept = [c for c in OPS.capability_refs if c != "operations.task.advance"]
    manifest = WorkspaceAgentContent.model_validate(
        {
            "schema": "workspace_agent.v1",
            "origin": {
                "profile_key": "operations",
                "spec_id": OPS.id,
                "version": OPS.version,
                "definition_hash": OPS.compute_hash(),
            },
            "name": "Vận hành gọn",
            "description": "",
            "instructions_addendum": "Ưu tiên việc tuần này.",
            "capability_refs": list(reversed(kept)),
        }
    )
    spec = build_effective_spec(
        OPS,
        manifest,
        workspace_id=WS,
        asset_id="custom.operations.cmd-1",
        version="0.1.0",
        asset_definition_hash="sha256:asset",
    )
    assert spec.id == f"workspace.{WS}.custom.operations.cmd-1"
    assert spec.version == "0.1.0"
    assert spec.instructions.startswith(OPS.instructions)
    assert spec.instructions.endswith("Ưu tiên việc tuần này.")
    assert spec.capability_refs == kept  # thứ tự của gốc, không phải của manifest
    assert "operations.task.advance" not in spec.capability_refs
    for field in (
        "model_policy",
        "autonomy_level",
        "prompt_ref",
        "model_policy_ref",
        "pinned_skills",
        "model_input_capability_ref",
        "limits",
    ):
        assert getattr(spec, field) == getattr(OPS, field), field
    assert spec.metadata["origin_agent_spec_id"] == OPS.id
    assert spec.definition_hash == spec.compute_hash()
