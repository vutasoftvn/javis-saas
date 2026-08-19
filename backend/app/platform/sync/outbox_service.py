"""Transactional Outbox Service for COSA Hybrid Data Architecture (Phase 2).

Manages atomic writes of business state and synchronization events to platform_outbox.
Specification: COSA_Hybrid_Local_PostgreSQL_Supabase_Project_Intelligence_Integration_v2.md (Section 8, 9, 16)
"""
from datetime import datetime
import logging
from typing import Any, Dict, Optional
import uuid

from sqlalchemy.orm import Session

from app.founder_os.strategy.models import Project
from app.platform.auth.models import Workspace
from app.platform.sync.models import PlatformOutbox
from app.platform.sync.schemas import (
    DataClassificationEnum,
    PlatformEventTypeEnum,
    PlatformEventEnvelope,
    ProjectRegistrationPayload,
    ProjectStageChangePayload,
    ProjectOutcomePayload,
    StartupStageEnum,
)

logger = logging.getLogger(__name__)


class PlatformOutboxService:
    """Service to atomically record and dispatch platform sync events."""

    @staticmethod
    def create_outbox_event(
        db: Session,
        event_type: PlatformEventTypeEnum,
        aggregate_type: str,
        aggregate_id: str,
        company_id: str,
        payload: Dict[str, Any],
        project_id: Optional[str] = None,
        classification: DataClassificationEnum = DataClassificationEnum.PLATFORM_REQUIRED,
    ) -> PlatformOutbox:
        """Atomic write of an event envelope to platform_outbox in the current transaction."""
        event_id = str(uuid.uuid4())
        
        # Validate envelope via Pydantic schema
        envelope = PlatformEventEnvelope(
            event_id=uuid.UUID(event_id),
            company_id=uuid.UUID(company_id),
            project_id=uuid.UUID(project_id) if project_id else None,
            event_type=event_type,
            classification=classification,
            payload=payload,
            occurred_at=datetime.utcnow(),
        )

        outbox_entry = PlatformOutbox(
            event_id=event_id,
            event_type=event_type.value,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            company_id=company_id,
            classification=classification.value,
            payload=envelope.payload,
            status="pending",
            retry_count=0,
            next_retry_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.add(outbox_entry)
        db.flush()
        logger.info(f"Recorded outbox event {event_id} ({event_type.value}) for aggregate {aggregate_id}")
        return outbox_entry

    @classmethod
    def emit_project_registered(
        cls,
        db: Session,
        project: Project,
        workspace: Workspace,
    ) -> PlatformOutbox:
        """Emits project.created event when a new project is created."""
        if not project.platform_project_id:
            project.platform_project_id = str(uuid.uuid4())
            db.flush()

        if not workspace.platform_company_id:
            workspace.platform_company_id = str(uuid.uuid4())
            db.flush()

        payload = ProjectRegistrationPayload(
            platform_project_id=uuid.UUID(project.platform_project_id),
            company_id=uuid.UUID(workspace.platform_company_id),
            local_project_snowflake=project.id,
            name=project.title,
            slug=None,
            industry=None,
            category=project.project_type,
            status="active",
            current_stage=StartupStageEnum(project.project_stage) if project.project_stage in StartupStageEnum.__members__ else StartupStageEnum.S0_EXPLORE,
        )

        return cls.create_outbox_event(
            db=db,
            event_type=PlatformEventTypeEnum.PROJECT_CREATED,
            aggregate_type="project",
            aggregate_id=project.platform_project_id,
            company_id=workspace.platform_company_id,
            project_id=project.platform_project_id,
            payload=payload.model_dump(mode="json"),
            classification=DataClassificationEnum.PLATFORM_REQUIRED,
        )

    @classmethod
    def emit_project_stage_changed(
        cls,
        db: Session,
        project: Project,
        workspace: Workspace,
        from_stage: Optional[str],
        to_stage: str,
        duration_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PlatformOutbox:
        """Emits project.stage_changed event when project transitions between stages."""
        if not project.platform_project_id:
            project.platform_project_id = str(uuid.uuid4())
            db.flush()

        if not workspace.platform_company_id:
            workspace.platform_company_id = str(uuid.uuid4())
            db.flush()

        payload = ProjectStageChangePayload(
            platform_project_id=uuid.UUID(project.platform_project_id),
            company_id=uuid.UUID(workspace.platform_company_id),
            from_stage=StartupStageEnum(from_stage) if from_stage and from_stage in StartupStageEnum.__members__ else None,
            to_stage=StartupStageEnum(to_stage) if to_stage in StartupStageEnum.__members__ else StartupStageEnum.S0_EXPLORE,
            duration_seconds=duration_seconds,
            change_source="local_sync",
            metadata=metadata or {},
        )

        return cls.create_outbox_event(
            db=db,
            event_type=PlatformEventTypeEnum.PROJECT_STAGE_CHANGED,
            aggregate_type="project",
            aggregate_id=project.platform_project_id,
            company_id=workspace.platform_company_id,
            project_id=project.platform_project_id,
            payload=payload.model_dump(mode="json"),
            classification=DataClassificationEnum.PLATFORM_REQUIRED,
        )

    @classmethod
    def emit_project_outcome_updated(
        cls,
        db: Session,
        project: Project,
        workspace: Workspace,
        outcome_data: Dict[str, Any],
    ) -> PlatformOutbox:
        """Emits project.milestone_reached or outcome event with de-identified metrics."""
        if not project.platform_project_id:
            project.platform_project_id = str(uuid.uuid4())
            db.flush()

        if not workspace.platform_company_id:
            workspace.platform_company_id = str(uuid.uuid4())
            db.flush()

        payload = ProjectOutcomePayload(
            platform_project_id=uuid.UUID(project.platform_project_id),
            company_id=uuid.UUID(workspace.platform_company_id),
            first_interview_at=outcome_data.get("first_interview_at"),
            first_experiment_at=outcome_data.get("first_experiment_at"),
            mvp_launched_at=outcome_data.get("mvp_launched_at"),
            first_customer_at=outcome_data.get("first_customer_at"),
            first_revenue_at=outcome_data.get("first_revenue_at"),
            has_revenue=outcome_data.get("has_revenue", False),
            revenue_band=outcome_data.get("revenue_band", "0"),
            team_size_band=outcome_data.get("team_size_band", "1-2"),
        )

        return cls.create_outbox_event(
            db=db,
            event_type=PlatformEventTypeEnum.PROJECT_MILESTONE_REACHED,
            aggregate_type="project",
            aggregate_id=project.platform_project_id,
            company_id=workspace.platform_company_id,
            project_id=project.platform_project_id,
            payload=payload.model_dump(mode="json"),
            classification=DataClassificationEnum.ANALYTICS_REQUIRED,
        )

    @classmethod
    def emit_project_deleted(
        cls,
        db: Session,
        project: Project,
        workspace: Workspace,
        last_known_stage: Optional[str] = None,
    ) -> PlatformOutbox:
        """Emits project.deleted event so Central retains aggregate lifecycle facts."""
        if not project.platform_project_id:
            project.platform_project_id = str(uuid.uuid4())
            db.flush()

        if not workspace.platform_company_id:
            workspace.platform_company_id = str(uuid.uuid4())
            db.flush()

        payload = {
            "platform_project_id": project.platform_project_id,
            "company_id": workspace.platform_company_id,
            "last_known_stage": last_known_stage or project.project_stage,
            "deleted_at": datetime.utcnow().isoformat(),
        }

        return cls.create_outbox_event(
            db=db,
            event_type=PlatformEventTypeEnum.PROJECT_DELETED,
            aggregate_type="project",
            aggregate_id=project.platform_project_id,
            company_id=workspace.platform_company_id,
            project_id=project.platform_project_id,
            payload=payload,
            classification=DataClassificationEnum.PLATFORM_REQUIRED,
        )
