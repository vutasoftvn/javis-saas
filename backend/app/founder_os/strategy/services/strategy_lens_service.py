from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.founder_os.strategy.models import (
    PestelSignal, SwotItem, TowsOption, BscGoal, Hypothesis, Evidence, Project
)
from app.founder_os.strategy.schemas.lens_schemas import (
    PestelSignalCreate, SwotItemCreate, TowsOptionCreate, BscGoalCreate,
    TowsToTacticConvertRequest, SwotTypeEnum, StageLensSummaryResponse
)


class StrategyLensService:
    """Dịch vụ quản trị 4 Lăng kính Chiến lược (PESTEL, SWOT, TOWS, BSC) theo COSA Stage-Aware."""

    # --- 1. PESTEL Radar ---
    @staticmethod
    def create_pestel_signal(
        db: Session,
        workspace_id: int,
        payload: PestelSignalCreate,
    ) -> PestelSignal:
        project = db.query(Project).filter(Project.id == payload.project_id).first()
        current_stage = getattr(project, "project_stage", "S0_EXPLORE") if project else "S0_EXPLORE"

        signal = PestelSignal(
            workspace_id=workspace_id,
            project_id=payload.project_id,
            dimension=payload.dimension.value,
            signal_title=payload.signal_title,
            description=payload.description,
            impact_level=payload.impact_level,
            time_horizon=payload.time_horizon,
            stage_captured=str(current_stage),
        )
        db.add(signal)
        db.commit()
        db.refresh(signal)
        return signal

    @staticmethod
    def list_pestel_signals(
        db: Session,
        workspace_id: int,
        project_id: int,
    ) -> List[PestelSignal]:
        return (
            db.query(PestelSignal)
            .filter(
                PestelSignal.workspace_id == workspace_id,
                PestelSignal.project_id == project_id,
            )
            .order_by(PestelSignal.created_at.desc())
            .all()
        )

    @staticmethod
    def convert_pestel_to_hypothesis(
        db: Session,
        workspace_id: int,
        signal_id: int,
    ) -> Hypothesis:
        signal = db.query(PestelSignal).filter(PestelSignal.id == signal_id).first()
        if not signal or signal.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Không tìm thấy tín hiệu PESTEL.")

        category = "regulatory" if signal.dimension == "legal" else "market"
        importance = 0.9 if signal.impact_level == "high" else 0.6
        uncertainty = 0.8  # Tín hiệu vĩ mô ban đầu luôn có độ bất định cao

        hypo = Hypothesis(
            workspace_id=workspace_id,
            project_id=signal.project_id or 0,
            category=category,
            statement=f"Cơ hội/Rủi ro [{signal.dimension.upper()}]: {signal.signal_title} - {signal.description or ''}",
            importance=importance,
            uncertainty=uncertainty,
            risk_score=round(importance * uncertainty, 4),
            evidence_score=0.0,
            confidence=0.5,
            status="UNTESTED",
            stage_created=signal.stage_captured,
            evidence_refs=[],
            experiment_refs=[],
            next_action=f"Thu thập dữ liệu kiểm chứng cho tín hiệu {signal.dimension}",
        )
        db.add(hypo)
        db.flush()

        signal.resulting_hypothesis_id = hypo.id
        db.commit()
        db.refresh(hypo)
        return hypo

    # --- 2. Evidence-backed SWOT ---
    @staticmethod
    def create_swot_item(
        db: Session,
        workspace_id: int,
        payload: SwotItemCreate,
    ) -> SwotItem:
        # Kiểm tra quy tắc nghiêm ngặt: Strength & Weakness BẮT BUỘC có bằng chứng
        if payload.category in (SwotTypeEnum.STRENGTH, SwotTypeEnum.WEAKNESS):
            if not payload.evidence_refs or len(payload.evidence_refs) == 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Điểm {payload.category.value} bắt buộc phải có ít nhất 1 bằng chứng minh chứng (evidence_refs) từ dữ liệu thực tế.",
                )
            evidence_status = "verified"
        else:
            evidence_status = "verified" if payload.pestel_signal_ref else "unverified"

        item = SwotItem(
            workspace_id=workspace_id,
            project_id=payload.project_id,
            category=payload.category.value,
            statement=payload.statement,
            importance=payload.importance,
            evidence_status=evidence_status,
            evidence_refs=payload.evidence_refs or [],
            pestel_signal_ref=payload.pestel_signal_ref,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def list_swot_items(
        db: Session,
        workspace_id: int,
        project_id: int,
    ) -> List[SwotItem]:
        return (
            db.query(SwotItem)
            .filter(
                SwotItem.workspace_id == workspace_id,
                SwotItem.project_id == project_id,
            )
            .order_by(SwotItem.created_at.desc())
            .all()
        )

    # --- 3. TOWS Strategy Matrix & 12WY Tactics ---
    @staticmethod
    def create_tows_option(
        db: Session,
        workspace_id: int,
        payload: TowsOptionCreate,
    ) -> TowsOption:
        option = TowsOption(
            workspace_id=workspace_id,
            project_id=payload.project_id,
            quadrant=payload.quadrant.value,
            title=payload.title,
            tradeoffs=payload.strategy_description,
            expected_impact="high",
            confidence="medium",
            status="draft",
            linked_strength_ids=payload.linked_strength_ids or [],
            linked_weakness_ids=payload.linked_weakness_ids or [],
            linked_opportunity_ids=payload.linked_opportunity_ids or [],
            linked_threat_ids=payload.linked_threat_ids or [],
            tactics_12wy=[],
        )
        db.add(option)
        db.commit()
        db.refresh(option)
        return option

    @staticmethod
    def list_tows_options(
        db: Session,
        workspace_id: int,
        project_id: int,
    ) -> List[TowsOption]:
        return (
            db.query(TowsOption)
            .filter(
                TowsOption.workspace_id == workspace_id,
                TowsOption.project_id == project_id,
            )
            .order_by(TowsOption.created_at.desc())
            .all()
        )

    @staticmethod
    def convert_tows_to_tactics(
        db: Session,
        workspace_id: int,
        option_id: int,
        req: TowsToTacticConvertRequest,
    ) -> TowsOption:
        option = db.query(TowsOption).filter(TowsOption.id == option_id).first()
        if not option or option.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Không tìm thấy chiến lược TOWS.")

        # Tự động tạo Giả định cốt lõi nếu chưa có
        if not option.resulting_hypothesis_id and option.project_id:
            project = db.query(Project).filter(Project.id == option.project_id).first()
            current_stage = getattr(project, "project_stage", "S2_SOLUTION_VALIDATION") if project else "S2_SOLUTION_VALIDATION"

            hypo = Hypothesis(
                workspace_id=workspace_id,
                project_id=option.project_id,
                category="growth",
                statement=f"Chiến lược [{option.quadrant}]: {option.title} sẽ mang lại tăng trưởng theo kỳ vọng.",
                importance=0.85,
                uncertainty=0.7,
                risk_score=0.595,
                evidence_score=0.0,
                confidence=0.6,
                status="UNTESTED",
                stage_created=str(current_stage),
                evidence_refs=[],
                experiment_refs=[],
                next_action=f"Thực thi chiến thuật Tuần {req.week_number}: {req.tactic_title}",
            )
            db.add(hypo)
            db.flush()
            option.resulting_hypothesis_id = hypo.id

        # Thêm tactic vào danh sách 12WY
        current_tactics = list(option.tactics_12wy or [])
        current_tactics.append({
            "week_number": req.week_number,
            "title": req.tactic_title,
            "lead_indicator": req.lead_indicator,
            "owner_agent": req.owner_agent or "Strategy Agent",
            "status": "pending",
        })
        option.tactics_12wy = current_tactics
        option.status = "selected"

        db.commit()
        db.refresh(option)
        return option

    # --- 4. Balanced Scorecard (BSC Gatekeeper) ---
    @staticmethod
    def create_bsc_goal(
        db: Session,
        workspace_id: int,
        payload: BscGoalCreate,
    ) -> BscGoal:
        project = db.query(Project).filter(Project.id == payload.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Không tìm thấy dự án.")

        current_stage = str(getattr(project, "project_stage", "S1_PROBLEM_VALIDATION")).upper()
        # Khóa BSC nếu chưa đạt S5 (Operate & Grow) hoặc S6 (Scale & Govern)
        if "S5" not in current_stage and "S6" not in current_stage:
            raise HTTPException(
                status_code=400,
                detail=f"Balanced Scorecard (BSC) chỉ được mở khóa từ S5 (Operate & Grow) và S6 (Scale & Govern). Dự án hiện tại đang ở stage {current_stage}.",
            )

        goal = BscGoal(
            workspace_id=workspace_id,
            project_id=payload.project_id,
            perspective=payload.perspective.value,
            objective=payload.objective,
            kpi_name=payload.kpi_name,
            target_value=payload.target_value,
            current_value=payload.current_value,
            initiatives=payload.initiatives or [],
            status="on_track",
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)
        return goal

    @staticmethod
    def list_bsc_goals(
        db: Session,
        workspace_id: int,
        project_id: int,
    ) -> List[BscGoal]:
        return (
            db.query(BscGoal)
            .filter(
                BscGoal.workspace_id == workspace_id,
                BscGoal.project_id == project_id,
            )
            .order_by(BscGoal.created_at.desc())
            .all()
        )

    # --- 5. Stage Lens Summary ---
    @staticmethod
    def get_stage_lens_summary(
        db: Session,
        workspace_id: int,
        project_id: int,
    ) -> StageLensSummaryResponse:
        project = db.query(Project).filter(Project.id == project_id).first()
        current_stage = str(getattr(project, "project_stage", "S1_PROBLEM_VALIDATION")).upper()
        is_bsc_unlocked = ("S5" in current_stage or "S6" in current_stage)

        pestels = StrategyLensService.list_pestel_signals(db, workspace_id, project_id)
        swots = StrategyLensService.list_swot_items(db, workspace_id, project_id)
        tows = StrategyLensService.list_tows_options(db, workspace_id, project_id)
        bscs = StrategyLensService.list_bsc_goals(db, workspace_id, project_id) if is_bsc_unlocked else []

        from app.founder_os.strategy.schemas.lens_schemas import (
            PestelSignalResponse, SwotItemResponse, TowsOptionResponse, BscGoalResponse
        )

        return StageLensSummaryResponse(
            project_id=project_id,
            project_stage=current_stage,
            is_bsc_unlocked=is_bsc_unlocked,
            pestel_signals=[
                PestelSignalResponse(
                    id=p.id,
                    workspace_id=p.workspace_id,
                    project_id=p.project_id or project_id,
                    dimension=p.dimension,
                    signal_title=p.signal_title,
                    description=p.description or p.signal_summary or "",
                    impact_level=p.impact_level,
                    time_horizon=p.time_horizon,
                    resulting_hypothesis_id=p.resulting_hypothesis_id,
                    stage_captured=p.stage_captured,
                    created_at=p.created_at,
                )
                for p in pestels
            ],
            swot_items=[SwotItemResponse.model_validate(s) for s in swots],
            tows_options=[TowsOptionResponse.model_validate(t) for t in tows],
            bsc_goals=[BscGoalResponse.model_validate(b) for b in bscs],
        )

    # Aliases for sync router handlers
    create_pestel_signal_sync = create_pestel_signal
    list_pestel_signals_sync = list_pestel_signals
    convert_pestel_to_hypothesis_sync = convert_pestel_to_hypothesis
    create_swot_item_sync = create_swot_item
    list_swot_items_sync = list_swot_items
    create_tows_option_sync = create_tows_option
    list_tows_options_sync = list_tows_options
    convert_tows_to_tactics_sync = convert_tows_to_tactics
    create_bsc_goal_sync = create_bsc_goal
    list_bsc_goals_sync = list_bsc_goals
    get_stage_lens_summary_sync = get_stage_lens_summary
