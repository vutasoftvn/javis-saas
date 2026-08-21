import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from workforce.models import WorkProduct
from workforce.work_product.transformer import WorkProductTransformer
from workforce.governance.quality_gate_policy import QualityGatePolicy
from workforce.automation.event_bus import InternalEventBus, AgentPlatformEvent
from founder_os.tasks.models import Task
from core.snowflake import generate_snowflake_id


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

        # Thẩm định chất lượng qua Cross-cutting QualityGatePolicy (F4 Spec)
        qg_eval = QualityGatePolicy.evaluate_work_product(
            title=structured.title,
            content=structured.content_markdown,
            domain=agent_key,
            metadata=structured.metadata,
        )

        metadata_with_qg = dict(structured.metadata or {})
        metadata_with_qg["quality_gate"] = qg_eval.model_dump() if hasattr(qg_eval, "model_dump") else qg_eval.dict()

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
            metadata_jsonb=metadata_with_qg,
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

        # G3 Phase 1E: the worker opens its own session and never raises -
        # awaited (not fire-and-forget) so failures are visible in tests and
        # in this request's own trace, but it can never roll back the
        # WorkProduct state change above (already committed via flush).
        # Imported lazily: review_worker.py transitively pulls in the whole
        # orchestration package (chief_of_staff.py) - see approval_service.py
        # for why a top-level import here breaks an unrelated circular import.
        from workforce.agents.learning.review_worker import LearningReviewWorker
        await asyncio.to_thread(
            LearningReviewWorker.on_work_product_rejected,
            workspace_id=wp.workspace_id,
            work_product_id=wp.id,
            agent_key=wp.agent_key,
            title=wp.title,
            feedback=feedback,
            run_id=wp.run_id,
            rejection_kind="revision_requested",
        )

        return wp

    async def reject_work_product(
        self,
        product_id: int,
        reviewed_by: int,
        feedback: str,
    ) -> WorkProduct:
        """Founder/Lead từ chối hẳn sản phẩm bàn giao (khác request_revision:
        không yêu cầu sửa lại, dừng hẳn). `status="REJECTED"` đã có sẵn trong
        vocabulary của WorkProduct từ trước nhưng chưa từng được set ở đâu."""
        wp = await self.get_work_product(product_id)
        if not wp:
            raise ValueError(f"WorkProduct with ID {product_id} not found")

        wp.status = "REJECTED"
        wp.reviewed_by = reviewed_by
        wp.reviewed_at = datetime.utcnow()
        wp.metadata_jsonb = {**(wp.metadata_jsonb or {}), "revision_feedback": feedback}

        await self.db.flush()

        await InternalEventBus.publish(
            AgentPlatformEvent(
                event_type="WORK_PRODUCT_REJECTED",
                workspace_id=wp.workspace_id,
                agent_key=wp.agent_key,
                payload={"work_product_id": wp.id, "task_id": wp.task_id, "feedback": feedback},
            )
        )

        from workforce.agents.learning.review_worker import LearningReviewWorker
        await asyncio.to_thread(
            LearningReviewWorker.on_work_product_rejected,
            workspace_id=wp.workspace_id,
            work_product_id=wp.id,
            agent_key=wp.agent_key,
            title=wp.title,
            feedback=feedback,
            run_id=wp.run_id,
            rejection_kind="rejected",
        )

        return wp
