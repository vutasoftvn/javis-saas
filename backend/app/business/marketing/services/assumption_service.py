from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc

from app.business.marketing.models_validation import (
    Assumption,
    Evidence,
    KnowledgeStatement,
    EpistemicStatus,
    KnowledgeOrigin,
    ConfidenceLevel,
    AssumptionCategory,
    AssumptionStatus,
    EvidenceStrength,
)
from app.business.marketing.schemas.validation_schemas import (
    AssumptionCreate,
    AssumptionUpdate,
    EvidenceCreate,
    KnowledgeStatementCreate,
)


class AssumptionService:
    @staticmethod
    def calculate_criticality(impact: int, uncertainty: int) -> int:
        """
        Tính Criticality = Impact (1-5) * Uncertainty (1-5) theo §14 trong E3.md.
        Phạm vi điểm: 1 đến 25.
        """
        clean_impact = max(1, min(5, impact))
        clean_uncertainty = max(1, min(5, uncertainty))
        return clean_impact * clean_uncertainty

    @classmethod
    def create_assumption(
        cls,
        db: Session,
        workspace_id: int,
        brain_id: int,
        data: AssumptionCreate,
    ) -> Assumption:
        """
        Tạo mới một Assumption trong hệ thống.
        """
        criticality = cls.calculate_criticality(data.impact, data.uncertainty)
        
        assumption = Assumption(
            workspace_id=workspace_id,
            brain_id=brain_id,
            project_id=data.project_id,
            canvas_id=data.canvas_id,
            category=data.category.value if hasattr(data.category, "value") else str(data.category),
            statement=data.statement.strip(),
            impact=data.impact,
            uncertainty=data.uncertainty,
            criticality=criticality,
            confidence=data.confidence.value if hasattr(data.confidence, "value") else str(data.confidence),
            status=data.status.value if hasattr(data.status, "value") else str(data.status),
            rationale=data.rationale,
            evidence_ids=list(data.evidence_ids),
            experiment_ids=list(data.experiment_ids),
        )
        db.add(assumption)
        db.flush()
        return assumption

    @classmethod
    def update_assumption(
        cls,
        db: Session,
        assumption: Assumption,
        data: AssumptionUpdate,
    ) -> Assumption:
        """
        Cập nhật giả định và tự động tính lại criticality nếu impact/uncertainty thay đổi.
        """
        update_data = data.model_dump(exclude_unset=True)
        
        impact = update_data.get("impact", assumption.impact)
        uncertainty = update_data.get("uncertainty", assumption.uncertainty)
        assumption.criticality = cls.calculate_criticality(impact, uncertainty)
        
        for key, value in update_data.items():
            if value is not None:
                if hasattr(value, "value"):
                    setattr(assumption, key, value.value)
                else:
                    setattr(assumption, key, value)
                    
        db.flush()
        return assumption

    @classmethod
    def create_knowledge_statement(
        cls,
        db: Session,
        workspace_id: int,
        brain_id: int,
        data: KnowledgeStatementCreate,
    ) -> KnowledgeStatement:
        """
        Tạo Knowledge Statement tuân thủ nguyên tắc:
        'AI-generated != Validated' (§5, §6 trong E3.md).
        Mọi claim tự sinh từ AI mặc định là ASSUMPTION và confidence LOW.
        """
        origin_val = data.origin.value if hasattr(data.origin, "value") else str(data.origin)
        status_val = data.epistemic_status.value if hasattr(data.epistemic_status, "value") else str(data.epistemic_status)
        conf_val = data.confidence.value if hasattr(data.confidence, "value") else str(data.confidence)

        # Enforce AI claim rule
        if origin_val == KnowledgeOrigin.AI_GENERATED.value and not data.evidence_ids:
            status_val = EpistemicStatus.ASSUMPTION.value
            conf_val = ConfidenceLevel.LOW.value

        statement = KnowledgeStatement(
            workspace_id=workspace_id,
            brain_id=brain_id,
            project_id=data.project_id,
            statement=data.statement.strip(),
            epistemic_status=status_val,
            origin=origin_val,
            confidence=conf_val,
            evidence_ids=list(data.evidence_ids),
            meta_data=data.meta_data,
        )
        db.add(statement)
        db.flush()
        return statement

    @classmethod
    def create_evidence(
        cls,
        db: Session,
        workspace_id: int,
        brain_id: int,
        data: EvidenceCreate,
    ) -> Tuple[Evidence, List[Assumption]]:
        """
        Tạo Evidence và cập nhật trạng thái/độ tin cậy của các Assumption liên quan (§34, §40).
        """
        evidence = Evidence(
            workspace_id=workspace_id,
            brain_id=brain_id,
            project_id=data.project_id,
            source_type=data.source_type.value if hasattr(data.source_type, "value") else str(data.source_type),
            source_id=data.source_id,
            statement=data.statement.strip(),
            supports_assumption_ids=[str(i) for i in data.supports_assumption_ids],
            contradicts_assumption_ids=[str(i) for i in data.contradicts_assumption_ids],
            strength=data.strength.value if hasattr(data.strength, "value") else str(data.strength),
            meta_data=data.meta_data,
            collected_at=data.collected_at or datetime.utcnow(),
        )
        db.add(evidence)
        db.flush()

        evidence_str_id = str(evidence.id)
        updated_assumptions: List[Assumption] = []

        # Update Supported Assumptions
        for asm_id_str in evidence.supports_assumption_ids:
            try:
                asm_id = int(asm_id_str)
            except ValueError:
                continue
            asm = db.query(Assumption).filter(
                Assumption.id == asm_id,
                Assumption.workspace_id == workspace_id,
            ).first()
            if asm:
                ev_list = list(asm.evidence_ids or [])
                if evidence_str_id not in ev_list:
                    ev_list.append(evidence_str_id)
                asm.evidence_ids = ev_list
                
                # Update status based on evidence strength
                unc = asm.uncertainty if asm.uncertainty is not None else 3
                imp = asm.impact if asm.impact is not None else 3
                if evidence.strength == EvidenceStrength.STRONG.value:
                    asm.status = AssumptionStatus.SUPPORTED.value
                    asm.confidence = ConfidenceLevel.HIGH.value
                    asm.uncertainty = max(1, unc - 2)
                elif evidence.strength == EvidenceStrength.MEDIUM.value:
                    if asm.status == AssumptionStatus.UNTESTED.value:
                        asm.status = AssumptionStatus.PARTIALLY_SUPPORTED.value
                    asm.confidence = ConfidenceLevel.MEDIUM.value
                    asm.uncertainty = max(1, unc - 1)
                else:
                    if asm.status == AssumptionStatus.UNTESTED.value:
                        asm.status = AssumptionStatus.TESTING.value
                    asm.uncertainty = unc
                
                asm.impact = imp
                asm.criticality = cls.calculate_criticality(asm.impact, asm.uncertainty)
                updated_assumptions.append(asm)

        # Update Contradicted Assumptions
        for asm_id_str in evidence.contradicts_assumption_ids:
            try:
                asm_id = int(asm_id_str)
            except ValueError:
                continue
            asm = db.query(Assumption).filter(
                Assumption.id == asm_id,
                Assumption.workspace_id == workspace_id,
            ).first()
            if asm:
                ev_list = list(asm.evidence_ids or [])
                if evidence_str_id not in ev_list:
                    ev_list.append(evidence_str_id)
                asm.evidence_ids = ev_list
                
                if evidence.strength in (EvidenceStrength.STRONG.value, EvidenceStrength.MEDIUM.value):
                    asm.status = AssumptionStatus.CONTRADICTED.value
                    asm.confidence = ConfidenceLevel.HIGH.value  # high confidence that it is false
                else:
                    asm.status = AssumptionStatus.INCONCLUSIVE.value
                
                updated_assumptions.append(asm)

        db.flush()
        return evidence, updated_assumptions

    @classmethod
    def get_assumptions(
        cls,
        db: Session,
        workspace_id: int,
        project_id: Optional[int] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        min_criticality: Optional[int] = None,
    ) -> List[Assumption]:
        """
        Lấy danh sách assumption xếp hạng theo Criticality giảm dần.
        """
        query = db.query(Assumption).filter(Assumption.workspace_id == workspace_id)
        if project_id is not None:
            query = query.filter(Assumption.project_id == project_id)
        if category:
            query = query.filter(Assumption.category == category)
        if status:
            query = query.filter(Assumption.status == status)
        if min_criticality is not None:
            query = query.filter(Assumption.criticality >= min_criticality)

        assumptions = query.all()
        # Sort in python memory to ensure consistent sorting even on FakeQuery
        return sorted(
            assumptions,
            key=lambda a: (getattr(a, "criticality", 0), getattr(a, "impact", 0)),
            reverse=True,
        )

    @classmethod
    def get_assumptions_summary(
        cls,
        db: Session,
        workspace_id: int,
        project_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Tổng hợp thống kê giả định cho Marketing Cockpit Dashboard & Hologram Hub (§46).
        """
        assumptions = cls.get_assumptions(db, workspace_id, project_id=project_id)
        
        total = len(assumptions)
        untested = sum(1 for a in assumptions if a.status == AssumptionStatus.UNTESTED.value)
        testing = sum(1 for a in assumptions if a.status == AssumptionStatus.TESTING.value)
        supported = sum(1 for a in assumptions if a.status == AssumptionStatus.SUPPORTED.value)
        partially = sum(1 for a in assumptions if a.status == AssumptionStatus.PARTIALLY_SUPPORTED.value)
        contradicted = sum(1 for a in assumptions if a.status == AssumptionStatus.CONTRADICTED.value)
        critical_untested = sum(1 for a in assumptions if a.criticality >= 15 and a.status == AssumptionStatus.UNTESTED.value)
        highest_crit = max([a.criticality for a in assumptions], default=0)

        top_critical = [a for a in assumptions if a.criticality >= 15][:5]

        return {
            "total_assumptions": total,
            "untested_count": untested,
            "testing_count": testing,
            "supported_count": supported,
            "partially_supported_count": partially,
            "contradicted_count": contradicted,
            "critical_untested_count": critical_untested,
            "highest_criticality": highest_crit,
            "top_critical_assumptions": top_critical,
        }
