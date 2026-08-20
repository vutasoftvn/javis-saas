"""
COSA Workflow Execution Engine
Điều phối thực thi các quy trình đa bước: Tuần tự, Song song (Parallel Tools) và Chờ phê duyệt (Structure.md Mục 13).
"""
import asyncio
from typing import Any, Dict, List, Optional
from agent.events.base import AgentEvent, EventStoreInterface, EventType
from skills.repository import SkillRepository, skill_repository
from tools.dispatcher import ToolDispatcher
from workflows.base import WorkflowDefinition, WorkflowStep, WorkflowStepType


class WorkflowEngine:
    """Động cơ thực thi Workflow đa bước tất định"""

    def __init__(
        self,
        tool_dispatcher: Optional[ToolDispatcher] = None,
        skills_repo: Optional[SkillRepository] = None,
        event_store: Optional[EventStoreInterface] = None
    ):
        self.tool_dispatcher = tool_dispatcher or ToolDispatcher()
        self.skills_repo = skills_repo or skill_repository
        self.event_store = event_store

    async def execute_workflow(
        self,
        workflow: WorkflowDefinition,
        initial_context: Dict[str, Any],
        session_id: Optional[str] = None,
        actor_id: str = "agent",
        approved_step_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Thực thi toàn bộ chuỗi các bước trong Workflow"""
        context = dict(initial_context)

        # 1. Phát sinh event workflow.started
        if self.event_store and session_id:
            await self.event_store.append(
                AgentEvent(
                    session_id=session_id,
                    type=EventType.WORKFLOW_STARTED,
                    actor={"type": "agent", "id": actor_id},
                    payload={"workflow_id": workflow.id, "workflow_name": workflow.name}
                )
            )

        executed_steps: List[str] = []
        is_skipping = approved_step_id is not None

        for step in workflow.steps:
            # Nếu đang resume từ một bước đã duyệt, bỏ qua các bước trước đó
            if is_skipping:
                if step.id == approved_step_id:
                    is_skipping = False  # Bắt đầu chạy lại từ bước sau approval
                    continue
                else:
                    executed_steps.append(step.id)
                    continue

            step_result = await self._execute_single_step(step, context, session_id, actor_id)

            # Xử lý trường hợp dừng chờ phê duyệt từ Founder
            if step_result.get("status") == "paused_waiting_approval":
                return {
                    "status": "paused_waiting_approval",
                    "workflow_id": workflow.id,
                    "waiting_step_id": step.id,
                    "executed_steps": executed_steps,
                    "context": context
                }

            executed_steps.append(step.id)

            # Phát sinh event workflow.step_completed
            if self.event_store and session_id:
                await self.event_store.append(
                    AgentEvent(
                        session_id=session_id,
                        type=EventType.WORKFLOW_STEP_COMPLETED,
                        actor={"type": "agent", "id": actor_id},
                        payload={"workflow_id": workflow.id, "step_id": step.id, "step_name": step.name}
                    )
                )

        return {
            "status": "completed",
            "workflow_id": workflow.id,
            "executed_steps": executed_steps,
            "context": context
        }

    async def _execute_single_step(
        self,
        step: WorkflowStep,
        context: Dict[str, Any],
        session_id: Optional[str],
        actor_id: str
    ) -> Dict[str, Any]:
        """Thực thi một bước đơn lẻ theo loại StepType"""
        # 1. BƯỚC SKILL: Nạp kiến thức nghiệp vụ vào context
        if step.type == WorkflowStepType.SKILL:
            skill = self.skills_repo.get(step.target)
            if skill:
                instructions = await skill.load_instructions()
                context[f"skill_{step.target}"] = instructions
                if self.event_store and session_id:
                    await self.event_store.append(
                        AgentEvent(
                            session_id=session_id,
                            type=EventType.SKILL_LOADED,
                            actor={"type": "agent", "id": actor_id},
                            payload={"skill_id": step.target, "title": skill.definition.name}
                        )
                    )
            return {"status": "success"}

        # 2. BƯỚC TOOL ĐƠN LẺ
        elif step.type == WorkflowStepType.TOOL:
            res = await self.tool_dispatcher.dispatch(
                tool_id=step.target,
                input_data=step.params,
                context=context,
                session_id=session_id,
                actor_id=actor_id
            )
            context[f"tool_{step.target}"] = res.data
            return {"status": res.status, "data": res.data}

        # 3. BƯỚC TOOL CHẠY SONG SONG (PARALLEL TOOLS)
        elif step.type == WorkflowStepType.PARALLEL_TOOLS:
            tool_ids = [t.strip() for t in step.target.split(",") if t.strip()]
            tasks = [
                self.tool_dispatcher.dispatch(
                    tool_id=tid,
                    input_data=step.params,
                    context=context,
                    session_id=session_id,
                    actor_id=actor_id
                )
                for tid in tool_ids
            ]
            results = await asyncio.gather(*tasks)
            for tid, r in zip(tool_ids, results):
                context[f"tool_{tid}"] = r.data
            return {"status": "success", "results_count": len(results)}

        # 4. BƯỚC DỪNG CHỜ PHÊ DUYỆT (HUMAN APPROVAL GATE)
        elif step.type == WorkflowStepType.HUMAN_APPROVAL:
            if self.event_store and session_id:
                await self.event_store.append(
                    AgentEvent(
                        session_id=session_id,
                        type=EventType.APPROVAL_REQUESTED,
                        actor={"type": "agent", "id": actor_id},
                        payload={
                            "step_id": step.id,
                            "action_summary": step.params.get("action_summary", "Chờ Founder phê duyệt bước tiếp theo"),
                            "action_payload": step.params
                        },
                        metadata={"risk_level": "HIGH"}
                    )
                )
            return {"status": "paused_waiting_approval"}

        return {"status": "success"}
