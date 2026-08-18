from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.workforce.models import WorkProduct, AgentRun
from app.workforce.work_product.transformer import WorkProductTransformer
from app.workforce.automation.event_bus import InternalEventBus, AgentPlatformEvent
from app.founder_os.tasks.models import Task
from app.core.snowflake import generate_snowflake_id


class WorkProductService:
    """Quản lý vòng đời và nghiệm thu sản phẩm bàn giao (Work Product Contract)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_from_execution(
        self,
        task: Task,
        agent_key: str,
        raw_content: str,
        run_id: Optional[int] = None,
        workspace_id: Optional[int] = None,
    ) -> WorkProduct:
        structured = WorkProductTransformer.transform(
            raw_content=raw_content,
            task_title=task.title,
            agent_key=agent_key,
        )

        wp = WorkProduct(
            id=generate_snowflake_id(),
            workspace_id=workspace_id or task.workspace_id,
            task_id=task.id,
            run_id=run_id,
            agent_key=agent_key,
            title=structured.title,
            product_type=structured.product_type,
            status="DRAFT",
            summary=structured.summary,
            content_markdown=structured.content_markdown,
            artifacts_jsonb={"items": structured.artifacts},
            metadata_jsonb=structured.metadata,
            created_at=datetime.utcnow(),
        )
        self.db.add(wp)
        await self.db.flush()

        # Bắn sự kiện WORK_PRODUCT_CREATED
        await InternalEventBus.publish(
            AgentPlatformEvent(
                event_type="WORK_PRODUCT_CREATED",
                workspace_id=wp.workspace_id,
                agent_key=agent_key,
                payload={"work_product_id": wp.id, "task_id": task.id, "title": wp.title},
            )
        )

        return wp

    async def get_work_product(self, product_id: int) -> Optional[WorkProduct]:
        stmt = select(WorkProduct).where(WorkProduct.id == product_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def list_work_products(
        self,
        workspace_id: Optional[int] = None,
        task_id: Optional[int] = None,
        agent_key: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[WorkProduct]:
        stmt = select(WorkProduct).order_by(desc(WorkProduct.created_at))
        filters = []
        if workspace_id is not None:
            filters.append(WorkProduct.workspace_id == workspace_id)
        if task_id is not None:
            filters.append(WorkProduct.task_id == task_id)
        if agent_key:
            filters.append(WorkProduct.agent_key == agent_key)
        if status:
            filters.append(WorkProduct.status == status)
        if filters:
            stmt = stmt.where(and_(*filters))
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def accept_work_product(
        self,
        product_id: int,
        reviewed_by: int,
        feedback: Optional[str] = None,
    ) -> WorkProduct:
        """Founder/Lead nghiệm thu và chấp thuận sản phẩm bàn giao."""
        wp = await self.get_work_product(product_id)
        if not wp:
            raise ValueError(f"WorkProduct with ID {product_id} not found")

        wp.status = "ACCEPTED"
        wp.reviewed_by = reviewed_by
        wp.reviewed_at = datetime.utcnow()
        if feedback:
            wp.metadata_jsonb = {**(wp.metadata_jsonb or {}), "approval_feedback": feedback}

        # Nếu có gắn task, cập nhật task sang done
        if wp.task_id:
            t_stmt = select(Task).where(Task.id == wp.task_id)
            t_res = await self.db.execute(t_stmt)
            task = t_res.scalars().first()
            if task:
                task.status = "done"

        await self.db.flush()

        await InternalEventBus.publish(
            AgentPlatformEvent(
                event_type="WORK_PRODUCT_ACCEPTED",
                workspace_id=wp.workspace_id,
                agent_key=wp.agent_key,
                payload={"work_product_id": wp.id, "task_id": wp.task_id},
            )
        )

        return wp

    async def request_revision(
        self,
        product_id: int,
        reviewed_by: int,
        feedback: str,
    ) -> WorkProduct:
        """Founder/Lead yêu cầu hiệu đính / sửa lại sản phẩm."""
        wp = await self.get_work_product(product_id)
        if not wp:
            raise ValueError(f"WorkProduct with ID {product_id} not found")

        wp.status = "REVISION_REQUESTED"
        wp.reviewed_by = reviewed_by
        wp.reviewed_at = datetime.utcnow()
        wp.metadata_jsonb = {**(wp.metadata_jsonb or {}), "revision_feedback": feedback}

        # Chuyển trạng thái task về in_progress hoặc todo
        if wp.task_id:
            t_stmt = select(Task).where(Task.id == wp.task_id)
            t_res = await self.db.execute(t_stmt)
            task = t_res.scalars().first()
            if task:
                task.status = "in_progress"

        await self.db.flush()

        await InternalEventBus.publish(
            AgentPlatformEvent(
                event_type="WORK_PRODUCT_REVISION_REQUESTED",
                workspace_id=wp.workspace_id,
                agent_key=wp.agent_key,
                payload={"work_product_id": wp.id, "task_id": wp.task_id, "feedback": feedback},
            )
        )

        return wp
