import time
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.workforce.adapters.base import ExecutionPayload, ExecutionResult
from app.workforce.adapters.factory import RuntimeAdapterFactory
from app.workforce.models import AgentDefinition, LegacyPlatformAgentRun, AgentStep
from app.core.snowflake import generate_snowflake_id


class AgentRunnerService:
    """Service điều phối vòng đời của một lần chạy (AgentRun Lifecycle)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute_run(
        self,
        payload: ExecutionPayload,
        agent: AgentDefinition,
        task_id: Optional[int] = None,
        session_id: Optional[int] = None,
        workspace_id: Optional[int] = None,
    ) -> ExecutionResult:
        start_time = datetime.utcnow()

        # 1. Tạo bản ghi AgentRun trạng thái 'running'
        run_record = LegacyPlatformAgentRun(
            id=generate_snowflake_id(),
            workspace_id=workspace_id or agent.workspace_id,
            trace_id=payload.trace_id,
            session_id=session_id,
            task_id=task_id,
            agent_id=agent.id,
            agent_key=agent.key,
            runtime_provider=agent.default_model_profile,
            model_name=payload.model_name,
            status="running",
            prompt_snapshot="\n---\n".join([f"[{m.role}]: {m.content}" for m in payload.messages]),
            started_at=start_time,
        )
        self.db.add(run_record)
        
        # Cập nhật status của agent thành 'busy'
        agent.status = "busy"
        await self.db.flush()

        # 2. Tạo Step span cho việc gọi Model
        step_record = AgentStep(
            id=generate_snowflake_id(),
            run_id=run_record.id,
            step_type="RUNTIME_CALL",
            name=f"Execute {payload.model_name}",
            status="pending",
            created_at=datetime.utcnow(),
        )
        self.db.add(step_record)
        await self.db.flush()

        try:
            # 3. Lấy Adapter & Thực thi
            adapter = RuntimeAdapterFactory.get_adapter(
                provider=agent.model_config_jsonb.get("provider"),
                model_profile=agent.default_model_profile,
                custom_config=agent.model_config_jsonb,
            )
            result: ExecutionResult = await adapter.execute(payload)

            # 4. Cập nhật thành công cho Step & Run
            step_record.status = "success"
            step_record.duration_ms = result.latency_ms
            step_record.metadata_jsonb = {
                "usage": {
                    "prompt_tokens": result.usage.prompt_tokens,
                    "completion_tokens": result.usage.completion_tokens,
                    "total_tokens": result.usage.total_tokens,
                    "cost_usd": result.usage.cost_usd,
                },
                "finish_reason": result.finish_reason,
            }

            run_record.status = "completed"
            run_record.duration_ms = result.latency_ms
            run_record.input_tokens = result.usage.prompt_tokens
            run_record.output_tokens = result.usage.completion_tokens
            run_record.estimated_cost = result.usage.cost_usd
            run_record.output_payload = result.content
            run_record.completed_at = datetime.utcnow()

            agent.status = "idle"
            await self.db.flush()
            return result

        except Exception as e:
            # Xử lý lỗi
            step_record.status = "failed"
            step_record.metadata_jsonb = {"error": str(e)}

            run_record.status = "failed"
            run_record.error_jsonb = {"error_message": str(e), "error_type": type(e).__name__}
            run_record.completed_at = datetime.utcnow()

            agent.status = "error"
            await self.db.flush()
            raise e
