from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.workforce.models import AgentRoutine, RoutineExecution
from app.workforce.automation.event_bus import InternalEventBus, AgentPlatformEvent
from app.founder_os.tasks.models import Task
from app.core.snowflake import generate_snowflake_id


DEFAULT_ROUTINES_CONFIG = [
    {
        "key": "monday_tactics_dispatch",
        "name": "Monday Morning 12WY Tactics Dispatch",
        "routine_type": "WEEKLY_TACTICS",
        "cron_expression": "0 8 * * 1",
        "target_agent_key": "founder_copilot",
        "payload_template": {
            "title": "[12WY Routine] Phân rã Weekly Tactics & Kế hoạch tuần mới",
            "priority": "high",
            "instructions": "Tổng hợp các mục tiêu chiến lược 12WY, rà soát OKR/KPI và tự động tạo/giao Weekly Tactics cho từng Agent phụ trách phòng ban.",
        },
    },
    {
        "key": "friday_scoreboard_wrapup",
        "name": "Friday Afternoon 12WY Scoreboard Wrap-up",
        "routine_type": "FRIDAY_SCOREBOARD",
        "cron_expression": "0 17 * * 5",
        "target_agent_key": "founder_copilot",
        "payload_template": {
            "title": "[12WY Routine] Tổng kết Weekly Scoreboard & Báo cáo tiến độ tuần",
            "priority": "high",
            "instructions": "Thu thập kết quả hoàn thành task của tất cả các Agent, tính toán điểm thực thi Execution Score và lập bản tóm tắt điều hành gửi Founder.",
        },
    },
    {
        "key": "daily_standup_brief",
        "name": "Daily Standup Brief & Blocker Check",
        "routine_type": "DAILY_STANDUP",
        "cron_expression": "0 9 * * 1-5",
        "target_agent_key": "founder_copilot",
        "payload_template": {
            "title": "[Daily Routine] Báo cáo Standup đầu ngày & Kiểm tra điểm nghẽn",
            "priority": "medium",
            "instructions": "Điểm danh tiến độ công việc đang chạy, phát hiện các task chờ duyệt hoặc vượt ngân sách để cảnh báo sớm.",
        },
    },
    {
        "key": "week_13_review",
        "name": "Week 13 Cycle Review & Planning",
        "routine_type": "WEEK_13_REVIEW",
        "cron_expression": "0 9 1 4,7,10,1 *",
        "target_agent_key": "founder_copilot",
        "payload_template": {
            "title": "[12WY Routine] Đánh giá tổng kết chu kỳ 12-Week Year",
            "priority": "urgent",
            "instructions": "Tổng kết toàn diện 12 tuần đã qua, đo lường tỷ lệ hoàn thành mục tiêu và đề xuất định hướng chiến lược cho chu kỳ 12 tuần kế tiếp.",
        },
    },
]


class RoutineService:
    """Quản lý các quy trình tuần hoàn (12-Week Year Routines) và tự động kích hoạt."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_routine(self, key: str, workspace_id: Optional[int] = None) -> Optional[AgentRoutine]:
        stmt = select(AgentRoutine).where(AgentRoutine.key == key)
        if workspace_id is not None:
            stmt = stmt.where(AgentRoutine.workspace_id == workspace_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def list_routines(self, workspace_id: Optional[int] = None) -> List[AgentRoutine]:
        stmt = select(AgentRoutine)
        if workspace_id is not None:
            stmt = stmt.where(AgentRoutine.workspace_id == workspace_id)
        res = await self.db.execute(stmt)
        routines = list(res.scalars().all())
        if not routines:
            routines = await self.seed_default_routines(workspace_id)
        return routines

    async def seed_default_routines(self, workspace_id: Optional[int] = None) -> List[AgentRoutine]:
        seeded = []
        for r_data in DEFAULT_ROUTINES_CONFIG:
            existing = await self.get_routine(r_data["key"], workspace_id)
            if not existing:
                routine = AgentRoutine(
                    id=generate_snowflake_id(),
                    workspace_id=workspace_id,
                    key=r_data["key"],
                    name=r_data["name"],
                    routine_type=r_data["routine_type"],
                    cron_expression=r_data["cron_expression"],
                    target_agent_key=r_data["target_agent_key"],
                    enabled=True,
                    payload_template_jsonb=r_data["payload_template"],
                )
                self.db.add(routine)
                seeded.append(routine)
            else:
                seeded.append(existing)
        await self.db.flush()
        return seeded

    async def trigger_routine(
        self,
        key: str,
        workspace_id: Optional[int] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Kích hoạt thực thi ngay một Routine."""
        from app.workforce.dispatcher.task_dispatcher import AgentTaskDispatcher

        routine = await self.get_routine(key, workspace_id)
        if not routine:
            # Kiểm tra nếu chưa seed
            await self.seed_default_routines(workspace_id)
            routine = await self.get_routine(key, workspace_id)
            if not routine:
                raise ValueError(f"Routine '{key}' not found")

        # 1. Tạo Task đại diện cho Routine
        tmpl = routine.payload_template_jsonb or {}
        new_task = Task(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            title=tmpl.get("title", f"[Routine] {routine.name}"),
            status="todo",
            priority=tmpl.get("priority", "medium"),
            source=routine.target_agent_key,
        )
        self.db.add(new_task)
        await self.db.flush()

        # 2. Điều phối Task qua TaskDispatcher
        dispatcher = AgentTaskDispatcher(self.db)
        dispatch_result = await dispatcher.dispatch_task(
            task_id=new_task.id,
            agent_key=routine.target_agent_key,
            extra_context={
                "routine_key": routine.key,
                "routine_type": routine.routine_type,
                "instructions": tmpl.get("instructions", ""),
                **(extra_context or {}),
            },
        )

        # 3. Ghi nhận lịch sử RoutineExecution
        routine_exec = RoutineExecution(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            routine_id=routine.id,
            task_id=new_task.id,
            status="SUCCESS" if dispatch_result.get("status") == "completed" else "RUNNING",
            duration_ms=dispatch_result.get("latency_ms", 0),
            output_summary_jsonb={
                "result_summary": dispatch_result.get("result_summary"),
                "tokens_used": dispatch_result.get("tokens_used"),
            },
            executed_at=datetime.utcnow(),
        )
        self.db.add(routine_exec)

        # 4. Cập nhật last_run_at cho Routine
        routine.last_run_at = datetime.utcnow()
        await self.db.flush()

        # 5. Bắn sự kiện qua Event Bus
        await InternalEventBus.publish(
            AgentPlatformEvent(
                event_type="ROUTINE_TRIGGERED",
                workspace_id=workspace_id,
                agent_key=routine.target_agent_key,
                payload={"routine_key": routine.key, "task_id": new_task.id, "execution_id": routine_exec.id},
            )
        )

        return {
            "routine_key": routine.key,
            "routine_name": routine.name,
            "task_id": new_task.id,
            "execution_id": routine_exec.id,
            "status": routine_exec.status,
            "dispatch_result": dispatch_result,
        }
