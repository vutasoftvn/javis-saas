from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.workforce.dispatcher.context_builder import AgentContextBuilder
from app.workforce.dispatcher.runner import AgentRunnerService
from app.workforce.registry.agent_registry import AgentRegistryService
from app.workforce.governance.budget_service import BudgetingEngine, BudgetExceededError
from app.workforce.governance.risk_evaluator import RiskPolicyEvaluator
from app.workforce.governance.approval_service import ApprovalInboxService
from app.workforce.governance.cost_ledger_service import CostLedgerService
from app.workforce.automation.event_bus import InternalEventBus, AgentPlatformEvent
from app.workforce.work_product.work_product_service import WorkProductService
from app.workforce.models import AgentDefinition
from app.founder_os.tasks.models import Task


class AgentTaskDispatcher:
    """Bộ điều phối tác vụ tích hợp Governance, Event-driven & Work Product Contract.

    Ranh giới với `app.workforce.agents.delegation.task_execution_bridge.dispatch_agent_task()`
    (quyết định đã ghi trong docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md,
    hàng "Task-to-agent dispatch"): 2 đường dispatch này CỐ Ý tách biệt, không
    gộp. `AgentTaskDispatcher` phục vụ Direct Agent Execution/Routines (tự động
    hoá theo lịch, admin trigger) - resolve thẳng `AgentDefinition.key`, KHÔNG
    đọc `Task.execution_mode`/`assignee_member_id`. `dispatch_agent_task()`
    phục vụ Business Work Items đi qua `Task.execution_mode="AGENT"` ->
    `TaskBoardService`/`RunStep` (đường canonical, governed, hỗ trợ
    pause/resume). KHÔNG thêm 1 đường dispatch thứ 3.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.registry = AgentRegistryService(db)
        self.context_builder = AgentContextBuilder(db)
        self.runner = AgentRunnerService(db)
        self.budget_engine = BudgetingEngine(db)
        self.approval_service = ApprovalInboxService(db)
        self.cost_ledger = CostLedgerService(db)
        self.work_product_service = WorkProductService(db)

    async def dispatch_task(
        self,
        task_id: int,
        agent_key: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None,
        bypass_approval_check: bool = False,
    ) -> Dict[str, Any]:
        # 1. Tra cứu Task
        stmt = select(Task).where(Task.id == task_id)
        res = await self.db.execute(stmt)
        task = res.scalars().first()
        if not task:
            raise ValueError(f"Task with ID {task_id} not found")

        # 2. Xác định Agent được chỉ định
        target_agent_key = agent_key or task.source or "founder_copilot"
        agent = await self.registry.get_agent_by_key(target_agent_key, workspace_id=task.workspace_id)
        if not agent:
            agent = await self.registry.get_agent_by_key(target_agent_key, None)
            if not agent:
                agent = await self.registry.get_agent_by_key("founder_copilot", None)
                if not agent:
                    seeded = await self.registry.seed_factory_defaults(workspace_id=task.workspace_id)
                    agent = seeded[0] if seeded else None

        if not agent:
            raise ValueError(f"No suitable agent found to execute task {task_id}")

        # 3. Governance: Kiểm tra hạn mức ngân sách (Budget Check)
        await self.budget_engine.check_budget_quota(agent.key, workspace_id=task.workspace_id)

        # 4. Governance: Đánh giá ma trận rủi ro (Risk Evaluation)
        risk_eval = RiskPolicyEvaluator.evaluate(
            tool_key=agent.key,
            action_type="TASK_DISPATCH",
            risk_level_int=agent.risk_level,
        )

        if risk_eval.requires_approval and not bypass_approval_check:
            # Tạo phiếu yêu cầu phê duyệt trong Inbox & tạm dừng Task
            ticket = await self.approval_service.create_request(
                requester_agent_key=agent.key,
                requester_agent_id=agent.id,
                action_type="TASK_EXECUTION",
                risk_evaluation=risk_eval,
                payload={"task_id": task.id, "title": task.title, "priority": task.priority},
                task_id=task.id,
                workspace_id=task.workspace_id,
            )
            task.status = "waiting_approval"
            await self.db.flush()

            # Bắn sự kiện APPROVAL_REQUESTED qua Event Bus
            await InternalEventBus.publish(
                AgentPlatformEvent(
                    event_type="APPROVAL_REQUESTED",
                    workspace_id=task.workspace_id,
                    agent_key=agent.key,
                    payload={"ticket_id": ticket.id, "task_id": task.id, "risk_tier": risk_eval.tier.value},
                )
            )

            return {
                "task_id": task.id,
                "agent_key": agent.key,
                "status": "waiting_approval",
                "approval_ticket_id": ticket.id,
                "risk_tier": risk_eval.tier.value,
                "required_role": risk_eval.required_role,
                "reason": risk_eval.reason,
            }

        # 5. Chuẩn bị Execution Payload
        payload = await self.context_builder.build_task_payload(
            agent=agent,
            task=task,
            extra_context=extra_context,
        )

        # 6. Cập nhật task status sang 'in_progress'
        task.status = "in_progress"
        await self.db.flush()

        # Bắn sự kiện TASK_DISPATCHED
        await InternalEventBus.publish(
            AgentPlatformEvent(
                event_type="TASK_DISPATCHED",
                workspace_id=task.workspace_id,
                agent_key=agent.key,
                payload={"task_id": task.id, "trace_id": payload.trace_id},
            )
        )

        # 7. Thực thi qua AgentRunnerService
        exec_result = await self.runner.execute_run(
            payload=payload,
            agent=agent,
            task_id=task.id,
            workspace_id=task.workspace_id,
        )

        # 8. Governance: Ghi sổ cái Cost Ledger & Trừ quota ngân sách
        await self.cost_ledger.record_entry(
            agent_key=agent.key,
            provider=agent.default_model_profile,
            model_name=payload.model_name,
            prompt_tokens=exec_result.usage.prompt_tokens,
            completion_tokens=exec_result.usage.completion_tokens,
            cost_usd=exec_result.usage.cost_usd,
            task_id=task.id,
            agent_id=agent.id,
            workspace_id=task.workspace_id,
        )
        await self.budget_engine.record_spend(
            agent_key=agent.key,
            amount_usd=exec_result.usage.cost_usd,
            workspace_id=task.workspace_id,
        )

        # 9. Phase E: Tạo Work Product có cấu trúc (Work Product Contract)
        work_product = await self.work_product_service.create_from_execution(
            task=task,
            agent_key=agent.key,
            raw_content=exec_result.content,
            workspace_id=task.workspace_id,
        )

        # 10. Cập nhật Task hoàn thành
        task.status = "done"
        await self.db.flush()

        # Bắn sự kiện TASK_COMPLETED
        await InternalEventBus.publish(
            AgentPlatformEvent(
                event_type="TASK_COMPLETED",
                workspace_id=task.workspace_id,
                agent_key=agent.key,
                payload={
                    "task_id": task.id,
                    "work_product_id": work_product.id,
                    "trace_id": payload.trace_id,
                    "cost_usd": exec_result.usage.cost_usd,
                    "tokens_used": exec_result.usage.total_tokens,
                },
            )
        )

        return {
            "task_id": task.id,
            "agent_key": agent.key,
            "work_product_id": work_product.id,
            "status": "completed",
            "result_summary": work_product.summary or (exec_result.content[:300] + "..."),
            "full_content": exec_result.content,
            "tokens_used": exec_result.usage.total_tokens,
            "cost_usd": exec_result.usage.cost_usd,
            "latency_ms": exec_result.latency_ms,
        }
