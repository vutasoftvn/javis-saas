from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from agent.contracts.errors import AgentRuntimeError, RuntimeErrorCode
from agent.contracts.identity import PinnedSkillRef
from agent.conversations.repository import InMemoryConversationRepository
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository, SpecVersionHashConflictError
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent.skills.resolver import SkillResolver
from agent_testkit.fake_sdk_model import FakeSDKModel

from apps.cosa.agents import skillpack_seed
from apps.cosa.agents import seed as seed_module
from apps.cosa.agents.seed import seed_cosa_runtime_specs
from apps.cosa.agents.skillpack_seed import (
    BuiltinSkillpackSeedError,
    resolve_skillpacks_root,
    seed_builtin_skillpacks,
)
from apps.cosa.agents.specs import COSA_DEPLOYED_AGENT_SPECS
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import CosaAgentPlane, build_cosa_agent_plane

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLPACKS_ROOT = REPO_ROOT / "skillpacks"


@pytest.fixture
def mock_company_client():
    client = AsyncMock(spec=CompanyServiceClient)
    client.get.return_value = {}
    client.patch.return_value = {}
    client.post.return_value = {}
    return client


@pytest.fixture
def plane(mock_company_client) -> CosaAgentPlane:
    return build_cosa_agent_plane(
        company_client=mock_company_client,
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )


@pytest.mark.asyncio
async def test_seed_cosa_runtime_specs_resolves_all_pinned_skills(plane: CosaAgentPlane) -> None:
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
        skillpacks_root=SKILLPACKS_ROOT,
    )
    resolver = SkillResolver(plane.spec_registry)
    for agent_spec in COSA_DEPLOYED_AGENT_SPECS:
        resolved = await resolver.resolve(agent_spec.pinned_skills)
        assert [item.id for item in resolved] == [pin.skill_id for pin in agent_spec.pinned_skills]


@pytest.mark.asyncio
async def test_seed_cosa_runtime_specs_is_idempotent(plane: CosaAgentPlane) -> None:
    kwargs = {
        "spec_registry": plane.spec_registry,
        "capability_registry": plane.capability_registry,
        "skillpacks_root": SKILLPACKS_ROOT,
    }
    await seed_cosa_runtime_specs(**kwargs)
    await seed_cosa_runtime_specs(**kwargs)
    expected_count = len(list(SKILLPACKS_ROOT.rglob("manifest.yaml")))
    assert len(await plane.spec_registry.list_all(spec_kind="skill")) == expected_count


def test_resolve_skillpacks_root_uses_repository_bundle_outside_runtime_image(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("COSA_SKILLPACKS_ROOT", raising=False)

    assert resolve_skillpacks_root() == SKILLPACKS_ROOT.resolve()


def test_resolve_skillpacks_root_raises_on_missing_directory(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    with pytest.raises(BuiltinSkillpackSeedError):
        resolve_skillpacks_root(missing)


@pytest.mark.asyncio
async def test_seed_builtin_skillpacks_raises_on_missing_bundle_root(
    plane: CosaAgentPlane, tmp_path: Path
) -> None:
    missing = tmp_path / "does-not-exist"
    capability_ids = {spec.id for spec in plane.capability_registry.list_specs()}

    with pytest.raises(BuiltinSkillpackSeedError):
        await seed_builtin_skillpacks(
            plane.spec_registry,
            capability_ids=capability_ids,
            skillpacks_root=missing,
        )

    assert await plane.spec_registry.list_all(spec_kind="skill") == []


@pytest.mark.asyncio
async def test_seed_builtin_skillpacks_raises_on_contract_violation(
    plane: CosaAgentPlane, tmp_path: Path
) -> None:
    broken_pack = tmp_path / "broken-pack"
    broken_pack.mkdir()
    # manifest.yaml cố ý thiếu toàn bộ section bắt buộc (publisher, source,
    # capability, runtime, permissions, risk, trust) -> validate_skillpack_tree
    # phải báo violation, KHÔNG được publish một phần rồi mới lỗi.
    (broken_pack / "manifest.yaml").write_text(
        "apiVersion: v1\nkind: Skillpack\nmetadata:\n  id: broken.pack\n",
        encoding="utf-8",
    )
    (broken_pack / "SKILL.md").write_text(
        "---\nname: broken-pack\ndescription: broken\n---\nBody.\n",
        encoding="utf-8",
    )
    capability_ids = {spec.id for spec in plane.capability_registry.list_specs()}

    with pytest.raises(BuiltinSkillpackSeedError):
        await seed_builtin_skillpacks(
            plane.spec_registry,
            capability_ids=capability_ids,
            skillpacks_root=tmp_path,
        )

    assert await plane.spec_registry.list_all(spec_kind="skill") == []


@pytest.mark.asyncio
async def test_seed_builtin_skillpacks_propagates_immutable_version_conflict(
    plane: CosaAgentPlane, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Version/hash conflict phải giữ nguyên để caller trả 409 chính xác."""
    monkeypatch.setattr(
        skillpack_seed,
        "publish_skill_batch",
        AsyncMock(
            side_effect=SpecVersionHashConflictError(
                "skill", "core.weekly-review", "1.0.0"
            )
        ),
    )

    with pytest.raises(SpecVersionHashConflictError):
        await seed_builtin_skillpacks(
            plane.spec_registry,
            capability_ids={spec.id for spec in plane.capability_registry.list_specs()},
            skillpacks_root=SKILLPACKS_ROOT,
        )


@pytest.mark.asyncio
async def test_seed_cosa_runtime_specs_fails_closed_on_pin_hash_mismatch(
    plane: CosaAgentPlane, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pin hash sai phải khiến startup verification raise trước khi phục vụ —
    message chứa skill id, version và dấu hiệu hash mismatch (Global
    Constraints: "pin/hash mismatch" phải fail-closed, không khởi động với
    tham chiếu treo)."""
    await seed_builtin_skillpacks(
        plane.spec_registry,
        capability_ids={spec.id for spec in plane.capability_registry.list_specs()},
        skillpacks_root=SKILLPACKS_ROOT,
    )
    await seed_module.seed_cosa_agent_specs(plane.spec_registry)

    import dataclasses

    source_entry = seed_module.deployed_entries()[0]
    assert source_entry.agent_spec.pinned_skills, "test cần một AgentSpec có ít nhất 1 pin"
    original_pin = source_entry.agent_spec.pinned_skills[0]

    corrupted_spec = deepcopy(source_entry.agent_spec)
    corrupted_spec.pinned_skills = (
        PinnedSkillRef(
            skill_id=original_pin.skill_id,
            version=original_pin.version,
            definition_hash="0" * 64,
        ),
        *corrupted_spec.pinned_skills[1:],
    )
    corrupted_entry = dataclasses.replace(source_entry, agent_spec=corrupted_spec)
    monkeypatch.setattr(seed_module, "deployed_entries", lambda: (corrupted_entry,))

    with pytest.raises(AgentRuntimeError) as exc_info:
        await seed_cosa_runtime_specs(
            spec_registry=plane.spec_registry,
            capability_registry=plane.capability_registry,
            skillpacks_root=SKILLPACKS_ROOT,
        )

    assert exc_info.value.code == RuntimeErrorCode.SKILL_RESOLUTION_ERROR
    message = str(exc_info.value)
    assert original_pin.skill_id in message
    assert original_pin.version in message
    assert "hash" in message.lower()


@pytest.mark.asyncio
async def test_skillpack_batch_is_atomic_when_a_later_manifest_conflicts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Manifest thứ 2 xung đột hash với bản đã publish -> manifest thứ 1 không được hiển thị."""
    from agent.registry.models import PublishedSpecRecord
    from apps.cosa.api.skillpack_mapper import parse_skillpack_spec

    # Tree validation có test riêng; ở đây chỉ cô lập hành vi publish atomic.
    monkeypatch.setattr(skillpack_seed, "validate_skillpack_tree", lambda *a, **k: [])
    packs = ["core/weekly-review", "executive/cfo-advisor"]
    root = tmp_path / "skillpacks"
    for pack in packs:
        (root / pack).parent.mkdir(parents=True, exist_ok=True)
        import shutil

        shutil.copytree(SKILLPACKS_ROOT / pack, root / pack)
    ordered = sorted(root.rglob("manifest.yaml"))
    first_spec = parse_skillpack_spec(ordered[0].parent)
    second_spec = parse_skillpack_spec(ordered[1].parent)

    registry = InMemorySpecRegistryRepository()
    # Bản đã publish cho skill thứ 2 với nội dung khác -> conflict khi batch tới nó.
    await registry.publish(
        PublishedSpecRecord(
            spec_kind="skill",
            spec_id=second_spec.id,
            version=second_spec.version,
            definition_hash="f" * 64,
            content={},
            publisher="test",
        )
    )

    with pytest.raises(SpecVersionHashConflictError):
        await seed_builtin_skillpacks(registry, capability_ids=set(), skillpacks_root=root)

    assert await registry.get("skill", first_spec.id, first_spec.version) is None


@pytest.mark.asyncio
async def test_skillpack_batch_publishes_nothing_when_one_manifest_cannot_parse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import shutil

    root = tmp_path / "skillpacks"
    shutil.copytree(SKILLPACKS_ROOT / "executive/cfo-advisor", root / "executive/cfo-advisor")
    registry = InMemorySpecRegistryRepository()
    monkeypatch.setattr(skillpack_seed, "validate_skillpack_tree", lambda *a, **k: [])
    (root / "broken").mkdir()
    (root / "broken" / "manifest.yaml").write_text("not: [valid", encoding="utf-8")
    with pytest.raises(BuiltinSkillpackSeedError):
        await seed_builtin_skillpacks(registry, capability_ids=set(), skillpacks_root=root)

    assert await registry.list_all("skill") == []
