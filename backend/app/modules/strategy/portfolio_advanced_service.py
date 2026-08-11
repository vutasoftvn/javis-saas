import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.core.tenancy import (

    get_portfolio_scoped,
    get_project_scoped,
)
from app.modules.strategy.models import (
    Portfolio,
    SwotItem,
    TowsOption,
    PortfolioSynergy,
    PortfolioDependency,
    PortfolioOption,
    StrategyAnalysis,
    ContextPack,
)

logger = logging.getLogger(__name__)

VALID_SYNERGY_TYPES = {"REVENUE", "COST_SAVING", "SHARED_CAPABILITY", "DATA_NETWORK"}
VALID_DEPENDENCY_TYPES = {"BLOCKS", "ENABLES", "REQUIRES_MILESTONE"}
VALID_RISK_LEVELS = {"LOW", "MEDIUM", "HIGH"}
VALID_OPTION_STATUSES = {"draft", "under_review", "selected", "rejected"}


class PortfolioAdvancedService:
    """Portfolio Advanced Intelligence Engine (mCOSA V12 Spec §25–27 & Sprint 7).

    Quản lý SWOT/TOWS cấp Danh mục, Ma trận Cộng hưởng (Synergies), Phụ thuộc (Dependencies),
    và Tùy chọn chiến lược cấp Portfolio (Portfolio Options).
    """

    def __init__(self, db: Session, workspace_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.workspace_id = workspace_id
        self.user_id = user_id

    # ------------------------------------------------------------------
    # Portfolio SWOT & TOWS
    # ------------------------------------------------------------------

    def add_portfolio_swot_item(
        self,
        portfolio_id: uuid.UUID,
        category: str,
        statement: str,
        impact: str = "medium",
        likelihood: str = "medium",
        confidence: str = "medium",
        evidence_status: str = "hypothesis",
    ) -> Dict[str, Any]:
        get_portfolio_scoped(self.db, portfolio_id, self.workspace_id)
        analysis = self._get_or_create_portfolio_analysis(portfolio_id, "SWOT")

        item = SwotItem(
            id=uuid.UUID(int=generate_snowflake_id()),
            workspace_id=self.workspace_id,
            portfolio_id=portfolio_id,
            analysis_id=analysis.id,
            category=category.upper(),
            statement=statement,
            impact=impact,
            likelihood=likelihood,
            confidence=confidence,
            evidence_status=evidence_status,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return self._serialize_swot_item(item)

    def get_portfolio_swot(self, portfolio_id: uuid.UUID) -> List[Dict[str, Any]]:
        get_portfolio_scoped(self.db, portfolio_id, self.workspace_id)
        items = (
            self.db.query(SwotItem)
            .filter(
                SwotItem.portfolio_id == portfolio_id,
                SwotItem.workspace_id == self.workspace_id,
            )
            .all()
        )
        return [self._serialize_swot_item(i) for i in items]

    def add_portfolio_tows_option(
        self,
        portfolio_id: uuid.UUID,
        quadrant: str,
        title: str,
        tradeoffs: str = "",
        expected_impact: str = "medium",
        confidence: str = "medium",
        status_val: str = "draft",
    ) -> Dict[str, Any]:
        get_portfolio_scoped(self.db, portfolio_id, self.workspace_id)
        analysis = self._get_or_create_portfolio_analysis(portfolio_id, "TOWS")

        tows = TowsOption(
            id=uuid.UUID(int=generate_snowflake_id()),
            workspace_id=self.workspace_id,
            portfolio_id=portfolio_id,
            analysis_id=analysis.id,
            quadrant=quadrant.upper(),
            title=title,
            tradeoffs=tradeoffs,
            expected_impact=expected_impact,
            confidence=confidence,
            status=status_val,
        )
        self.db.add(tows)
        self.db.commit()
        self.db.refresh(tows)
        return self._serialize_tows_option(tows)

    def get_portfolio_tows(self, portfolio_id: uuid.UUID) -> List[Dict[str, Any]]:
        get_portfolio_scoped(self.db, portfolio_id, self.workspace_id)
        items = (
            self.db.query(TowsOption)
            .filter(
                TowsOption.portfolio_id == portfolio_id,
                TowsOption.workspace_id == self.workspace_id,
            )
            .all()
        )
        return [self._serialize_tows_option(t) for t in items]

    # ------------------------------------------------------------------
    # Portfolio Synergies (Spec §25)
    # ------------------------------------------------------------------

    def add_portfolio_synergy(
        self,
        portfolio_id: uuid.UUID,
        source_project_id: uuid.UUID,
        target_project_id: uuid.UUID,
        synergy_type: str = "SHARED_CAPABILITY",
        description: str = "",
        estimated_value: Optional[float] = None,
        status_val: str = "identified",
    ) -> Dict[str, Any]:
        get_portfolio_scoped(self.db, portfolio_id, self.workspace_id)
        get_project_scoped(self.db, source_project_id, self.workspace_id)
        get_project_scoped(self.db, target_project_id, self.workspace_id)

        syn_type_upper = synergy_type.upper()
        if syn_type_upper not in VALID_SYNERGY_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Loại cộng hưởng không hợp lệ. Phải thuộc: {VALID_SYNERGY_TYPES}",
            )

        synergy = PortfolioSynergy(
            id=uuid.UUID(int=generate_snowflake_id()),
            workspace_id=self.workspace_id,
            portfolio_id=portfolio_id,
            source_project_id=source_project_id,
            target_project_id=target_project_id,
            synergy_type=syn_type_upper,
            description=description,
            estimated_value=estimated_value,
            status=status_val,
            created_at=datetime.utcnow(),
        )
        self.db.add(synergy)
        self.db.commit()
        self.db.refresh(synergy)
        return self._serialize_synergy(synergy)

    def list_portfolio_synergies(self, portfolio_id: uuid.UUID) -> List[Dict[str, Any]]:
        get_portfolio_scoped(self.db, portfolio_id, self.workspace_id)
        items = (
            self.db.query(PortfolioSynergy)
            .filter(
                PortfolioSynergy.portfolio_id == portfolio_id,
                PortfolioSynergy.workspace_id == self.workspace_id,
            )
            .all()
        )
        return [self._serialize_synergy(s) for s in items]

    def delete_portfolio_synergy(self, synergy_id: uuid.UUID) -> Dict[str, Any]:
        syn = (
            self.db.query(PortfolioSynergy)
            .filter(
                PortfolioSynergy.id == synergy_id,
                PortfolioSynergy.workspace_id == self.workspace_id,
            )
            .first()
        )
        if not syn:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PortfolioSynergy not found")
        self.db.delete(syn)
        self.db.commit()
        return {"deleted": True, "synergy_id": str(synergy_id)}

    # ------------------------------------------------------------------
    # Portfolio Dependencies (Spec §26)
    # ------------------------------------------------------------------

    def add_portfolio_dependency(
        self,
        portfolio_id: uuid.UUID,
        predecessor_project_id: uuid.UUID,
        successor_project_id: uuid.UUID,
        dependency_type: str = "BLOCKS",
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        get_portfolio_scoped(self.db, portfolio_id, self.workspace_id)
        get_project_scoped(self.db, predecessor_project_id, self.workspace_id)
        get_project_scoped(self.db, successor_project_id, self.workspace_id)

        dep_type_upper = dependency_type.upper()
        if dep_type_upper not in VALID_DEPENDENCY_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Loại phụ thuộc không hợp lệ. Phải thuộc: {VALID_DEPENDENCY_TYPES}",
            )

        dependency = PortfolioDependency(
            id=uuid.UUID(int=generate_snowflake_id()),
            workspace_id=self.workspace_id,
            portfolio_id=portfolio_id,
            predecessor_project_id=predecessor_project_id,
            successor_project_id=successor_project_id,
            dependency_type=dep_type_upper,
            description=description,
            created_at=datetime.utcnow(),
        )
        self.db.add(dependency)
        self.db.commit()
        self.db.refresh(dependency)
        return self._serialize_dependency(dependency)

    def list_portfolio_dependencies(self, portfolio_id: uuid.UUID) -> List[Dict[str, Any]]:
        get_portfolio_scoped(self.db, portfolio_id, self.workspace_id)
        items = (
            self.db.query(PortfolioDependency)
            .filter(
                PortfolioDependency.portfolio_id == portfolio_id,
                PortfolioDependency.workspace_id == self.workspace_id,
            )
            .all()
        )
        return [self._serialize_dependency(d) for d in items]

    def delete_portfolio_dependency(self, dependency_id: uuid.UUID) -> Dict[str, Any]:
        dep = (
            self.db.query(PortfolioDependency)
            .filter(
                PortfolioDependency.id == dependency_id,
                PortfolioDependency.workspace_id == self.workspace_id,
            )
            .first()
        )
        if not dep:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PortfolioDependency not found")
        self.db.delete(dep)
        self.db.commit()
        return {"deleted": True, "dependency_id": str(dependency_id)}

    # ------------------------------------------------------------------
    # Portfolio Strategic Options (Spec §27)
    # ------------------------------------------------------------------

    def create_portfolio_option(
        self,
        portfolio_id: uuid.UUID,
        title: str,
        description: Optional[str] = None,
        tows_option_id: Optional[uuid.UUID] = None,
        strategic_fit_score: float = 0.8,
        feasibility_score: float = 0.7,
        risk_level: str = "MEDIUM",
        status_val: str = "draft",
    ) -> Dict[str, Any]:
        get_portfolio_scoped(self.db, portfolio_id, self.workspace_id)

        risk_upper = risk_level.upper()
        if risk_upper not in VALID_RISK_LEVELS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Mức rủi ro không hợp lệ. Phải thuộc: {VALID_RISK_LEVELS}",
            )

        option = PortfolioOption(
            id=uuid.UUID(int=generate_snowflake_id()),
            workspace_id=self.workspace_id,
            portfolio_id=portfolio_id,
            tows_option_id=tows_option_id,
            title=title,
            description=description,
            strategic_fit_score=strategic_fit_score,
            feasibility_score=feasibility_score,
            risk_level=risk_upper,
            status=status_val,
            created_at=datetime.utcnow(),
        )
        self.db.add(option)
        self.db.commit()
        self.db.refresh(option)
        return self._serialize_option(option)

    def list_portfolio_options(self, portfolio_id: uuid.UUID) -> List[Dict[str, Any]]:
        get_portfolio_scoped(self.db, portfolio_id, self.workspace_id)
        options = (
            self.db.query(PortfolioOption)
            .filter(
                PortfolioOption.portfolio_id == portfolio_id,
                PortfolioOption.workspace_id == self.workspace_id,
            )
            .all()
        )
        return [self._serialize_option(o) for o in options]

    def update_portfolio_option(
        self,
        option_id: uuid.UUID,
        status_val: Optional[str] = None,
        strategic_fit_score: Optional[float] = None,
        feasibility_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        option = (
            self.db.query(PortfolioOption)
            .filter(
                PortfolioOption.id == option_id,
                PortfolioOption.workspace_id == self.workspace_id,
            )
            .first()
        )
        if not option:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PortfolioOption not found")

        if status_val is not None:
            option.status = status_val
        if strategic_fit_score is not None:
            option.strategic_fit_score = strategic_fit_score
        if feasibility_score is not None:
            option.feasibility_score = feasibility_score

        self.db.commit()
        self.db.refresh(option)
        return self._serialize_option(option)

    # ------------------------------------------------------------------
    # Helpers & Serializers
    # ------------------------------------------------------------------

    def _get_or_create_portfolio_analysis(
        self, portfolio_id: uuid.UUID, kind: str
    ) -> StrategyAnalysis:
        analysis = (
            self.db.query(StrategyAnalysis)
            .filter(
                StrategyAnalysis.portfolio_id == portfolio_id,
                StrategyAnalysis.workspace_id == self.workspace_id,
                StrategyAnalysis.kind == kind,
            )
            .first()
        )
        if not analysis:
            pack = (
                self.db.query(ContextPack)
                .filter(ContextPack.workspace_id == self.workspace_id)
                .first()
            )
            if not pack:
                pack = ContextPack(
                    id=uuid.UUID(int=generate_snowflake_id()),
                    workspace_id=self.workspace_id,
                    name="Portfolio Analysis Pack",
                    created_at=datetime.utcnow(),
                )
                self.db.add(pack)
                self.db.flush()

            analysis = StrategyAnalysis(
                id=uuid.UUID(int=generate_snowflake_id()),
                workspace_id=self.workspace_id,
                portfolio_id=portfolio_id,
                context_pack_id=pack.id,
                kind=kind,
                status="active",
                created_at=datetime.utcnow(),
            )
            self.db.add(analysis)
            self.db.flush()
        return analysis

    def _serialize_swot_item(self, item: SwotItem) -> Dict[str, Any]:
        return {
            "id": str(item.id),
            "portfolio_id": str(item.portfolio_id) if item.portfolio_id else None,
            "category": item.category,
            "statement": item.statement,
            "impact": item.impact,
            "likelihood": item.likelihood,
            "confidence": item.confidence,
            "evidence_status": item.evidence_status,
        }

    def _serialize_tows_option(self, t: TowsOption) -> Dict[str, Any]:
        return {
            "id": str(t.id),
            "portfolio_id": str(t.portfolio_id) if t.portfolio_id else None,
            "quadrant": t.quadrant,
            "title": t.title,
            "tradeoffs": t.tradeoffs,
            "expected_impact": t.expected_impact,
            "confidence": t.confidence,
            "status": t.status,
        }

    def _serialize_synergy(self, s: PortfolioSynergy) -> Dict[str, Any]:
        return {
            "id": str(s.id),
            "portfolio_id": str(s.portfolio_id),
            "source_project_id": str(s.source_project_id),
            "target_project_id": str(s.target_project_id),
            "synergy_type": s.synergy_type,
            "description": s.description,
            "estimated_value": s.estimated_value,
            "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }

    def _serialize_dependency(self, d: PortfolioDependency) -> Dict[str, Any]:
        return {
            "id": str(d.id),
            "portfolio_id": str(d.portfolio_id),
            "predecessor_project_id": str(d.predecessor_project_id),
            "successor_project_id": str(d.successor_project_id),
            "dependency_type": d.dependency_type,
            "description": d.description,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }

    def _serialize_option(self, o: PortfolioOption) -> Dict[str, Any]:
        return {
            "id": str(o.id),
            "portfolio_id": str(o.portfolio_id),
            "tows_option_id": str(o.tows_option_id) if o.tows_option_id else None,
            "title": o.title,
            "description": o.description,
            "strategic_fit_score": o.strategic_fit_score,
            "feasibility_score": o.feasibility_score,
            "risk_level": o.risk_level,
            "status": o.status,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
