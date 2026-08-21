# backend/app/workforce/agents/orchestration/mission_resume_service.py
"""Thay cho advisory-lock + materialized-event trong
chief_of_staff.py::resume_after_delegation (xem continuation.py hiện tại) —
đảm bảo đúng 1 worker resume AdkCofounderWorkflow cho mỗi checkpoint."""
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.workforce.agents.orchestration.mission_resume_models import MissionResumeJob


class MissionResumeJobService:
    @staticmethod
    def enqueue_resume(
        db: Session,
        *,
        workspace_id: int,
        mission_run_id: int,
        workflow_session_id: str | None,
        checkpoint_key: str,
        reason: str,
    ) -> MissionResumeJob:
        existing = (
            db.query(MissionResumeJob)
            .filter(
                MissionResumeJob.mission_run_id == mission_run_id,
                MissionResumeJob.checkpoint_key == checkpoint_key,
            )
            .first()
        )
        if existing is not None:
            return existing

        job = MissionResumeJob(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            mission_run_id=mission_run_id,
            workflow_session_id=workflow_session_id,
            checkpoint_key=checkpoint_key,
            idempotency_key=f"mission_resume:{mission_run_id}:{checkpoint_key}",
            reason=reason,
            status="queued",
        )
        db.add(job)
        try:
            db.commit()
        except IntegrityError:
            # Race: worker khác vừa insert cùng checkpoint giữa lúc query và
            # commit ở trên — coi row của họ là nguồn sự thật, không tạo trùng.
            db.rollback()
            existing = (
                db.query(MissionResumeJob)
                .filter(
                    MissionResumeJob.mission_run_id == mission_run_id,
                    MissionResumeJob.checkpoint_key == checkpoint_key,
                )
                .one()
            )
            return existing
        db.refresh(job)
        return job
