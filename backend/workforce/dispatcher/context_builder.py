import uuid
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from workforce.adapters.base import ExecutionPayload, Message, ModelRole
from workforce.models import AgentDefinition
from workforce.registry.prompt_registry import PromptRegistryService
from workforce.registry.defaults import DEFAULT_PROMPT_TEMPLATES
from workforce.skills.skill_loader import DynamicSkillLoader
from founder_os.tasks.models import Task


class AgentContextBuilder:
    """Xây dựng ExecutionPayload hoàn chỉnh từ 4 lớp: Prompt, Skill, Policy và Task Spec."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.prompt_registry = PromptRegistryService(db)
        self.skill_loader = DynamicSkillLoader(db)

    async def build_task_payload(
        self,
        agent: AgentDefinition,
        task: Task,
        extra_context: Optional[Dict[str, Any]] = None,
        model_name: Optional[str] = None,
    ) -> ExecutionPayload:
        trace_id = f"trace_{uuid.uuid4().hex[:16]}"
        workspace_id = agent.workspace_id

        # 1. PROMPT LAYER: Tra cứu System Prompt (Versioned)
        system_prompt = await self.prompt_registry.get_prompt_content(
            key=agent.system_prompt_key,
            workspace_id=workspace_id,
        )
        if not system_prompt:
            system_prompt = DEFAULT_PROMPT_TEMPLATES.get(
                agent.system_prompt_key,
                f"You are {agent.name}, a specialized AI agent in COSA OS."
            )

        # 2. SPEC LAYER: Xây dựng Task Prompt từ Task Specification
        task_info_lines = [
            f"# YÊU CẦU NHIỆM VỤ (TASK SPECIFICATION)",
            f"- **Tiêu đề**: {task.title}",
            f"- **Trạng thái**: {task.status}",
            f"- **Mức độ ưu tiên**: {task.priority}",
        ]
        if task.due_at:
            task_info_lines.append(f"- **Hạn chót**: {task.due_at.isoformat()}")

        if extra_context:
            task_info_lines.append("\n# DỮ LIỆU BỔ SUNG:")
            for k, v in extra_context.items():
                task_info_lines.append(f"- **{k}**: {v}")

        task_prompt = "\n".join(task_info_lines)
        task_prompt += "\n\nHãy phân tích yêu cầu trên, thực thi theo đúng thẩm quyền chuyên môn và tạo ra sản phẩm hoàn chỉnh (Work Product Draft) kèm các khuyến nghị cần thiết."

        messages = [
            Message(role=ModelRole.SYSTEM, content=system_prompt),
            Message(role=ModelRole.USER, content=task_prompt),
        ]

        # 3. SKILL LAYER: Nạp danh sách tools động theo phân quyền của Agent
        tools_schema = await self.skill_loader.load_tools_for_agent(agent, workspace_id=workspace_id)

        resolved_model = model_name or agent.model_config_jsonb.get("model") or "claude-3-5-sonnet-20241022"

        return ExecutionPayload(
            trace_id=trace_id,
            agent_key=agent.key,
            model_name=resolved_model,
            messages=messages,
            temperature=agent.model_config_jsonb.get("temperature", 0.2),
            max_tokens=agent.model_config_jsonb.get("max_tokens", 4096),
            tools_schema=tools_schema if tools_schema else None,
            extra_params={"task_id": task.id, "agent_id": agent.id},
        )
