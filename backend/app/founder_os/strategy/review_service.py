import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.core.tenancy import get_cycle_scoped

from app.founder_os.strategy.models import (
    TwelveWeekCycle,
    WeeklyPlan,
    WeeklyReview,
    CycleReview,
    CelebrationRecord,
    Milestone,
)
from app.workforce.ai_team.service import get_function_statuses
from app.business.finance.models import FinanceManagementSnapshot
from app.business.learning.models import Lesson

logger = logging.getLogger(__name__)

VALID_RECOMMENDATIONS = {
    "CONTINUE",
    "PIVOT_NEXT_WEEK",
    "DOUBLE_DOWN",
    "RECALIBRATE_CAPACITY",
}


class ReviewAndTransitionService:
    """Review & Week 13 Strategic Transition Engine (mCOSA V12 Spec §17–19, §62.10 & Sprint 5).

    Hỗ trợ thực hiện đánh giá tuần (Weekly Review), lưu vết giả định, bằng chứng thực tế,
    và tổng kết chu kỳ tuần 13 (Strategic Transition, Retrospective & Celebration).
    """

    def __init__(self, db: Session, workspace_id: int, user_id: int):
        self.db = db
        self.workspace_id = workspace_id
        self.user_id = user_id

    # ------------------------------------------------------------------
    # Weekly Reviews (Spec §17)
    # ------------------------------------------------------------------

    def create_or_update_weekly_review(
        self,
        cycle_id: int,
        weekly_plan_id: int,
        execution_score: float,
        outcome_score: float,
        evidence_learned: Optional[str] = None,
        assumptions_confirmed: Optional[Dict[str, Any]] = None,
        assumptions_invalidated: Optional[Dict[str, Any]] = None,
        recommendation: str = "CONTINUE",
        narrative_summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        get_cycle_scoped(self.db, cycle_id, self.workspace_id)

        plan = (
            self.db.query(WeeklyPlan)
            .filter(
                WeeklyPlan.id == weekly_plan_id,
                WeeklyPlan.cycle_id == cycle_id,
                WeeklyPlan.workspace_id == self.workspace_id,
            )
            .first()
        )
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WeeklyPlan not found")

        rec_upper = recommendation.upper()
        if rec_upper not in VALID_RECOMMENDATIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Khuyến nghị không hợp lệ. Phải thuộc: {VALID_RECOMMENDATIONS}",
            )

        review = (
            self.db.query(WeeklyReview)
            .filter(
                WeeklyReview.weekly_plan_id == weekly_plan_id,
                WeeklyReview.workspace_id == self.workspace_id,
            )
            .first()
        )

        now = datetime.utcnow()
        if review:
            review.execution_score = execution_score
            review.outcome_score = outcome_score
            review.evidence_learned = evidence_learned
            review.assumptions_confirmed = assumptions_confirmed or {}
            review.assumptions_invalidated = assumptions_invalidated or {}
            review.recommendation = rec_upper
            review.narrative_summary = narrative_summary
            review.reviewed_by = self.user_id
            review.reviewed_at = now
        else:
            review = WeeklyReview(
                id=generate_snowflake_id(),
                workspace_id=self.workspace_id,
                cycle_id=cycle_id,
                weekly_plan_id=weekly_plan_id,
                week_no=plan.week_no,
                execution_score=execution_score,
                outcome_score=outcome_score,
                evidence_learned=evidence_learned,
                assumptions_confirmed=assumptions_confirmed or {},
                assumptions_invalidated=assumptions_invalidated or {},
                recommendation=rec_upper,
                narrative_summary=narrative_summary,
                reviewed_by=self.user_id,
                reviewed_at=now,
                created_at=now,
            )
            self.db.add(review)

        # Sync outcome_score and execution_score back to weekly_plan
        plan.outcome_score = outcome_score
        plan.execution_score = execution_score

        self.db.commit()
        self.db.refresh(review)
        return self._serialize_weekly_review(review)

    def get_weekly_review(self, weekly_plan_id: int) -> Optional[Dict[str, Any]]:
        review = (
            self.db.query(WeeklyReview)
            .filter(
                WeeklyReview.weekly_plan_id == weekly_plan_id,
                WeeklyReview.workspace_id == self.workspace_id,
            )
            .first()
        )
        if not review:
            return None
        return self._serialize_weekly_review(review)

    def list_weekly_reviews(self, cycle_id: int) -> List[Dict[str, Any]]:
        get_cycle_scoped(self.db, cycle_id, self.workspace_id)
        reviews = (
            self.db.query(WeeklyReview)
            .filter(
                WeeklyReview.cycle_id == cycle_id,
                WeeklyReview.workspace_id == self.workspace_id,
            )
            .order_by(WeeklyReview.week_no.asc())
            .all()
        )
        return [self._serialize_weekly_review(r) for r in reviews]

    # ------------------------------------------------------------------
    # Week 13 Strategic Transition & Celebration (Spec §18–19, §62.10)
    # ------------------------------------------------------------------

    def finalize_week13(
        self,
        cycle_id: int,
        overall_execution_score: float,
        overall_outcome_score: float,
        okr_achievement_rate: float,
        strategic_learnings: Optional[str] = None,
        systemic_blockers: Optional[str] = None,
        portfolio_adjustments: Optional[Dict[str, Any]] = None,
        next_cycle_recommendations: Optional[str] = None,
        celebration_title: Optional[str] = None,
        milestones_achieved: Optional[Dict[str, Any]] = None,
        top_performers_recognized: Optional[Dict[str, Any]] = None,
        rewards_or_rituals: Optional[str] = None,
        reflection_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        cycle = get_cycle_scoped(self.db, cycle_id, self.workspace_id)

        now = datetime.utcnow()

        # 1. Upsert CycleReview
        cycle_review = (
            self.db.query(CycleReview)
            .filter(
                CycleReview.cycle_id == cycle_id,
                CycleReview.workspace_id == self.workspace_id,
            )
            .first()
        )
        if cycle_review:
            cycle_review.overall_execution_score = overall_execution_score
            cycle_review.overall_outcome_score = overall_outcome_score
            cycle_review.okr_achievement_rate = okr_achievement_rate
            cycle_review.strategic_learnings = strategic_learnings
            cycle_review.systemic_blockers = systemic_blockers
            cycle_review.portfolio_adjustments = portfolio_adjustments or {}
            cycle_review.next_cycle_recommendations = next_cycle_recommendations
            cycle_review.status = "finalized"
            cycle_review.reviewed_by = self.user_id
            cycle_review.reviewed_at = now
        else:
            cycle_review = CycleReview(
                id=generate_snowflake_id(),
                workspace_id=self.workspace_id,
                cycle_id=cycle_id,
                overall_execution_score=overall_execution_score,
                overall_outcome_score=overall_outcome_score,
                okr_achievement_rate=okr_achievement_rate,
                strategic_learnings=strategic_learnings,
                systemic_blockers=systemic_blockers,
                portfolio_adjustments=portfolio_adjustments or {},
                next_cycle_recommendations=next_cycle_recommendations,
                status="finalized",
                reviewed_by=self.user_id,
                reviewed_at=now,
                created_at=now,
            )
            self.db.add(cycle_review)

        # 2. Upsert CelebrationRecord
        celebration = (
            self.db.query(CelebrationRecord)
            .filter(
                CelebrationRecord.cycle_id == cycle_id,
                CelebrationRecord.workspace_id == self.workspace_id,
            )
            .first()
        )
        celeb_title = celebration_title or f"Lễ Tôn Vinh Chu Kỳ: {cycle.theme}"
        if celebration:
            celebration.title = celeb_title
            celebration.milestones_achieved = milestones_achieved or {}
            celebration.top_performers_recognized = top_performers_recognized or {}
            celebration.rewards_or_rituals = rewards_or_rituals
            celebration.reflection_notes = reflection_notes
            celebration.celebrated_at = now
        else:
            celebration = CelebrationRecord(
                id=generate_snowflake_id(),
                workspace_id=self.workspace_id,
                cycle_id=cycle_id,
                title=celeb_title,
                milestones_achieved=milestones_achieved or {},
                top_performers_recognized=top_performers_recognized or {},
                rewards_or_rituals=rewards_or_rituals,
                reflection_notes=reflection_notes,
                created_by=self.user_id,
                celebrated_at=now,
                created_at=now,
            )
            self.db.add(celebration)

        # 3. Mark Cycle status as completed/transitioned
        cycle.status = "completed"

        self.db.commit()
        self.db.refresh(cycle_review)
        self.db.refresh(celebration)

        return {
            "cycle_id": str(cycle_id),
            "cycle_review": self._serialize_cycle_review(cycle_review),
            "celebration": self._serialize_celebration(celebration),
        }

    def get_cycle_review(self, cycle_id: int) -> Optional[Dict[str, Any]]:
        get_cycle_scoped(self.db, cycle_id, self.workspace_id)
        cr = (
            self.db.query(CycleReview)
            .filter(
                CycleReview.cycle_id == cycle_id,
                CycleReview.workspace_id == self.workspace_id,
            )
            .first()
        )
        if not cr:
            return None
        return self._serialize_cycle_review(cr)

    def get_celebration_record(self, cycle_id: int) -> Optional[Dict[str, Any]]:
        get_cycle_scoped(self.db, cycle_id, self.workspace_id)
        celeb = (
            self.db.query(CelebrationRecord)
            .filter(
                CelebrationRecord.cycle_id == cycle_id,
                CelebrationRecord.workspace_id == self.workspace_id,
            )
            .first()
        )
        if not celeb:
            return None
        return self._serialize_celebration(celeb)

    def validate_week13_transition_readiness(self, cycle_id: int) -> Dict[str, Any]:
        """Audit test check: 'Week 13 mandatory unless explicitly overridden' (§62.10)."""
        cycle = get_cycle_scoped(self.db, cycle_id, self.workspace_id)
        plans = (
            self.db.query(WeeklyPlan)
            .filter(
                WeeklyPlan.cycle_id == cycle_id,
                WeeklyPlan.workspace_id == self.workspace_id,
            )
            .all()
        )
        plan_ids = [p.id for p in plans]
        reviews = (
            self.db.query(WeeklyReview)
            .filter(
                WeeklyReview.weekly_plan_id.in_(plan_ids),
                WeeklyReview.workspace_id == self.workspace_id,
            )
            .all()
            if plan_ids
            else []
        )
        milestones = (
            self.db.query(Milestone)
            .filter(
                Milestone.cycle_id == cycle_id,
                Milestone.workspace_id == self.workspace_id,
            )
            .all()
        )

        completed_milestones = [m for m in milestones if m.status in ("completed", "done", "passed")]
        reviews_count = len(reviews)
        total_weeks = len(plans)

        ready_for_week13 = reviews_count >= max(1, total_weeks - 2)

        return {
            "cycle_id": str(cycle_id),
            "theme": cycle.theme,
            "total_weeks": total_weeks,
            "completed_weekly_reviews": reviews_count,
            "total_milestones": len(milestones),
            "completed_milestones": len(completed_milestones),
            "ready_for_week13": ready_for_week13,
            "week13_mandatory": True,
            "message": "Chu kỳ đủ điều kiện thực hiện chuyển dịch chiến lược Tuần 13." if ready_for_week13 else "Cần hoàn tất thêm các bản đánh giá tuần trước khi chuyển dịch sang Tuần 13.",
        }

    # ------------------------------------------------------------------
    # Serializers
    # ------------------------------------------------------------------

    def _v13_composition(self, cycle_id: int, week_no: Optional[int] = None) -> Dict[str, Any]:
        lesson_query = self.db.query(Lesson).filter(
            Lesson.workspace_id == self.workspace_id,
            Lesson.cycle_id == cycle_id,
        )
        if week_no is not None:
            lesson_query = lesson_query.filter(Lesson.week_no == week_no)
        lessons = lesson_query.order_by(Lesson.created_at.desc()).all()
        snapshot = (
            self.db.query(FinanceManagementSnapshot)
            .filter(
                FinanceManagementSnapshot.workspace_id == self.workspace_id,
                FinanceManagementSnapshot.cycle_id == cycle_id,
            )
            .order_by(FinanceManagementSnapshot.as_of.desc())
            .first()
        )
        return {
            "function_results": get_function_statuses(self.db, self.workspace_id),
            "lessons": [
                {
                    "id": str(lesson.id),
                    "function": lesson.function,
                    "observation": lesson.observation,
                    "recommendation": lesson.recommendation,
                    "status": lesson.status,
                }
                for lesson in lessons
            ],
            "finance_status": None if snapshot is None else {
                "as_of": snapshot.as_of.isoformat(),
                "cash": str(snapshot.cash),
                "burn": str(snapshot.burn),
                "runway_months": str(snapshot.runway_months) if snapshot.runway_months is not None else None,
            },
        }

    def _serialize_weekly_review(self, r: WeeklyReview) -> Dict[str, Any]:
        result = {
            "id": str(r.id),
            "cycle_id": str(r.cycle_id),
            "weekly_plan_id": str(r.weekly_plan_id),
            "week_no": r.week_no,
            "execution_score": r.execution_score,
            "outcome_score": r.outcome_score,
            "evidence_learned": r.evidence_learned,
            "assumptions_confirmed": r.assumptions_confirmed or {},
            "assumptions_invalidated": r.assumptions_invalidated or {},
            "recommendation": r.recommendation,
            "narrative_summary": r.narrative_summary,
            "reviewed_by": str(r.reviewed_by),
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        result.update(self._v13_composition(r.cycle_id, r.week_no))
        return result

    def _serialize_cycle_review(self, cr: CycleReview) -> Dict[str, Any]:
        result = {
            "id": str(cr.id),
            "cycle_id": str(cr.cycle_id),
            "overall_execution_score": cr.overall_execution_score,
            "overall_outcome_score": cr.overall_outcome_score,
            "okr_achievement_rate": cr.okr_achievement_rate,
            "strategic_learnings": cr.strategic_learnings,
            "systemic_blockers": cr.systemic_blockers,
            "portfolio_adjustments": cr.portfolio_adjustments or {},
            "next_cycle_recommendations": cr.next_cycle_recommendations,
            "status": cr.status,
            "reviewed_by": str(cr.reviewed_by),
            "reviewed_at": cr.reviewed_at.isoformat() if cr.reviewed_at else None,
            "created_at": cr.created_at.isoformat() if cr.created_at else None,
        }
        result.update(self._v13_composition(cr.cycle_id))
        return result

    def _serialize_celebration(self, c: CelebrationRecord) -> Dict[str, Any]:
        result = {
            "id": str(c.id),
            "cycle_id": str(c.cycle_id),
            "title": c.title,
            "milestones_achieved": c.milestones_achieved or {},
            "top_performers_recognized": c.top_performers_recognized or {},
            "rewards_or_rituals": c.rewards_or_rituals,
            "reflection_notes": c.reflection_notes,
            "created_by": str(c.created_by),
            "celebrated_at": c.celebrated_at.isoformat() if c.celebrated_at else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        result.update(self._v13_composition(c.cycle_id))
        return result
