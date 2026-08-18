import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.workforce.models import (
    AgentHeartbeat, AgentRoutine, RoutineExecution, AgentRun, AgentDefinition, AgentBudget
)
from app.workforce.automation.event_bus import InternalEventBus, AgentPlatformEvent
from app.workforce.automation.heartbeat_monitor import HeartbeatMonitorService
from app.workforce.automation.routine_service import RoutineService
from app.workforce.dispatcher.task_dispatcher import AgentTaskDispatcher
from app.workforce.adapters.base import ExecutionResult, TokenUsage
from app.founder_os.tasks.models import Task


class TestInternalEventBus:
    """Kiểm thử trục sự kiện nội bộ InternalEventBus."""

    @pytest.mark.asyncio
    async def test_publish_and_subscribe_flow(self):
        InternalEventBus.clear()
        received_events = []

        async def handler(event: AgentPlatformEvent):
            received_events.append(event)

        InternalEventBus.subscribe("TASK_COMPLETED", handler)

        event = AgentPlatformEvent(
            event_type="TASK_COMPLETED",
            workspace_id=1,
            agent_key="founder_copilot",
            payload={"task_id": 999, "tokens_used": 350},
        )
        await InternalEventBus.publish(event)

        assert len(received_events) == 1
        assert received_events[0].payload["task_id"] == 999
        assert received_events[0].agent_key == "founder_copilot"

    @pytest.mark.asyncio
    async def test_wildcard_subscription(self):
        InternalEventBus.clear()
        all_events = []

        def wildcard_handler(event: AgentPlatformEvent):
            all_events.append(event)

        InternalEventBus.subscribe("*", wildcard_handler)

        await InternalEventBus.publish(AgentPlatformEvent(event_type="EVENT_A", payload={"data": 1}))
        await InternalEventBus.publish(AgentPlatformEvent(event_type="EVENT_B", payload={"data": 2}))

        assert len(all_events) == 2


class TestHeartbeatAndStalledRecovery:
    """Kiểm thử ghi nhận liveness và tự động thu hồi tác vụ bị treo."""

    @pytest.mark.asyncio
    async def test_record_and_list_heartbeats(self):
        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalars().first.return_value = None
        mock_db.execute.return_value = mock_res

        service = HeartbeatMonitorService(mock_db)
        hb = await service.record_heartbeat(
            agent_key="cfo_agent",
            workspace_id=1,
            status="HEALTHY",
            active_runs_count=1,
        )

        assert hb.agent_key == "cfo_agent"
        assert hb.status == "HEALTHY"
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_detect_and_recover_stalled_runs(self):
        mock_db = AsyncMock()
        stalled_run = AgentRun(
            id=701,
            workspace_id=1,
            trace_id="stalled_trace_123",
            task_id=505,
            agent_key="devops_agent",
            status="running",
            started_at=datetime.utcnow() - timedelta(minutes=25),  # 25 minutes ago
        )

        mock_res = MagicMock()
        mock_res.scalars().all.return_value = [stalled_run]
        mock_res.scalars().first.return_value = None
        mock_db.execute.return_value = mock_res

        InternalEventBus.clear()
        stalled_events = []
        InternalEventBus.subscribe("HEARTBEAT_STALLED", lambda e: stalled_events.append(e))

        service = HeartbeatMonitorService(mock_db)
        recovered = await service.check_and_recover_stalled_runs(stalled_timeout_minutes=10, workspace_id=1)

        assert len(recovered) == 1
        assert stalled_run.status == "failed"
        assert stalled_run.error_jsonb["error_type"] == "STALLED_TIMEOUT"
        assert len(stalled_events) == 1
        assert stalled_events[0].payload["run_id"] == 701


class TestRoutineScheduler12WY:
    """Kiểm thử lập lịch và kích hoạt các quy trình 12-Week Year."""

    @pytest.mark.asyncio
    async def test_seed_and_trigger_monday_tactics_routine(self):
        mock_db = AsyncMock()
        service = RoutineService(mock_db)

        routine = AgentRoutine(
            id=10,
            key="monday_tactics_dispatch",
            name="Monday Morning 12WY Tactics Dispatch",
            routine_type="WEEKLY_TACTICS",
            cron_expression="0 8 * * 1",
            target_agent_key="founder_copilot",
            enabled=True,
            payload_template_jsonb={
                "title": "[12WY Routine] Phân rã Weekly Tactics",
                "priority": "high",
            },
        )

        def execute_side_effect(stmt):
            stmt_str = str(stmt)
            res_mock = MagicMock()
            if "agent_routines" in stmt_str:
                res_mock.scalars().first.return_value = routine
            elif "tasks" in stmt_str:
                res_mock.scalars().first.return_value = Task(id=801, title="Test Task", status="todo", source="founder_copilot")
            elif "agent_definitions" in stmt_str:
                res_mock.scalars().first.return_value = AgentDefinition(id=1, key="founder_copilot", name="Founder", risk_level=1, model_config_jsonb={})
            elif "agent_budgets" in stmt_str:
                res_mock.scalars().first.return_value = AgentBudget(agent_key="founder_copilot", limit_usd=50.0, spent_usd=0.0, is_blocked=False)
            else:
                res_mock.scalars().first.return_value = None
            return res_mock

        mock_db.execute.side_effect = execute_side_effect

        with patch("app.workforce.dispatcher.task_dispatcher.AgentRunnerService.execute_run", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = ExecutionResult(
                trace_id="routine_trace_01",
                content="Đã phân bổ 5 Weekly Tactics cho tuần 4.",
                usage=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150, cost_usd=0.001),
                latency_ms=80,
            )

            result = await service.trigger_routine("monday_tactics_dispatch", workspace_id=1)

            assert result["routine_key"] == "monday_tactics_dispatch"
            assert result["status"] == "SUCCESS"
            assert routine.last_run_at is not None


class TestEventDrivenExecutionFlow:
    """Kiểm thử luồng phát sự kiện tự động khi Dispatch Task."""

    @pytest.mark.asyncio
    async def test_task_dispatch_fires_events(self):
        InternalEventBus.clear()
        events_captured = []

        InternalEventBus.subscribe("TASK_DISPATCHED", lambda e: events_captured.append(e))
        InternalEventBus.subscribe("TASK_COMPLETED", lambda e: events_captured.append(e))

        mock_db = AsyncMock()
        mock_task = Task(id=901, workspace_id=1, title="Phân tích báo cáo tuần", status="todo", priority="medium")
        mock_agent = AgentDefinition(id=1, key="founder_copilot", name="Founder", risk_level=1, model_config_jsonb={})
        mock_budget = AgentBudget(agent_key="founder_copilot", limit_usd=50.0, spent_usd=0.0, is_blocked=False)

        def execute_side_effect(stmt):
            stmt_str = str(stmt)
            res_mock = MagicMock()
            if "tasks" in stmt_str:
                res_mock.scalars().first.return_value = mock_task
            elif "agent_definitions" in stmt_str:
                res_mock.scalars().first.return_value = mock_agent
            elif "agent_budgets" in stmt_str:
                res_mock.scalars().first.return_value = mock_budget
            else:
                res_mock.scalars().first.return_value = None
            return res_mock

        mock_db.execute.side_effect = execute_side_effect

        dispatcher = AgentTaskDispatcher(mock_db)
        with patch.object(dispatcher.runner, "execute_run", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = ExecutionResult(
                trace_id="ev_trace_01",
                content="Báo cáo hoàn tất.",
                usage=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150, cost_usd=0.001),
                latency_ms=90,
            )

            await dispatcher.dispatch_task(task_id=901, agent_key="founder_copilot")

            assert len(events_captured) == 2
            assert events_captured[0].event_type == "TASK_DISPATCHED"
            assert events_captured[1].event_type == "TASK_COMPLETED"
            assert events_captured[1].payload["cost_usd"] == 0.001
