import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.platform.auth.models import Workspace
from app.founder_os.strategy.models import (
    Project,
    StrategyCanvas,
    StrategyRevision,
    StrategyFoundation,
    CoreValue
)
from app.founder_os.strategy.schemas.stage_schemas import (
    ProjectStageEnum,
    StageContextResponse,
    StagePolicySpec
)
from app.founder_os.strategy.services.management_policy_engine import ManagementPolicyEngine

logger = logging.getLogger(__name__)


class StageResolverService:
    """COSA Stage Context Resolver Service.
    
    Phân giải ngữ cảnh vận hành thực tế kết hợp giữa:
    - Company Level: Vision, Mission, Core Values, Company Stage.
    - Project Level: Project ID, Title, Project Stage, Stage Goal, Constraints, Exit Criteria.
    """

    def __init__(self, db: Session, workspace_id: int, user_id: Optional[int] = None):
        self.db = db
        self.workspace_id = workspace_id
        self.user_id = user_id

    def _get_company_identity(self) -> Dict[str, Any]:
        """Trích xuất Vision, Mission và Core Values của Company."""
        # G2 P0.5 / G3 §10.2: fallback đồng bộ với default mới của Workspace.company_stage.
        company_stage = "S0_GENESIS"
        vision = None
        mission = None
        values: List[str] = []

        workspace = self.db.query(Workspace).filter(Workspace.id == self.workspace_id).first()
        if workspace and getattr(workspace, "company_stage", None):
            company_stage = workspace.company_stage

        # Tìm StrategyFoundation mới nhất
        canvas = (
            self.db.query(StrategyCanvas)
            .filter(StrategyCanvas.workspace_id == self.workspace_id)
            .order_by(desc(StrategyCanvas.created_at))
            .first()
        )
        if canvas:
            rev = (
                self.db.query(StrategyRevision)
                .filter(StrategyRevision.canvas_id == canvas.id)
                .order_by(desc(StrategyRevision.revision_no))
                .first()
            )
            if rev:
                foundation = (
                    self.db.query(StrategyFoundation)
                    .filter(StrategyFoundation.strategy_revision_id == rev.id)
                    .first()
                )
                if foundation:
                    vision = foundation.vision
                    mission = foundation.mission
                    core_vals = (
                        self.db.query(CoreValue)
                        .filter(CoreValue.foundation_id == foundation.id)
                        .order_by(CoreValue.slot_no.asc())
                        .all()
                    )
                    values = [v.title for v in core_vals if v.title]

        return {
            "company_stage": company_stage,
            "vision": vision,
            "mission": mission,
            "values": values
        }

    def _resolve_project(self, project_id: Optional[int] = None) -> Optional[Project]:
        """Tìm Project tương ứng hoặc tự động fallback về Project P0 active."""
        if project_id:
            return (
                self.db.query(Project)
                .filter(Project.id == project_id, Project.workspace_id == self.workspace_id)
                .first()
            )

        # Fallback: Ưu tiên Project active có strategic_priority P0 hoặc mới nhất
        project = (
            self.db.query(Project)
            .filter(Project.workspace_id == self.workspace_id, Project.status == "active")
            .order_by(
                desc(Project.strategic_priority == "P0"),
                desc(Project.created_at)
            )
            .first()
        )
        if not project:
            project = (
                self.db.query(Project)
                .filter(Project.workspace_id == self.workspace_id)
                .order_by(desc(Project.created_at))
                .first()
            )
        return project

    def resolve_context(self, project_id: Optional[int] = None) -> StageContextResponse:
        """Phân giải toàn diện ngữ cảnh điều hành theo Stage."""
        company_info = self._get_company_identity()
        project = self._resolve_project(project_id)

        if project:
            raw_stage = getattr(project, "project_stage", None) or "S1_PROBLEM_VALIDATION"
            try:
                stage_enum = ProjectStageEnum(raw_stage)
            except ValueError:
                stage_enum = ProjectStageEnum.S1_PROBLEM_VALIDATION

            policy = ManagementPolicyEngine.get_policy(stage_enum)

            return StageContextResponse(
                workspace_id=self.workspace_id,
                company_stage=company_info["company_stage"],
                company_vision=company_info["vision"],
                company_mission=company_info["mission"],
                company_values=company_info["values"],
                project_id=project.id,
                project_title=project.title,
                project_type=project.project_type,
                project_stage=stage_enum,
                stage_started_at=getattr(project, "stage_started_at", None),
                stage_goal=getattr(project, "stage_goal", None) or policy.primary_goal,
                critical_constraints=getattr(project, "critical_constraints", []) or [],
                exit_criteria=getattr(project, "exit_criteria_jsonb", {}) or {},
                stage_metadata=getattr(project, "stage_metadata", {}) or {},
                policy=policy
            )

        # Trường hợp workspace chưa có Project nào
        default_stage = ProjectStageEnum.S1_PROBLEM_VALIDATION
        policy = ManagementPolicyEngine.get_policy(default_stage)

        return StageContextResponse(
            workspace_id=self.workspace_id,
            company_stage=company_info["company_stage"],
            company_vision=company_info["vision"],
            company_mission=company_info["mission"],
            company_values=company_info["values"],
            project_id=None,
            project_title=None,
            project_type=None,
            project_stage=default_stage,
            stage_started_at=None,
            stage_goal=policy.primary_goal,
            critical_constraints=[],
            exit_criteria={},
            stage_metadata={},
            policy=policy
        )
