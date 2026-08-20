from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.workforce.models import AgentHeartbeat, LegacyPlatformAgentRun, AgentDefinition
from app.workforce.automation.event_bus import InternalEventBus, AgentPlatformEvent
from app.core.snowflake import generate_snowflake_id


class HeartbeatMonitorService:
    """Giám sát liveness của Agent Workforce & Tự động phục hồi tác vụ bị treo (Stalled Runs)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_heartbeat(
        self,
        agent_key: str,
        agent_id: Optional[int] = None,
        workspace_id: Optional[int] = None,
        status: str = "HEALTHY",
        active_runs_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentHeartbeat:
        stmt = select(AgentHeartbeat).where(AgentHeartbeat.agent_key == agent_key)
        if workspace_id is not None:
            stmt = stmt.where(AgentHeartbeat.workspace_id == workspace_id)
        res = await self.db.execute(stmt)
        heartbeat = res.scalars().first()

        if heartbeat:
            heartbeat.status = status
            heartbeat.active_runs_count = active_runs_count
            heartbeat.last_heartbeat_at = datetime.utcnow()
            if metadata:
                heartbeat.metadata_jsonb = metadata
        else:
            heartbeat = AgentHeartbeat(
                id=generate_snowflake_id(),
                workspace_id=workspace_id,
                agent_id=agent_id,
                agent_key=agent_key,
                status=status,
                active_runs_count=active_runs_count,
                last_heartbeat_at=datetime.utcnow(),
                metadata_jsonb=metadata or {},
            )
            self.db.add(heartbeat)

        await self.db.flush()
        return heartbeat

    async def list_heartbeats(self, workspace_id: Optional[int] = None) -> List[AgentHeartbeat]:
        stmt = select(AgentHeartbeat)
        if workspace_id is not None:
            stmt = stmt.where(AgentHeartbeat.workspace_id == workspace_id)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def check_and_recover_stalled_runs(
        self,
        stalled_timeout_minutes: int = 10,
        workspace_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Quét và thu hồi các AgentRun bị kẹt ở trạng thái 'running' quá thời gian timeout."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=stalled_timeout_minutes)

        stmt = select(LegacyPlatformAgentRun).where(
            and_(
                LegacyPlatformAgentRun.status == "running",
                LegacyPlatformAgentRun.started_at < cutoff_time,
            )
        )
        if workspace_id is not None:
            stmt = stmt.where(LegacyPlatformAgentRun.workspace_id == workspace_id)

        res = await self.db.execute(stmt)
        stalled_runs = list(res.scalars().all())
        recovered_details = []

        for run in stalled_runs:
            run.status = "failed"
            run.completed_at = datetime.utcnow()
            run.error_jsonb = {
                "error_type": "STALLED_TIMEOUT",
                "message": f"Execution timed out after {stalled_timeout_minutes} minutes without completion.",
            }

            # Cập nhật nhịp tim Agent sang STALLED/DEGRADED
            await self.record_heartbeat(
                agent_key=run.agent_key,
                agent_id=run.agent_id,
                workspace_id=run.workspace_id,
                status="DEGRADED",
                active_runs_count=0,
                metadata={"last_error": "Stalled run detected and recovered"},
            )

            # Phát sự kiện thông báo qua Event Bus
            await InternalEventBus.publish(
                AgentPlatformEvent(
                    event_type="HEARTBEAT_STALLED",
                    workspace_id=run.workspace_id,
                    agent_key=run.agent_key,
                    payload={"run_id": run.id, "trace_id": run.trace_id, "task_id": run.task_id},
                )
            )

            recovered_details.append({
                "run_id": run.id,
                "agent_key": run.agent_key,
                "trace_id": run.trace_id,
                "started_at": run.started_at.isoformat(),
            })

        await self.db.flush()
        return recovered_details
