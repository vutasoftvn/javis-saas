import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from core.snowflake import generate_snowflake_id
from founder_os.strategy.models import StrategicDecision, Evidence
from platform_core.vault.models import Brain
from founder_os.strategy.schemas.evidence_schemas import (
    StrategicDecisionCreate,
    StrategicDecisionResponse,
)

logger = logging.getLogger(__name__)


class DecisionLogService:
    """COSA Decision Log & Company Memory Service.
    
    Lưu vết các quyết định chiến lược có bằng chứng (Decision Lineage) và cung cấp
    bộ nhớ công ty (Company Memory) trả lời câu hỏi: Vì sao chúng ta đưa ra quyết định này?
    """

    def __init__(self, db: Session, workspace_id: int, user_id: Optional[int] = None):
        self.db = db
        self.workspace_id = workspace_id
        self.user_id = user_id

    def record_decision(self, payload: StrategicDecisionCreate) -> StrategicDecisionResponse:
        """Ghi nhận một quyết định chiến lược kèm danh sách bằng chứng minh chứng."""
        brain = self.db.query(Brain).filter(Brain.workspace_id == self.workspace_id).first()
        brain_id = brain.id if brain else generate_snowflake_id()

        dec = StrategicDecision(
            workspace_id=self.workspace_id,
            brain_id=brain_id,
            project_id=payload.project_id,
            question=payload.question,
            decision=f"{payload.question} -> {payload.selected_option}",
            selected_option=payload.selected_option,
            alternatives_jsonb=payload.alternatives,
            rationale=payload.rationale,
            evidence_refs=payload.evidence_refs,
            stage=payload.stage,
            expected_result=payload.expected_result,
            review_date=payload.review_date,
            status="active",
            decided_by=self.user_id,
        )
        self.db.add(dec)
        self.db.commit()
        self.db.refresh(dec)
        return self._serialize_decision(dec)

    def list_decisions(self, project_id: Optional[int] = None) -> List[StrategicDecisionResponse]:
        """Danh sách các quyết định chiến lược."""
        query = self.db.query(StrategicDecision).filter(
            StrategicDecision.workspace_id == self.workspace_id
        )
        if project_id:
            query = query.filter(StrategicDecision.project_id == project_id)

        decisions = query.order_by(desc(StrategicDecision.created_at)).all()
        return [self._serialize_decision(d) for d in decisions]

    def query_company_memory(
        self,
        query_text: Optional[str] = None,
        project_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Truy vấn Bộ Nhớ Quyết Định Công Ty kèm bằng chứng minh chứng chi tiết."""
        query = self.db.query(StrategicDecision).filter(
            StrategicDecision.workspace_id == self.workspace_id
        )
        if project_id:
            query = query.filter(StrategicDecision.project_id == project_id)

        decisions = query.order_by(desc(StrategicDecision.created_at)).all()
        memory_items: List[Dict[str, Any]] = []

        for d in decisions:
            # Lọc theo từ khóa nếu có
            if query_text:
                text_corpus = f"{d.question or ''} {d.selected_option or ''} {d.rationale or ''}".lower()
                if query_text.lower() not in text_corpus:
                    continue

            # Trích xuất các Evidence thực tế từ evidence_refs
            ev_ids = list(d.evidence_refs or [])
            evidences = []
            if ev_ids:
                ev_objs = self.db.query(Evidence).filter(
                    Evidence.id.in_(ev_ids),
                    Evidence.workspace_id == self.workspace_id
                ).all()
                evidences = [
                    {
                        "id": e.id,
                        "ladder_level": e.ladder_level,
                        "source": e.source,
                        "claim_supported": e.claim_supported,
                        "strength": e.strength,
                    }
                    for e in ev_objs
                ]

            memory_items.append({
                "decision_id": d.id,
                "project_id": d.project_id,
                "stage": d.stage,
                "question": d.question or d.decision,
                "selected_option": d.selected_option,
                "alternatives": list(d.alternatives_jsonb or []),
                "rationale": d.rationale,
                "evidences": evidences,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            })

        return memory_items

    def _serialize_decision(self, d: StrategicDecision) -> StrategicDecisionResponse:
        return StrategicDecisionResponse(
            id=d.id,
            workspace_id=d.workspace_id,
            project_id=d.project_id,
            question=d.question,
            decision=d.decision,
            selected_option=d.selected_option,
            alternatives=list(d.alternatives_jsonb or []),
            rationale=d.rationale,
            evidence_refs=list(d.evidence_refs or []),
            stage=d.stage or "S1_PROBLEM_VALIDATION",
            expected_result=d.expected_result,
            review_date=d.review_date,
            status=d.status,
            decided_by=d.decided_by,
            created_at=d.created_at
        )
