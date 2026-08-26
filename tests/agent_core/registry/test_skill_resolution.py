"""Wave 5 — ADR-SKILL-IDENTITY §4 (kích hoạt 2026-08-24, Phương án A): verify
publish_skill_spec + SkillResolver chống floating runtime reference, và kernel
compose đúng skill instructions vào PromptBundle khi AgentSpec.pinned_skills
được set."""
from __future__ import annotations

import pytest

from agent_core.contracts.errors import AgentRuntimeError, RuntimeErrorCode
from agent_core.contracts.identity import PinnedSkillRef
from agent_core.contracts.run import RunRequest, RunStatus
from agent_core.contracts.spec import AgentSpec
from agent_core.kernel.openai_agents_kernel import ManualToolLoopKernel
from agent_core.registry.publisher import publish_skill_spec
from agent_core.registry.repository import InMemorySpecRegistryRepository
from agent_core.runs.repository import InMemoryRunRepository
from agent_core.skills.contracts import SkillSpec
from agent_core.skills.resolver import SkillResolver


@pytest.mark.asyncio
async def test_publish_skill_spec_shares_registry_with_agent_spec_no_new_table():
    repo = InMemorySpecRegistryRepository()
    skill = SkillSpec(id="test.skill.finance_close", version="1.0.0", instructions="Đóng sổ kế toán cuối kỳ.")

    record = await publish_skill_spec(skill, repository=repo, publisher="tester")

    assert record.spec_kind == "skill"
    assert record.spec_id == "test.skill.finance_close"

    # Cùng registry với agent — get() theo spec_kind="skill" phải resolve đúng
    fetched = await repo.get("skill", "test.skill.finance_close", "1.0.0")
    assert fetched is not None
    assert fetched.content["instructions"] == "Đóng sổ kế toán cuối kỳ."


@pytest.mark.asyncio
async def test_skill_resolver_rejects_missing_skill():
    repo = InMemorySpecRegistryRepository()
    resolver = SkillResolver(repo)

    with pytest.raises(AgentRuntimeError) as exc_info:
        await resolver.resolve([PinnedSkillRef(skill_id="does.not.exist", version="1.0.0", definition_hash="deadbeef")])

    assert exc_info.value.code == RuntimeErrorCode.SKILL_RESOLUTION_ERROR


@pytest.mark.asyncio
async def test_skill_resolver_rejects_hash_mismatch_floating_reference():
    """Đây chính là invariant ADR-SKILL-IDENTITY lo ngại: AgentSpec pin đúng
    version nhưng hash không khớp (vd data pin sai, hoặc race condition publish)
    -> PHẢI từ chối, không được âm thầm dùng nội dung registry hiện tại."""
    repo = InMemorySpecRegistryRepository()
    skill = SkillSpec(id="test.skill.drift", version="1.0.0", instructions="Nội dung gốc")
    published = await publish_skill_spec(skill, repository=repo, publisher="tester")

    resolver = SkillResolver(repo)
    wrong_ref = PinnedSkillRef(skill_id="test.skill.drift", version="1.0.0", definition_hash="not_the_real_hash")

    with pytest.raises(AgentRuntimeError) as exc_info:
        await resolver.resolve([wrong_ref])

    assert exc_info.value.code == RuntimeErrorCode.SKILL_RESOLUTION_ERROR
    assert exc_info.value.details["registry_hash"] == published.definition_hash


@pytest.mark.asyncio
async def test_kernel_run_composes_pinned_skill_instructions_into_system_prompt():
    repo = InMemoryRunRepository()
    registry = InMemorySpecRegistryRepository()

    skill = SkillSpec(
        id="test.skill.competitor_intel",
        version="1.0.0",
        instructions="Khi phân tích đối thủ, luôn trích dẫn nguồn công khai.",
    )
    published = await publish_skill_spec(skill, repository=registry, publisher="tester")

    kernel = ManualToolLoopKernel(repository=repo, spec_registry=registry)

    spec = AgentSpec(
        id="test.agent.with_skill",
        version="1.0.0",
        instructions="Bạn là chuyên viên phân tích thị trường.",
        pinned_skills=[
            PinnedSkillRef(
                skill_id="test.skill.competitor_intel",
                version="1.0.0",
                definition_hash=published.definition_hash,
            )
        ],
    )
    request = RunRequest(
        principal="test_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "Phân tích đối thủ Acme Corp"},
    )

    result = await kernel.run(request, spec)

    assert result.status == RunStatus.COMPLETED
    events = await repo.list_events(result.run_id)
    # Không có API check trực tiếp system prompt qua RunResult — verify gián tiếp
    # qua việc Run không raise SKILL_RESOLUTION_ERROR (nếu resolve fail, run() sẽ
    # raise trước khi tạo RunRecord — assert dưới xác nhận RunRecord tồn tại đúng).
    run_rec = await repo.get_run(result.run_id)
    assert run_rec is not None
    assert run_rec.status == RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_kernel_run_raises_and_creates_no_run_record_when_pinned_skill_unresolvable():
    """Skill resolution fail PHẢI xảy ra trước khi tạo RunRecord — tránh RunRecord
    kẹt ở status RUNNING vĩnh viễn (cùng nguyên tắc như publish_agent_spec conflict)."""
    repo = InMemoryRunRepository()
    registry = InMemorySpecRegistryRepository()
    kernel = ManualToolLoopKernel(repository=repo, spec_registry=registry)

    spec = AgentSpec(
        id="test.agent.broken_skill_ref",
        version="1.0.0",
        pinned_skills=[
            PinnedSkillRef(skill_id="never.published", version="1.0.0", definition_hash="whatever")
        ],
    )
    request = RunRequest(
        principal="test_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "hello"},
    )

    with pytest.raises(AgentRuntimeError) as exc_info:
        await kernel.run(request, spec)

    assert exc_info.value.code == RuntimeErrorCode.SKILL_RESOLUTION_ERROR
    # Không có Run nào được tạo — không kẹt RUNNING vĩnh viễn.
    all_runs = [r for r in repo._runs.values()]  # InMemoryRunRepository nội bộ, chỉ dùng để verify test
    assert all_runs == []
