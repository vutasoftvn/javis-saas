import pytest
import yaml

from agentos.core.context_builder import ContextBuilder, DEFAULT_SYSTEM_POLICY
from agentos.core.models import TaskContext
from agentos.memory.models import MemoryItem, MemoryKind
from agentos.memory.retriever import MemoryRetriever
from agentos.memory.store import InMemoryMemoryStore
from agentos.skills.instruction_loader import SkillInstructionLoader
from agentos.skills.registry import SkillRegistry as SkillRegistryForRouter
from agentos.skills.router import SkillRouter
from agentos.tools.registry import ToolRegistry, ToolSpec


async def _noop(arguments: dict) -> dict:
    return {}


def _write_skill(root, skill_id: str, instructions: str) -> None:
    skill_dir = root / skill_id.replace(".", "-")
    skill_dir.mkdir(parents=True)
    manifest = {
        "apiVersion": "agentos.ai/v1",
        "kind": "Skill",
        "metadata": {"id": skill_id, "name": skill_id, "version": "1.0.0", "description": "d"},
        "publisher": {"name": "internal", "type": "official"},
        "source": {"type": "local", "path": str(skill_dir)},
        "capability": {"domain": "core", "category": "review", "intents": ["weekly review"]},
        "runtime": {"entrypoint": "SKILL.md", "tools": []},
        "permissions": {"filesystem": "workspace", "network": "none", "business_write": False},
        "risk": {"level": "low"},
        "trust": {"tier": "T0", "security_scan": "passed"},
        "quality": {"eval_score": 0.9, "success_rate": 0.8},
    }
    (skill_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    (skill_dir / "SKILL.md").write_text(instructions, encoding="utf-8")


@pytest.mark.asyncio
async def test_build_includes_registered_tool_names_and_default_policy():
    registry = ToolRegistry()
    registry.register(ToolSpec(name="echo", description="d", handler=_noop))
    builder = ContextBuilder(registry)
    task = TaskContext(goal="say hi", agent_key="fake", workspace_id="ws1")

    context = await builder.build(task)

    assert context.task == task
    assert context.tool_names == ["echo"]
    assert context.system_policy == DEFAULT_SYSTEM_POLICY


@pytest.mark.asyncio
async def test_build_without_memory_retriever_returns_empty_snippets():
    registry = ToolRegistry()
    builder = ContextBuilder(registry)
    task = TaskContext(goal="say hi", agent_key="fake", workspace_id="ws1")

    context = await builder.build(task)

    assert context.memory_snippets == []


@pytest.mark.asyncio
async def test_build_populates_memory_snippets_from_retriever():
    registry = ToolRegistry()
    store = InMemoryMemoryStore()
    await store.put(
        MemoryItem(workspace_id="ws1", agent_key="fake", kind=MemoryKind.EPISODIC, content="closed acme corp deal")
    )
    retriever = MemoryRetriever(store)
    builder = ContextBuilder(registry, memory_retriever=retriever)
    task = TaskContext(goal="follow up acme corp deal", agent_key="fake", workspace_id="ws1")

    context = await builder.build(task)

    assert context.memory_snippets == ["closed acme corp deal"]


@pytest.mark.asyncio
async def test_build_without_skill_router_returns_empty_skill_instructions():
    registry = ToolRegistry()
    builder = ContextBuilder(registry)
    task = TaskContext(goal="say hi", agent_key="fake", workspace_id="ws1")

    context = await builder.build(task)

    assert context.skill_instructions == []


@pytest.mark.asyncio
async def test_build_populates_skill_instructions_when_router_matches(tmp_path):
    _write_skill(tmp_path, "core.weekly-review", "Do the weekly review steps.")
    skill_registry = SkillRegistryForRouter()
    skill_registry.discover(tmp_path)
    router = SkillRouter(skill_registry)
    loader = SkillInstructionLoader(skill_registry)
    tool_registry = ToolRegistry()
    builder = ContextBuilder(tool_registry, skill_router=router, skill_instruction_loader=loader)
    task = TaskContext(goal="run my weekly review", agent_key="fake", workspace_id="ws1")

    context = await builder.build(task)

    assert context.skill_instructions == ["Do the weekly review steps."]
