from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException

from founder_os.strategy.models import (
    Project,
    TwelveWeekCycle,
    TacticalExecutionItem,
    WeeklyAccountabilityReview,
    TowsOption,
    Hypothesis,
)
from founder_os.strategy.schemas.twelve_wy_schemas import (
    TacticalItemCreate,
    TacticalItemUpdate,
    TwelveWeekCycleCreate,
)


class TwelveWyService:
    """Động cơ Vòng Lặp Thực Thi Chiến Lược 12 Tuần & Chỉ Số Dẫn Dắt (12WY Service)."""

    @staticmethod
    def get_or_create_active_cycle(
        db: Session,
        workspace_id: int,
        project_id: int,
        title: Optional[str] = None,
    ) -> TwelveWeekCycle:
        cycle = (
            db.query(TwelveWeekCycle)
            .filter(
                TwelveWeekCycle.workspace_id == workspace_id,
                TwelveWeekCycle.project_id == project_id,
                TwelveWeekCycle.status == "ACTIVE",
            )
            .first()
        )
        if not cycle:
            project = db.query(Project).filter(Project.id == project_id).first()
            p_stage = str(getattr(project, "project_stage", "S1_PROBLEM_VALIDATION")).upper() if project else "S1_PROBLEM_VALIDATION"
            p_title = project.title if project else f"Dự án {project_id}"

            start_dt = datetime.utcnow()
            end_dt = start_dt + timedelta(days=84) # 12 tuần = 84 ngày

            brain_id = getattr(project, 'brain_id', None) or 3001
            cycle = TwelveWeekCycle(
                workspace_id=workspace_id,
                brain_id=brain_id,
                project_id=project_id,
                theme=title or f"Chu Kỳ 12 Tuần: {p_title}",
                vision_statement=f"Tập trung kiểm chứng và đạt bước ngoặt tại {p_stage}.",
                stage_at_start=p_stage,
                current_week=1,
                duration_weeks=12,
                status="ACTIVE",
                overall_execution_score=0.0,
                start_date=start_dt,
                end_date=end_dt,
            )
            db.add(cycle)
            db.commit()
            db.refresh(cycle)

        return cycle

    @staticmethod
    def create_tactic(
        db: Session,
        workspace_id: int,
        payload: TacticalItemCreate,
    ) -> TacticalExecutionItem:
        cycle = (
            db.query(TwelveWeekCycle).filter(TwelveWeekCycle.id == payload.cycle_id).first()
            if payload.cycle_id
            else TwelveWyService.get_or_create_active_cycle(db, workspace_id, payload.project_id)
        )
        if not cycle or cycle.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Không tìm thấy chu kỳ 12 tuần.")

        status = payload.status or "PLANNED"
        completed_at = None
        if payload.actual_count >= payload.target_count or status == "DONE":
            status = "DONE"
            completed_at = datetime.utcnow()

        tactic = TacticalExecutionItem(
            workspace_id=workspace_id,
            project_id=payload.project_id,
            cycle_id=cycle.id,
            week_number=payload.week_number,
            title=payload.title,
            description=payload.description or "",
            tows_option_id=payload.tows_option_id,
            hypothesis_id=payload.hypothesis_id,
            lead_indicator_name=payload.lead_indicator_name,
            target_count=payload.target_count,
            actual_count=payload.actual_count,
            status=status,
            owner_role=payload.owner_role or "Founder",
            completed_at=completed_at,
        )
        db.add(tactic)
        db.commit()
        db.refresh(tactic)

        TwelveWyService._recalculate_cycle_score(db, cycle.id)
        return tactic

    @staticmethod
    def update_tactic(
        db: Session,
        workspace_id: int,
        tactic_id: int,
        payload: TacticalItemUpdate,
    ) -> TacticalExecutionItem:
        tactic = db.query(TacticalExecutionItem).filter(TacticalExecutionItem.id == tactic_id).first()
        if not tactic or tactic.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Không tìm thấy hành động chiến thuật.")

        if payload.title is not None:
            tactic.title = payload.title
        if payload.description is not None:
            tactic.description = payload.description
        if payload.actual_count is not None:
            tactic.actual_count = payload.actual_count
            if tactic.actual_count >= tactic.target_count:
                tactic.status = "DONE"
                if not tactic.completed_at:
                    tactic.completed_at = datetime.utcnow()

        if payload.status is not None:
            tactic.status = payload.status
            if payload.status == "DONE" and not tactic.completed_at:
                tactic.completed_at = datetime.utcnow()
            elif payload.status != "DONE":
                tactic.completed_at = None

        db.commit()
        db.refresh(tactic)

        TwelveWyService._recalculate_cycle_score(db, tactic.cycle_id)
        return tactic

    @staticmethod
    def calculate_week_score(db: Session, cycle_id: int, week_number: int) -> float:
        tactics = (
            db.query(TacticalExecutionItem)
            .filter(
                TacticalExecutionItem.cycle_id == cycle_id,
                TacticalExecutionItem.week_number == week_number,
            )
            .all()
        )
        if not tactics:
            return 0.0

        done_count = sum(1 for t in tactics if t.status == "DONE")
        return round((done_count / len(tactics)) * 100.0, 1)

    @staticmethod
    def generate_weekly_review(
        db: Session,
        workspace_id: int,
        cycle_id: int,
        week_number: int,
    ) -> WeeklyAccountabilityReview:
        cycle = db.query(TwelveWeekCycle).filter(TwelveWeekCycle.id == cycle_id).first()
        if not cycle or cycle.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Không tìm thấy chu kỳ 12 tuần.")

        tactics = (
            db.query(TacticalExecutionItem)
            .filter(
                TacticalExecutionItem.cycle_id == cycle_id,
                TacticalExecutionItem.week_number == week_number,
            )
            .all()
        )
        total_planned = len(tactics)
        completed_tactics = [t for t in tactics if t.status == "DONE"]
        total_completed = len(completed_tactics)

        score = round((total_completed / total_planned) * 100.0, 1) if total_planned > 0 else 0.0

        breakthroughs = [
            f"Hoàn thành xuất sắc: {t.title} ({t.actual_count}/{t.target_count} {t.lead_indicator_name})"
            for t in completed_tactics
        ]
        blocks = [
            f"Chưa đạt chỉ số: {t.title} ({t.actual_count}/{t.target_count} {t.lead_indicator_name})"
            for t in tactics if t.status != "DONE"
        ]

        if score >= 85.0:
            recs = [
                "Vận tốc thực thi Xuất Sắc (>=85%). Giữ vững nhịp độ kỷ luật cho tuần tiếp theo.",
                "Chuyển đổi các phát hiện thực tế thành bằng chứng củng cố Giả định cốt lõi.",
            ]
        elif score >= 60.0:
            recs = [
                "Vận tốc thực thi Khá (60-84%). Cần tập trung giải quyết các điểm nghẽn lead indicators.",
                "Ủy quyền bớt các công việc phụ để dồn toàn lực vào 1-2 tactics quan trọng nhất.",
            ]
        else:
            recs = [
                "Cảnh báo: Vận tốc thực thi Dưới Chuẩn (<60%). Có nguy cơ trễ mục tiêu quý.",
                "Khuyến nghị họp WAM khẩn cấp với AI Strategic Copilot để tinh gọn khối lượng công việc.",
            ]

        review = WeeklyAccountabilityReview(
            workspace_id=workspace_id,
            project_id=cycle.project_id,
            cycle_id=cycle.id,
            week_number=week_number,
            execution_score=score,
            total_planned=total_planned,
            total_completed=total_completed,
            key_breakthroughs=breakthroughs,
            root_cause_blocks=blocks,
            ai_recommendations=recs,
        )
        db.add(review)
        db.commit()
        db.refresh(review)
        return review

    @staticmethod
    def get_cycle_dashboard(
        db: Session,
        workspace_id: int,
        project_id: int,
    ) -> Dict[str, Any]:
        cycle = TwelveWyService.get_or_create_active_cycle(db, workspace_id, project_id)

        tactics = (
            db.query(TacticalExecutionItem)
            .filter(TacticalExecutionItem.cycle_id == cycle.id)
            .order_by(TacticalExecutionItem.week_number.asc(), TacticalExecutionItem.created_at.asc())
            .all()
        )

        tactics_by_week: Dict[int, List[TacticalExecutionItem]] = {w: [] for w in range(1, 13)}
        weekly_scores: Dict[int, float] = {}

        for t in tactics:
            tactics_by_week[t.week_number].append(t)

        for w in range(1, 13):
            w_tactics = tactics_by_week[w]
            if w_tactics:
                done = sum(1 for t in w_tactics if t.status == "DONE")
                weekly_scores[w] = round((done / len(w_tactics)) * 100.0, 1)
            else:
                weekly_scores[w] = 0.0

        current_score = weekly_scores.get(cycle.current_week, 0.0)

        latest_review = (
            db.query(WeeklyAccountabilityReview)
            .filter(WeeklyAccountabilityReview.cycle_id == cycle.id)
            .order_by(WeeklyAccountabilityReview.week_number.desc(), WeeklyAccountabilityReview.created_at.desc())
            .first()
        )

        return {
            "cycle": cycle,
            "current_week": cycle.current_week,
            "current_week_execution_score": current_score,
            "tactics_by_week": tactics_by_week,
            "weekly_scores": weekly_scores,
            "latest_review": latest_review,
        }

    @staticmethod
    def _recalculate_cycle_score(db: Session, cycle_id: int):
        tactics = db.query(TacticalExecutionItem).filter(TacticalExecutionItem.cycle_id == cycle_id).all()
        if not tactics:
            return

        done = sum(1 for t in tactics if t.status == "DONE")
        avg_score = round((done / len(tactics)) * 100.0, 1)

        cycle = db.query(TwelveWeekCycle).filter(TwelveWeekCycle.id == cycle_id).first()
        if cycle:
            cycle.overall_execution_score = avg_score
            db.commit()
