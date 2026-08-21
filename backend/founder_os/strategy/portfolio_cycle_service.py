import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.snowflake import generate_snowflake_id
from core.tenancy import get_portfolio_scoped, get_project_scoped

from founder_os.strategy.models import (
    Portfolio,
    PortfolioProject,
    FounderProfile,
    PortfolioCycle,
    CapacityAllocation,
    FounderAttentionAllocation,
)

logger = logging.getLogger(__name__)


class PortfolioCycleService:
    """Portfolio 12WY Execution, WIP Limit & Founder Attention Engine (mCOSA V12 Spec §28–31 & Sprint 8)."""

    def __init__(self, db: Session, workspace_id: int, user_id: int):
        self.db = db
        self.workspace_id = workspace_id
        self.user_id = user_id

    # ------------------------------------------------------------------
    # Founder Profile & WIP Limit Management (Spec §31)
    # ------------------------------------------------------------------

    def get_or_create_founder_profile(self) -> FounderProfile:

        profile = (
            self.db.query(FounderProfile)
            .filter(
                FounderProfile.workspace_id == self.workspace_id,
                FounderProfile.user_id == self.user_id,
            )
            .first()
        )
        if not profile:
            profile = FounderProfile(
                id=generate_snowflake_id(),
                workspace_id=self.workspace_id,
                user_id=self.user_id,
                weekly_capacity_hours=40.0,
                max_active_strategic_projects=3,  # Spec §31 Default WIP Limit
                created_at=datetime.utcnow(),
            )
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
        return profile

    def update_founder_profile(
        self,
        weekly_capacity_hours: Optional[float] = None,
        max_active_strategic_projects: Optional[int] = None,
    ) -> Dict[str, Any]:
        profile = self.get_or_create_founder_profile()
        if weekly_capacity_hours is not None:
            profile.weekly_capacity_hours = weekly_capacity_hours
        if max_active_strategic_projects is not None:
            if max_active_strategic_projects < 1:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Hạn mức dự án tối đa (WIP Limit) phải >= 1",
                )
            profile.max_active_strategic_projects = max_active_strategic_projects

        profile.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(profile)
        return self._serialize_founder_profile(profile)

    # ------------------------------------------------------------------
    # Portfolio Cycle & WIP Limit Activation Gate (Spec §28–31)
    # ------------------------------------------------------------------

    def create_portfolio_cycle(
        self,
        portfolio_id: int,
        title: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        get_portfolio_scoped(self.db, portfolio_id, self.workspace_id)
        start = start_date or datetime.utcnow()
        end = end_date or datetime.utcnow()

        cycle = PortfolioCycle(
            id=generate_snowflake_id(),
            workspace_id=self.workspace_id,

            portfolio_id=portfolio_id,
            title=title,
            status="draft",
            start_date=start,
            end_date=end,
            active_project_count=0,
            created_at=datetime.utcnow(),
        )
        self.db.add(cycle)
        self.db.commit()
        self.db.refresh(cycle)
        return self._serialize_cycle(cycle)

    def list_portfolio_cycles(self, portfolio_id: int) -> List[Dict[str, Any]]:
        get_portfolio_scoped(self.db, portfolio_id, self.workspace_id)
        cycles = (
            self.db.query(PortfolioCycle)
            .filter(
                PortfolioCycle.portfolio_id == portfolio_id,
                PortfolioCycle.workspace_id == self.workspace_id,
            )
            .all()
        )
        return [self._serialize_cycle(c) for c in cycles]

    def activate_portfolio_cycle(self, portfolio_cycle_id: int) -> Dict[str, Any]:
        """Kích hoạt Chu kỳ Portfolio 12WY với kiểm tra nghiêm ngặt Hạn mức WIP Limit (Spec §31)."""
        cycle = (
            self.db.query(PortfolioCycle)
            .filter(
                PortfolioCycle.id == portfolio_cycle_id,
                PortfolioCycle.workspace_id == self.workspace_id,
            )
            .first()
        )
        if not cycle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PortfolioCycle not found")

        # 1. Thống kê số lượng dự án trong Portfolio
        active_project_count = (
            self.db.query(PortfolioProject)
            .filter(
                PortfolioProject.portfolio_id == cycle.portfolio_id,
                PortfolioProject.workspace_id == self.workspace_id,
            )
            .count()
        )

        # 2. Đọc cấu hình WIP Limit từ FounderProfile (Spec §31)
        founder = self.get_or_create_founder_profile()
        wip_limit = founder.max_active_strategic_projects

        # 3. Enforce Activation Gate
        if active_project_count > wip_limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Vượt quá giới hạn WIP Limit (§31): Số dự án đang chạy ({active_project_count}) vượt quá hạn mức tối đa của Founder ({wip_limit}). Vui lòng tạm dừng bớt dự án trước khi kích hoạt chu kỳ.",
            )

        cycle.status = "active"
        cycle.active_project_count = active_project_count
        self.db.commit()
        self.db.refresh(cycle)
        return self._serialize_cycle(cycle)

    # ------------------------------------------------------------------
    # Capacity & Founder Attention Allocations
    # ------------------------------------------------------------------

    def set_capacity_allocation(
        self,
        portfolio_cycle_id: int,
        project_id: int,
        allocated_percentage: float,
    ) -> Dict[str, Any]:
        get_project_scoped(self.db, project_id, self.workspace_id)
        alloc = (
            self.db.query(CapacityAllocation)
            .filter(
                CapacityAllocation.portfolio_cycle_id == portfolio_cycle_id,
                CapacityAllocation.project_id == project_id,
                CapacityAllocation.workspace_id == self.workspace_id,
            )
            .first()
        )
        if not alloc:
            alloc = CapacityAllocation(
                id=generate_snowflake_id(),
                workspace_id=self.workspace_id,
                portfolio_cycle_id=portfolio_cycle_id,
                project_id=project_id,
                allocated_percentage=allocated_percentage,
                created_at=datetime.utcnow(),
            )
            self.db.add(alloc)
        else:
            alloc.allocated_percentage = allocated_percentage

        self.db.commit()
        self.db.refresh(alloc)
        return {
            "id": str(alloc.id),
            "portfolio_cycle_id": str(alloc.portfolio_cycle_id),
            "project_id": str(alloc.project_id),
            "allocated_percentage": alloc.allocated_percentage,
        }

    def set_founder_attention_allocation(
        self,
        portfolio_cycle_id: int,
        project_id: int,
        allocated_hours_per_week: float,
    ) -> Dict[str, Any]:
        get_project_scoped(self.db, project_id, self.workspace_id)
        alloc = (
            self.db.query(FounderAttentionAllocation)
            .filter(
                FounderAttentionAllocation.portfolio_cycle_id == portfolio_cycle_id,
                FounderAttentionAllocation.project_id == project_id,
                FounderAttentionAllocation.workspace_id == self.workspace_id,
            )
            .first()
        )
        if not alloc:
            alloc = FounderAttentionAllocation(
                id=generate_snowflake_id(),
                workspace_id=self.workspace_id,
                portfolio_cycle_id=portfolio_cycle_id,
                project_id=project_id,
                allocated_hours_per_week=allocated_hours_per_week,
                created_at=datetime.utcnow(),
            )
            self.db.add(alloc)
        else:
            alloc.allocated_hours_per_week = allocated_hours_per_week

        self.db.commit()
        self.db.refresh(alloc)
        return {
            "id": str(alloc.id),
            "portfolio_cycle_id": str(alloc.portfolio_cycle_id),
            "project_id": str(alloc.project_id),
            "allocated_hours_per_week": alloc.allocated_hours_per_week,
        }

    def get_cycle_allocations(self, portfolio_cycle_id: int) -> Dict[str, Any]:
        cap_allocs = (
            self.db.query(CapacityAllocation)
            .filter(
                CapacityAllocation.portfolio_cycle_id == portfolio_cycle_id,
                CapacityAllocation.workspace_id == self.workspace_id,
            )
            .all()
        )
        attn_allocs = (
            self.db.query(FounderAttentionAllocation)
            .filter(
                FounderAttentionAllocation.portfolio_cycle_id == portfolio_cycle_id,
                FounderAttentionAllocation.workspace_id == self.workspace_id,
            )
            .all()
        )
        return {
            "capacity_allocations": [
                {
                    "id": str(c.id),
                    "project_id": str(c.project_id),
                    "allocated_percentage": c.allocated_percentage,
                }
                for c in cap_allocs
            ],
            "founder_attention_allocations": [
                {
                    "id": str(a.id),
                    "project_id": str(a.project_id),
                    "allocated_hours_per_week": a.allocated_hours_per_week,
                }
                for a in attn_allocs
            ],
        }

    # ------------------------------------------------------------------
    # Serializers
    # ------------------------------------------------------------------

    def _serialize_founder_profile(self, f: FounderProfile) -> Dict[str, Any]:
        return {
            "id": str(f.id),
            "user_id": str(f.user_id),
            "weekly_capacity_hours": f.weekly_capacity_hours,
            "max_active_strategic_projects": f.max_active_strategic_projects,
            "created_at": f.created_at.isoformat() if f.created_at else None,
            "updated_at": f.updated_at.isoformat() if f.updated_at else None,
        }

    def _serialize_cycle(self, c: PortfolioCycle) -> Dict[str, Any]:
        return {
            "id": str(c.id),
            "portfolio_id": str(c.portfolio_id),
            "title": c.title,
            "status": c.status,
            "start_date": c.start_date.isoformat() if c.start_date else None,
            "end_date": c.end_date.isoformat() if c.end_date else None,
            "active_project_count": c.active_project_count,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
