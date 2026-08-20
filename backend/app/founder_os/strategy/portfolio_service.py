import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.core.tenancy import (

    get_portfolio_scoped,
    get_portfolio_project_scoped,
    get_project_scoped,
)
from app.founder_os.strategy.models import (
    Portfolio,
    PortfolioProject,
    Project,
    PestelItem,
    ProjectPestelImpact,
    StrategyAnalysis,
    ContextPack,
)

logger = logging.getLogger(__name__)

VALID_PRIORITIES = {"core", "growth", "experimental", "maintenance"}
VALID_IMPACT_TYPES = {"POSITIVE", "NEGATIVE", "NEUTRAL"}
VALID_MAGNITUDES = {"HIGH", "MEDIUM", "LOW"}


class PortfolioDetectorService:
    """Quy tắc xác định sự cần thiết của Portfolio (Portfolio Detector - Spec §22).

    Dịch vụ thuần quy tắc (Rule-based, không cần AI):
    - Khi có từ 2 dự án chiến lược đang active.
    - Hoặc có tranh chấp năng lực sáng lập/tài nguyên giữa các sáng kiến.
    """

    def __init__(self, db: Session, workspace_id: int):
        self.db = db
        self.workspace_id = workspace_id

    def detect(self) -> Dict[str, Any]:
        active_projects = (
            self.db.query(Project)
            .filter(
                Project.workspace_id == self.workspace_id,
                Project.status.in_(["active", "in_progress", "planning", "draft"]),
            )
            .all()
        )
        active_count = len(active_projects)

        existing_portfolios = (
            self.db.query(Portfolio)
            .filter(
                Portfolio.workspace_id == self.workspace_id,
                Portfolio.status == "active",
            )
            .count()
        )

        needs_portfolio = active_count >= 2
        trigger = "MULTI_PROJECTS" if needs_portfolio else "SINGLE_PROJECT"
        reason = (
            f"Phát hiện có {active_count} dự án đang hoạt động đồng thời (Spec §22). "
            "Cần thiết lập Portfolio để quản trị danh mục, chia sẻ PESTEL và cân bằng năng lực sáng lập (Founder Attention)."
            if needs_portfolio
            else f"Không gian làm việc hiện có {active_count} dự án, chưa có xung đột đa danh mục."
        )

        return {
            "workspace_id": str(self.workspace_id),
            "needs_portfolio": needs_portfolio,
            "trigger": trigger,
            "reason": reason,
            "active_projects_count": active_count,
            "existing_portfolios_count": existing_portfolios,
            "suggested_actions": [
                "Tạo Shared PESTEL để nhận diện rủi ro/cơ hội vĩ mô tác động chéo lên toàn bộ dự án",
                "Phân bổ tỷ trọng chú ý của Founder (% Attention / giờ tuần) cho từng dự án Core / Growth",
                "Thiết lập Ma trận Tác động Dự án (Impact Matrix)",
            ]
            if needs_portfolio
            else ["Tiếp tục vận hành dưới mô hình Dự án đơn lẻ (Single Project Execution)"],
        }


class PortfolioService:
    """Portfolio Intelligence Engine (mCOSA V12 Spec §21–24 & Sprint 6).

    Quản lý Danh mục dự án, Shared PESTEL và Ma trận tác động chéo (Project PESTEL Impact Matrix).
    """

    def __init__(self, db: Session, workspace_id: int, user_id: int):
        self.db = db
        self.workspace_id = workspace_id
        self.user_id = user_id

    # ------------------------------------------------------------------
    # Portfolio CRUD
    # ------------------------------------------------------------------

    def create_portfolio(
        self,
        name: str,
        description: Optional[str] = None,
        strategic_focus: Optional[str] = None,
        brain_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        now = datetime.utcnow()
        portfolio = Portfolio(
            id=generate_snowflake_id(),
            workspace_id=self.workspace_id,
            brain_id=brain_id,
            name=name,
            description=description,
            strategic_focus=strategic_focus,
            status="active",
            created_at=now,
            updated_at=now,
        )
        self.db.add(portfolio)
        self.db.commit()
        self.db.refresh(portfolio)
        return self._serialize_portfolio(portfolio)

    def get_portfolio(self, portfolio_id: int) -> Dict[str, Any]:
        portfolio = get_portfolio_scoped(self.db, portfolio_id, self.workspace_id)
        return self._serialize_portfolio(portfolio)

    def list_portfolios(self) -> List[Dict[str, Any]]:
        portfolios = (
            self.db.query(Portfolio)
            .filter(
                Portfolio.workspace_id == self.workspace_id,
            )
            .order_by(Portfolio.created_at.desc())
            .all()
        )
        return [self._serialize_portfolio(p) for p in portfolios]

    def update_portfolio(
        self,
        portfolio_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        strategic_focus: Optional[str] = None,
        status_val: Optional[str] = None,
    ) -> Dict[str, Any]:
        portfolio = get_portfolio_scoped(self.db, portfolio_id, self.workspace_id)
        if name is not None:
            portfolio.name = name
        if description is not None:
            portfolio.description = description
        if strategic_focus is not None:
            portfolio.strategic_focus = strategic_focus
        if status_val is not None:
            portfolio.status = status_val
        portfolio.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(portfolio)
        return self._serialize_portfolio(portfolio)

    def delete_portfolio(self, portfolio_id: int) -> Dict[str, Any]:
        portfolio = get_portfolio_scoped(self.db, portfolio_id, self.workspace_id)
        self.db.delete(portfolio)
        self.db.commit()
        return {"deleted": True, "portfolio_id": str(portfolio_id)}

    # ------------------------------------------------------------------
    # Portfolio Projects Management & Zero-Trust Scoping (§57, §62.8)
    # ------------------------------------------------------------------

    def add_project_to_portfolio(
        self,
        portfolio_id: int,
        project_id: int,
        strategic_priority: str = "core",
        capacity_allocation: float = 0.0,
        founder_attention_hours: float = 0.0,
    ) -> Dict[str, Any]:
        get_portfolio_scoped(self.db, portfolio_id, self.workspace_id)
        # Spec §57, §62.8: Portfolio membership must not grant access to a restricted project
        # get_project_scoped enforces project belongs to the tenant
        get_project_scoped(self.db, project_id, self.workspace_id)

        priority_lower = strategic_priority.lower()
        if priority_lower not in VALID_PRIORITIES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Độ ưu tiên chiến lược không hợp lệ. Phải thuộc: {VALID_PRIORITIES}",
            )

        existing = (
            self.db.query(PortfolioProject)
            .filter(
                PortfolioProject.portfolio_id == portfolio_id,
                PortfolioProject.project_id == project_id,
                PortfolioProject.workspace_id == self.workspace_id,
            )
            .first()
        )
        if existing:
            existing.strategic_priority = priority_lower
            existing.capacity_allocation = capacity_allocation
            existing.founder_attention_hours = founder_attention_hours
            self.db.commit()
            self.db.refresh(existing)
            return self._serialize_portfolio_project(existing)

        pp = PortfolioProject(
            id=generate_snowflake_id(),
            workspace_id=self.workspace_id,
            portfolio_id=portfolio_id,
            project_id=project_id,
            strategic_priority=priority_lower,
            capacity_allocation=capacity_allocation,
            founder_attention_hours=founder_attention_hours,
            created_at=datetime.utcnow(),
        )
        self.db.add(pp)
        self.db.commit()
        self.db.refresh(pp)
        return self._serialize_portfolio_project(pp)

    def remove_project_from_portfolio(
        self, portfolio_id: int, project_id: int
    ) -> Dict[str, Any]:
        pp = get_portfolio_project_scoped(self.db, portfolio_id, project_id, self.workspace_id)
        self.db.delete(pp)
        self.db.commit()
        return {"removed": True, "portfolio_id": str(portfolio_id), "project_id": str(project_id)}

    def list_portfolio_projects(
        self, 
        portfolio_id: int,
        operating_unit_id: Optional[int] = None,
        offering_id: Optional[int] = None,
        initiative_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        get_portfolio_scoped(self.db, portfolio_id, self.workspace_id)
        
        query = (
            self.db.query(PortfolioProject)
            .join(Project, PortfolioProject.project_id == Project.id)
            .filter(
                PortfolioProject.portfolio_id == portfolio_id,
                PortfolioProject.workspace_id == self.workspace_id,
            )
        )
        
        if initiative_id:
            from core.strategy.initiative import Initiative
            query = query.join(Initiative, Project.id == Initiative.project_id)
            query = query.filter(Initiative.id == initiative_id)
        elif offering_id or operating_unit_id:
            from core.strategy.initiative import Initiative
            from core.organization.models import Offering
            query = query.join(Initiative, Project.id == Initiative.project_id)
            if offering_id:
                query = query.filter(Initiative.offering_id == offering_id)
            elif operating_unit_id:
                query = query.join(Offering, Initiative.offering_id == Offering.id)
                query = query.filter(Offering.operating_unit_id == operating_unit_id)

        items = query.all()
        return [self._serialize_portfolio_project(item) for item in items]

    # ------------------------------------------------------------------
    # Shared PESTEL & Project Impact Matrix (Spec §24)
    # ------------------------------------------------------------------

    def get_portfolio_pestel(self, portfolio_id: int) -> List[Dict[str, Any]]:
        get_portfolio_scoped(self.db, portfolio_id, self.workspace_id)
        items = (
            self.db.query(PestelItem)
            .filter(
                PestelItem.portfolio_id == portfolio_id,
                PestelItem.workspace_id == self.workspace_id,
            )
            .all()
        )
        return [self._serialize_pestel_item(item) for item in items]

    def add_portfolio_pestel_item(
        self,
        portfolio_id: int,
        factor: str,
        statement: str,
        impact: str = "medium",
        horizon: str = "medium",
        confidence: str = "medium",
        evidence_status: str = "hypothesis",
    ) -> Dict[str, Any]:
        get_portfolio_scoped(self.db, portfolio_id, self.workspace_id)

        # Get or create a default Analysis for portfolio
        analysis = (
            self.db.query(StrategyAnalysis)
            .filter(
                StrategyAnalysis.portfolio_id == portfolio_id,
                StrategyAnalysis.workspace_id == self.workspace_id,
                StrategyAnalysis.kind == "PESTEL",
            )
            .first()
        )
        if not analysis:
            # Need a ContextPack
            pack = (
                self.db.query(ContextPack)
                .filter(ContextPack.workspace_id == self.workspace_id)
                .first()
            )
            if not pack:
                pack = ContextPack(
                    id=generate_snowflake_id(),
                    workspace_id=self.workspace_id,
                    name="Default Portfolio Context",
                    created_at=datetime.utcnow(),
                )
                self.db.add(pack)
                self.db.flush()

            analysis = StrategyAnalysis(
                id=generate_snowflake_id(),
                workspace_id=self.workspace_id,
                portfolio_id=portfolio_id,
                context_pack_id=pack.id,
                kind="PESTEL",
                status="active",
                created_at=datetime.utcnow(),
            )
            self.db.add(analysis)
            self.db.flush()

        item = PestelItem(
            id=generate_snowflake_id(),
            workspace_id=self.workspace_id,
            portfolio_id=portfolio_id,
            analysis_id=analysis.id,
            factor=factor,
            statement=statement,
            impact=impact,
            horizon=horizon,
            confidence=confidence,
            evidence_status=evidence_status,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return self._serialize_pestel_item(item)

    def set_project_pestel_impact(
        self,
        project_id: int,
        pestel_item_id: int,
        impact_type: str = "POSITIVE",
        impact_magnitude: str = "MEDIUM",
        impact_analysis: Optional[str] = None,
        mitigation_or_leverage: Optional[str] = None,
    ) -> Dict[str, Any]:
        get_project_scoped(self.db, project_id, self.workspace_id)

        pestel = (
            self.db.query(PestelItem)
            .filter(
                PestelItem.id == pestel_item_id,
                PestelItem.workspace_id == self.workspace_id,
            )
            .first()
        )
        if not pestel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PestelItem not found")

        type_upper = impact_type.upper()
        if type_upper not in VALID_IMPACT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Loại tác động không hợp lệ. Phải thuộc: {VALID_IMPACT_TYPES}",
            )

        mag_upper = impact_magnitude.upper()
        if mag_upper not in VALID_MAGNITUDES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Mức độ tác động không hợp lệ. Phải thuộc: {VALID_MAGNITUDES}",
            )

        impact_rec = (
            self.db.query(ProjectPestelImpact)
            .filter(
                ProjectPestelImpact.project_id == project_id,
                ProjectPestelImpact.pestel_item_id == pestel_item_id,
                ProjectPestelImpact.workspace_id == self.workspace_id,
            )
            .first()
        )
        if impact_rec:
            impact_rec.impact_type = type_upper
            impact_magnitude = mag_upper
            impact_rec.impact_analysis = impact_analysis
            impact_rec.mitigation_or_leverage = mitigation_or_leverage
        else:
            impact_rec = ProjectPestelImpact(
                id=generate_snowflake_id(),
                workspace_id=self.workspace_id,
                project_id=project_id,
                pestel_item_id=pestel_item_id,
                impact_type=type_upper,
                impact_magnitude=mag_upper,
                impact_analysis=impact_analysis,
                mitigation_or_leverage=mitigation_or_leverage,
                created_at=datetime.utcnow(),
            )
            self.db.add(impact_rec)

        self.db.commit()
        self.db.refresh(impact_rec)
        return self._serialize_impact(impact_rec)

    def get_portfolio_impact_matrix(self, portfolio_id: int) -> Dict[str, Any]:
        get_portfolio_scoped(self.db, portfolio_id, self.workspace_id)
        projects = (
            self.db.query(PortfolioProject)
            .filter(
                PortfolioProject.portfolio_id == portfolio_id,
                PortfolioProject.workspace_id == self.workspace_id,
            )
            .all()
        )
        project_ids = [pp.project_id for pp in projects]

        pestel_items = (
            self.db.query(PestelItem)
            .filter(
                PestelItem.portfolio_id == portfolio_id,
                PestelItem.workspace_id == self.workspace_id,
            )
            .all()
        )

        impacts = (
            self.db.query(ProjectPestelImpact)
            .filter(
                ProjectPestelImpact.project_id.in_(project_ids),
                ProjectPestelImpact.workspace_id == self.workspace_id,
            )
            .all()
            if project_ids
            else []
        )

        return {
            "portfolio_id": str(portfolio_id),
            "projects": [self._serialize_portfolio_project(pp) for pp in projects],
            "pestel_items": [self._serialize_pestel_item(pi) for pi in pestel_items],
            "impacts": [self._serialize_impact(imp) for imp in impacts],
        }

    # ------------------------------------------------------------------
    # Serializers
    # ------------------------------------------------------------------

    def _serialize_portfolio(self, p: Portfolio) -> Dict[str, Any]:
        projects_count = (
            self.db.query(PortfolioProject)
            .filter(PortfolioProject.portfolio_id == p.id)
            .count()
        )
        return {
            "id": str(p.id),
            "workspace_id": str(p.workspace_id),
            "brain_id": str(p.brain_id) if p.brain_id else None,
            "name": p.name,
            "description": p.description,
            "strategic_focus": p.strategic_focus,
            "status": p.status,
            "projects_count": projects_count,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }

    def _serialize_portfolio_project(self, pp: PortfolioProject) -> Dict[str, Any]:
        proj = self.db.query(Project).filter(Project.id == pp.project_id).first()
        return {
            "id": str(pp.id),
            "portfolio_id": str(pp.portfolio_id),
            "project_id": str(pp.project_id),
            "project_name": proj.title if proj else "Unknown",
            "project_status": proj.status if proj else "unknown",
            "strategic_priority": pp.strategic_priority,
            "capacity_allocation": pp.capacity_allocation,
            "founder_attention_hours": pp.founder_attention_hours,
            "created_at": pp.created_at.isoformat() if pp.created_at else None,
        }


    def _serialize_pestel_item(self, item: PestelItem) -> Dict[str, Any]:
        return {
            "id": str(item.id),
            "portfolio_id": str(item.portfolio_id) if item.portfolio_id else None,
            "analysis_id": str(item.analysis_id),
            "factor": item.factor,
            "statement": item.statement,
            "impact": item.impact,
            "horizon": item.horizon,
            "confidence": item.confidence,
            "evidence_status": item.evidence_status,
        }

    def _serialize_impact(self, imp: ProjectPestelImpact) -> Dict[str, Any]:
        return {
            "id": str(imp.id),
            "project_id": str(imp.project_id),
            "pestel_item_id": str(imp.pestel_item_id),
            "impact_type": imp.impact_type,
            "impact_magnitude": imp.impact_magnitude,
            "impact_analysis": imp.impact_analysis,
            "mitigation_or_leverage": imp.mitigation_or_leverage,
            "created_at": imp.created_at.isoformat() if imp.created_at else None,
        }
