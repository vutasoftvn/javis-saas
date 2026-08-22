from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from agentos.core.context_builder import ContextBuilder
from agentos.core.executor import Executor
from agentos.core.model_provider import ModelProvider
from agentos.core.models import AgentRun, AgentRunStatus, TaskContext
from agentos.core.planner import Planner
from agentos.core.policy import PolicyDecision, PolicyEngine
from agentos.core.runtime import AgentRuntime
from agentos.core.trace import TraceRecorder
from agentos.memory.models import MemoryItem, MemoryKind
from agentos.memory.store import InMemoryMemoryStore
from agentos.skills.registry import SkillRegistry
from agentos.skills.router import SkillRouter
from agentos.tools.encore_client import EncoreClient
from agentos.tools.registry import ToolRegistry


from agentos.core.model_provider import ModelProvider, ModelResponse, ToolCallRequest


class FakeLLMProvider(ModelProvider):
    """Giả lập Model Provider thực hiện lập kế hoạch và gọi tool hợp lệ."""

    def __init__(self) -> None:
        self.call_count = 0

    async def generate(self, *, system_prompt: str, messages: list[dict]) -> ModelResponse:
        self.call_count += 1
        if self.call_count == 1:
            return ModelResponse(
                tool_call=ToolCallRequest(
                    tool_name="okr_cycle_create",
                    arguments={"workspaceId": 1, "title": "Q3-2026", "startDate": "2026-07-01", "endDate": "2026-09-30"}
                )
            )
        elif self.call_count == 2:
            return ModelResponse(
                tool_call=ToolCallRequest(
                    tool_name="task_create",
                    arguments={"workspaceId": 1, "title": "Xây dựng kế hoạch chi tiết Q3", "priority": "high"}
                )
            )
        else:
            return ModelResponse(
                text="Đã thiết lập thành công Chu kỳ OKR Q3-2026 và tạo Task tuần 1 cho Workspace 1."
            )


@pytest.mark.asyncio
async def test_agent_os_full_lifecycle_e2e():
    workspace_id = "ws_test_001"
    agent_key = "founder_copilot"

    # 1. Khởi tạo Memory Store & nạp Working/Semantic Memory ban đầu
    memory_store = InMemoryMemoryStore()
    await memory_store.put(
        MemoryItem(
            workspace_id=workspace_id,
            agent_key=agent_key,
            kind=MemoryKind.SEMANTIC,
            content="Mục tiêu năm 2026: Tăng trưởng doanh thu 3x qua kênh Digital.",
            importance=0.9,
        )
    )

    # 2. Khởi tạo Skill Registry & Scan toàn bộ skillpacks tại root
    skill_registry = SkillRegistry()
    skillpacks_dir = Path(__file__).resolve().parents[2] / "skillpacks"
    discovered = skill_registry.discover(skillpacks_dir)
    assert len(discovered) >= 4  # core, marketing, okr, twelve-week-year, tasks

    # 3. Router chọn skillpack cho intent "create okr cycle"
    skill_router = SkillRouter(skill_registry)
    matched_skill = skill_router.select("create okr cycle", allow_business_write=True)
    assert matched_skill is not None
    assert matched_skill.metadata.id == "operations.okr"

    # 4. Khởi tạo Tool Registry kết nối với Mocked Encore Client
    mock_encore = MagicMock(spec=EncoreClient)
    mock_encore.post = AsyncMock(side_effect=[
        {"id": 101, "title": "Q3-2026", "status": "active"},
        {"id": 202, "title": "Xây dựng kế hoạch chi tiết Q3", "status": "todo"},
    ])
    mock_encore.get = AsyncMock(return_value={"items": []})

    tool_registry = ToolRegistry()
    tool_registry.register_cluster_tools(encore_client=mock_encore)

    # 5. Policy Engine kiểm tra quyền cho phép
    from agentos.core.policy import PermissionClass
    policy_engine = PolicyEngine(
        table={
            PermissionClass.READ_LOCAL: PolicyDecision.ALLOW,
            PermissionClass.MODIFY_BUSINESS_DATA: PolicyDecision.ALLOW,
        }
    )
    decision = policy_engine.evaluate(PermissionClass.MODIFY_BUSINESS_DATA)
    assert decision == PolicyDecision.ALLOW

    # 6. Khởi tạo và thực thi AgentRuntime với Fake LLM
    llm_provider = FakeLLMProvider()
    runtime = AgentRuntime(
        model_provider=llm_provider, tool_registry=tool_registry, policy_engine=policy_engine
    )

    task = TaskContext(
        workspace_id=workspace_id,
        agent_key=agent_key,
        goal="Thiết lập chu kỳ OKR Q3-2026 và tạo task tuần 1",
    )

    result = await runtime.run(task)

    # 7. Kiểm chứng kết quả toàn trình
    assert result.status == AgentRunStatus.COMPLETED
    assert "Đã thiết lập thành công" in result.output
    assert result.tool_calls_made == 2

    # Kiểm tra Encore API được gọi đúng tham số
    mock_encore.post.assert_any_call(
        "/operations/okr-cycles",
        json={"workspaceId": 1, "title": "Q3-2026", "startDate": "2026-07-01", "endDate": "2026-09-30"},
    )
    mock_encore.post.assert_any_call(
        "/operations/tasks",
        json={"workspaceId": 1, "title": "Xây dựng kế hoạch chi tiết Q3", "priority": "high"},
    )
