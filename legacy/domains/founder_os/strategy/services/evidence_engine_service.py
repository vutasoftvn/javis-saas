import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from founder_os.strategy.models import Hypothesis, Evidence, Project
from founder_os.strategy.schemas.evidence_schemas import (
    HypothesisCreate,
    HypothesisUpdate,
    HypothesisResponse,
    EvidenceCreate,
    EvidenceUpdate,
    EvidenceResponse,
    AssumptionMatrixResponse,
    AssumptionMatrixQuadrant,
    HypothesisStatusEnum,
)

logger = logging.getLogger(__name__)


LADDER_WEIGHTS: Dict[str, float] = {
    "E0_OPINION": 0.0,
    "E1_STATED_INTEREST": 0.2,
    "E2_OBSERVED_PROBLEM": 0.4,
    "E3_BEHAVIORAL_COMMITMENT": 0.7,
    "E4_ECONOMIC_COMMITMENT": 0.9,
    "E5_REPEAT_BEHAVIOR": 0.95,
    "E6_SCALABLE_EVIDENCE": 1.0,
}

STRENGTH_MULTIPLIERS: Dict[str, float] = {
    "weak": 0.6,
    "medium": 1.0,
    "strong": 1.3,
}

DIRECTION_SIGNS: Dict[str, float] = {
    "supports": 1.0,
    "contradicts": -1.2,  # Bằng chứng phủ định có sức nặng cảnh báo cao hơn
    "neutral": 0.0,
}


class EvidenceEngineService:
    """COSA Assumption & Evidence Engine.
    
    Quản lý vòng đời Giả định (Hypothesis), Bằng chứng (Evidence) theo Thang đo Evidence Ladder (E0 -> E6)
    và Ma trận Rủi ro Giả định (Assumption Risk Matrix).
    """

    def __init__(self, db: Session, workspace_id: int, user_id: Optional[int] = None):
        self.db = db
        self.workspace_id = workspace_id
        self.user_id = user_id

    # --- Hypothesis Management ---

    def create_hypothesis(self, payload: HypothesisCreate) -> HypothesisResponse:
        """Tạo Giả định mới cho Project."""
        project = self.db.query(Project).filter(
            Project.id == payload.project_id,
            Project.workspace_id == self.workspace_id
        ).first()
        stage_created = getattr(project, "project_stage", "S1_PROBLEM_VALIDATION") if project else "S1_PROBLEM_VALIDATION"

        risk_score = round(payload.importance * payload.uncertainty, 4)

        hypo = Hypothesis(
            workspace_id=self.workspace_id,
            project_id=payload.project_id,
            category=payload.category.value,
            statement=payload.statement,
            importance=payload.importance,
            uncertainty=payload.uncertainty,
            risk_score=risk_score,
            evidence_score=0.0,
            confidence=0.0,
            status=HypothesisStatusEnum.UNTESTED.value,
            stage_created=stage_created,
            evidence_refs=[],
            experiment_refs=[],
            next_action=payload.next_action,
        )
        self.db.add(hypo)
        self.db.commit()
        self.db.refresh(hypo)
        return self._serialize_hypothesis(hypo)

    def update_hypothesis(self, hypothesis_id: int, payload: HypothesisUpdate) -> Optional[HypothesisResponse]:
        """Cập nhật thông tin Giả định."""
        hypo = self.db.query(Hypothesis).filter(
            Hypothesis.id == hypothesis_id,
            Hypothesis.workspace_id == self.workspace_id
        ).first()
        if not hypo:
            return None

        if payload.category is not None:
            hypo.category = payload.category.value
        if payload.statement is not None:
            hypo.statement = payload.statement
        if payload.importance is not None:
            hypo.importance = payload.importance
        if payload.uncertainty is not None:
            hypo.uncertainty = payload.uncertainty
        if payload.importance is not None or payload.uncertainty is not None:
            hypo.risk_score = round(hypo.importance * hypo.uncertainty, 4)
        if payload.status is not None:
            hypo.status = payload.status.value
        if payload.next_action is not None:
            hypo.next_action = payload.next_action

        self.db.commit()
        self.db.refresh(hypo)
        return self._serialize_hypothesis(hypo)

    def list_hypotheses(
        self,
        project_id: Optional[int] = None,
        category: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[HypothesisResponse]:
        """Danh sách Giả định kèm bộ lọc."""
        query = self.db.query(Hypothesis).filter(Hypothesis.workspace_id == self.workspace_id)
        if project_id:
            query = query.filter(Hypothesis.project_id == project_id)
        if category:
            query = query.filter(Hypothesis.category == category)
        if status:
            query = query.filter(Hypothesis.status == status)

        hypos = query.order_by(desc(Hypothesis.risk_score), desc(Hypothesis.created_at)).all()
        return [self._serialize_hypothesis(h) for h in hypos]

    def delete_hypothesis(self, hypothesis_id: int) -> bool:
        """Xóa Giả định."""
        hypo = self.db.query(Hypothesis).filter(
            Hypothesis.id == hypothesis_id,
            Hypothesis.workspace_id == self.workspace_id
        ).first()
        if not hypo:
            return False
        self.db.delete(hypo)
        self.db.commit()
        return True

    # --- Evidence Management & Evidence Ladder Engine ---

    def create_evidence(self, payload: EvidenceCreate) -> EvidenceResponse:
        """Ghi nhận Bằng chứng thực tế mới và tự động tái tính điểm Giả định."""
        ev = Evidence(
            workspace_id=self.workspace_id,
            project_id=payload.project_id,
            type=payload.type.value,
            ladder_level=payload.ladder_level.value,
            source=payload.source,
            claim_supported=payload.claim_supported,
            strength=payload.strength.value,
            direction=payload.direction.value,
            hypothesis_refs=payload.hypothesis_refs,
            artifact_refs=payload.artifact_refs,
            raw_payload=payload.raw_payload,
        )
        self.db.add(ev)
        self.db.commit()
        self.db.refresh(ev)

        # Cập nhật danh sách evidence_refs trong các Hypothesis liên quan & tính lại điểm
        for hyp_id in payload.hypothesis_refs:
            hypo = self.db.query(Hypothesis).filter(
                Hypothesis.id == hyp_id,
                Hypothesis.workspace_id == self.workspace_id
            ).first()
            if hypo:
                current_refs = list(hypo.evidence_refs or [])
                if ev.id not in current_refs:
                    current_refs.append(ev.id)
                    hypo.evidence_refs = current_refs
                    self.db.commit()
                self.recalculate_hypothesis_evidence(hyp_id)

        return self._serialize_evidence(ev)

    def list_evidences(
        self,
        project_id: Optional[int] = None,
        ladder_level: Optional[str] = None,
        type: Optional[str] = None
    ) -> List[EvidenceResponse]:
        """Danh sách Bằng chứng kèm bộ lọc."""
        query = self.db.query(Evidence).filter(Evidence.workspace_id == self.workspace_id)
        if project_id:
            query = query.filter(Evidence.project_id == project_id)
        if ladder_level:
            query = query.filter(Evidence.ladder_level == ladder_level)
        if type:
            query = query.filter(Evidence.type == type)

        evs = query.order_by(desc(Evidence.captured_at)).all()
        return [self._serialize_evidence(e) for e in evs]

    def delete_evidence(self, evidence_id: int) -> bool:
        """Xóa Bằng chứng và tái tính điểm Giả định."""
        ev = self.db.query(Evidence).filter(
            Evidence.id == evidence_id,
            Evidence.workspace_id == self.workspace_id
        ).first()
        if not ev:
            return False

        affected_hypos = list(ev.hypothesis_refs or [])
        self.db.delete(ev)
        self.db.commit()

        for hyp_id in affected_hypos:
            hypo = self.db.query(Hypothesis).filter(
                Hypothesis.id == hyp_id,
                Hypothesis.workspace_id == self.workspace_id
            ).first()
            if hypo:
                current_refs = list(hypo.evidence_refs or [])
                if evidence_id in current_refs:
                    current_refs.remove(evidence_id)
                    hypo.evidence_refs = current_refs
                    self.db.commit()
            self.recalculate_hypothesis_evidence(hyp_id)

        return True

    def recalculate_hypothesis_evidence(self, hypothesis_id: int) -> None:
        """Thuật toán cốt lõi tính toán điểm tin cậy và tự động chuyển trạng thái Giả định."""
        hypo = self.db.query(Hypothesis).filter(
            Hypothesis.id == hypothesis_id,
            Hypothesis.workspace_id == self.workspace_id
        ).first()
        if not hypo:
            return

        evidence_ids = list(hypo.evidence_refs or [])
        if not evidence_ids:
            hypo.evidence_score = 0.0
            hypo.confidence = 0.0
            hypo.status = HypothesisStatusEnum.UNTESTED.value
            self.db.commit()
            return

        evidences = self.db.query(Evidence).filter(
            Evidence.id.in_(evidence_ids),
            Evidence.workspace_id == self.workspace_id
        ).all()

        if not evidences:
            hypo.evidence_score = 0.0
            hypo.confidence = 0.0
            hypo.status = HypothesisStatusEnum.UNTESTED.value
            self.db.commit()
            return

        raw_score = 0.0
        has_high_ladder_proof = False
        has_strong_contradiction = False

        for ev in evidences:
            weight = LADDER_WEIGHTS.get(ev.ladder_level, 0.2)
            multiplier = STRENGTH_MULTIPLIERS.get(ev.strength, 1.0)
            sign = DIRECTION_SIGNS.get(ev.direction, 0.0)

            contribution = weight * multiplier * sign
            raw_score += contribution

            # Kiểm tra xem có bằng chứng cấp E3 trở lên ủng hộ không
            if sign > 0 and ev.ladder_level in ["E3_BEHAVIORAL_COMMITMENT", "E4_ECONOMIC_COMMITMENT", "E5_REPEAT_BEHAVIOR", "E6_SCALABLE_EVIDENCE"]:
                has_high_ladder_proof = True

            # Kiểm tra xem có bằng chứng phủ định mạnh không
            if sign < 0 and ev.strength == "strong":
                has_strong_contradiction = True

        # Chuẩn hóa điểm về khoảng [0.0, 1.0]
        evidence_score = max(0.0, min(1.0, round(raw_score, 4)))
        confidence = round(min(1.0, len(evidences) * 0.25) * evidence_score, 4)

        hypo.evidence_score = evidence_score
        hypo.confidence = confidence

        # Tự động chuyển trạng thái (State Machine)
        if raw_score < -0.3 or (has_strong_contradiction and evidence_score < 0.3):
            hypo.status = HypothesisStatusEnum.CONTRADICTED.value
        elif evidence_score >= 0.75 and has_high_ladder_proof:
            hypo.status = HypothesisStatusEnum.SUPPORTED.value
        else:
            hypo.status = HypothesisStatusEnum.TESTING.value

        self.db.commit()

    # --- Assumption Risk Matrix (2x2) ---

    def get_assumption_matrix(self, project_id: int) -> AssumptionMatrixResponse:
        """Trực quan hóa Ma trận Rủi ro Giả định theo 4 góc phần tư."""
        hypos = self.list_hypotheses(project_id=project_id)

        critical_test_first: List[HypothesisResponse] = []
        monitor: List[HypothesisResponse] = []
        important_low_risk: List[HypothesisResponse] = []
        low_priority: List[HypothesisResponse] = []

        for h in hypos:
            # Importance >= 0.7 & Uncertainty >= 0.6 => Critical Test First
            if h.importance >= 0.7 and h.uncertainty >= 0.6:
                critical_test_first.append(h)
            elif h.importance < 0.7 and h.uncertainty >= 0.6:
                monitor.append(h)
            elif h.importance >= 0.7 and h.uncertainty < 0.6:
                important_low_risk.append(h)
            else:
                low_priority.append(h)

        quadrant = AssumptionMatrixQuadrant(
            critical_test_first=critical_test_first,
            monitor=monitor,
            important_low_risk=important_low_risk,
            low_priority=low_priority
        )

        return AssumptionMatrixResponse(
            project_id=project_id,
            total_hypotheses=len(hypos),
            critical_count=len(critical_test_first),
            quadrants=quadrant
        )

    # --- Serialization Helpers ---

    def _serialize_hypothesis(self, h: Hypothesis) -> HypothesisResponse:
        return HypothesisResponse(
            id=h.id,
            workspace_id=h.workspace_id,
            project_id=h.project_id,
            category=h.category,
            statement=h.statement,
            importance=h.importance,
            uncertainty=h.uncertainty,
            risk_score=h.risk_score,
            evidence_score=h.evidence_score,
            confidence=h.confidence,
            status=h.status,
            stage_created=h.stage_created,
            evidence_refs=list(h.evidence_refs or []),
            experiment_refs=list(h.experiment_refs or []),
            next_action=h.next_action,
            created_at=h.created_at,
            updated_at=h.updated_at or h.created_at
        )

    def _serialize_evidence(self, e: Evidence) -> EvidenceResponse:
        weight = LADDER_WEIGHTS.get(e.ladder_level, 0.2)
        return EvidenceResponse(
            id=e.id,
            workspace_id=e.workspace_id,
            project_id=e.project_id,
            type=e.type,
            ladder_level=e.ladder_level,
            ladder_weight=weight,
            source=e.source,
            claim_supported=e.claim_supported,
            strength=e.strength,
            direction=e.direction,
            hypothesis_refs=list(e.hypothesis_refs or []),
            artifact_refs=list(e.artifact_refs or []),
            raw_payload=dict(e.raw_payload or {}),
            captured_at=e.captured_at,
            created_at=e.created_at
        )
