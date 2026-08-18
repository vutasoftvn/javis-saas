from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, and_

from app.founder_os.validation.models import (
    ValidationSession,
    StructuredClaim,
    FieldRevision,
    ValidationAssumption,
    ValidationHypothesis,
    ValidationExperiment,
    ValidationEvidence,
    ValidationReview,
    ValidationDecision,
    DimensionState,
    ProjectStageHistory,
    ClaimConfirmationStatus,
    EpistemicType,
    DimensionName,
    DimensionStateEnum,
    FeasibilityPillar,
    AssumptionStatus,
    ValidationWorkflowState,
    ProjectStage,
)
from app.founder_os.validation.schemas import (
    StructuredClaimCreate,
    StructuredClaimEditRequest,
    AssumptionCreate,
    AssumptionUpdate,
    HypothesisCreate,
    ExperimentCreate,
    EvidenceCreate,
    ValidationReviewCreate,
    ValidationDecisionCreate,
    StateVectorResponse,
    DimensionStateResponse,
)
from app.founder_os.strategy.models import Project


class ValidationEngineService:
    @staticmethod
    def get_or_create_session(
        db: Session,
        workspace_id: int,
        brain_id: int,
        project_id: int,
        initial_topic: str = DimensionName.CUSTOMER.value,
    ) -> ValidationSession:
        stmt = (
            select(ValidationSession)
            .where(
                and_(
                    ValidationSession.workspace_id == workspace_id,
                    ValidationSession.project_id == project_id,
                )
            )
            .order_by(desc(ValidationSession.created_at))
        )
        session = db.scalars(stmt).first()
        if not session:
            session = ValidationSession(
                workspace_id=workspace_id,
                brain_id=brain_id,
                project_id=project_id,
                current_topic=initial_topic,
                workflow_state=ValidationWorkflowState.DATA_COLLECTION.value,
                interview_mode_active=True,
                fields_status_jsonb={},
                session_metadata={},
            )
            db.add(session)
            db.commit()
            db.refresh(session)
        return session

    @staticmethod
    def create_claim(
        db: Session,
        workspace_id: int,
        brain_id: int,
        project_id: int,
        claim_in: StructuredClaimCreate,
        session_id: Optional[int] = None,
    ) -> StructuredClaim:
        val_json = (
            claim_in.value
            if isinstance(claim_in.value, dict)
            else {"raw": claim_in.value}
        )
        claim = StructuredClaim(
            workspace_id=workspace_id,
            brain_id=brain_id,
            project_id=project_id,
            session_id=session_id,
            dimension=claim_in.dimension.value if hasattr(claim_in.dimension, "value") else str(claim_in.dimension),
            subject=claim_in.subject,
            predicate=claim_in.predicate,
            value_jsonb=val_json,
            epistemic_type=claim_in.epistemic_type.value if hasattr(claim_in.epistemic_type, "value") else str(claim_in.epistemic_type),
            confirmation_status=ClaimConfirmationStatus.AI_INFERRED.value,
            source_type=claim_in.source_type or "FOUNDER_CHAT",
            source_actor=claim_in.source_actor or "FOUNDER",
            source_ref=claim_in.source_ref,
            confidence=claim_in.confidence if claim_in.confidence is not None else 1.0,
        )
        db.add(claim)
        db.commit()
        db.refresh(claim)
        return claim

    @staticmethod
    def confirm_claim(
        db: Session,
        claim_id: int,
        confidence: float = 1.0,
    ) -> StructuredClaim:
        claim = db.get(StructuredClaim, claim_id)
        if not claim:
            raise ValueError(f"StructuredClaim {claim_id} not found")

        claim.confirmation_status = ClaimConfirmationStatus.FOUNDER_CONFIRMED.value
        claim.confidence = confidence
        claim.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(claim)
        return claim

    @staticmethod
    def edit_claim(
        db: Session,
        claim_id: int,
        edit_in: StructuredClaimEditRequest,
        changed_by: str = "FOUNDER",
    ) -> StructuredClaim:
        claim = db.get(StructuredClaim, claim_id)
        if not claim:
            raise ValueError(f"StructuredClaim {claim_id} not found")

        old_val = claim.value_jsonb
        new_val = (
            edit_in.new_value
            if isinstance(edit_in.new_value, dict)
            else {"raw": edit_in.new_value}
        )

        # 1. Record immutable revision
        field_path = f"{claim.dimension}.{claim.subject}.{claim.predicate}"
        revision = FieldRevision(
            workspace_id=claim.workspace_id,
            project_id=claim.project_id,
            claim_id=claim.id,
            field_path=field_path,
            old_value_jsonb=old_val,
            new_value_jsonb=new_val,
            changed_by=changed_by,
            reason=edit_in.reason or "Founder correction",
        )
        db.add(revision)

        # 2. Update claim with new value
        claim.value_jsonb = new_val
        claim.confirmation_status = ClaimConfirmationStatus.FOUNDER_EDITED.value
        claim.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(claim)
        return claim

    @staticmethod
    def create_assumption(
        db: Session,
        workspace_id: int,
        brain_id: int,
        project_id: int,
        assumption_in: AssumptionCreate,
    ) -> ValidationAssumption:
        risk = assumption_in.importance * assumption_in.uncertainty
        assumption = ValidationAssumption(
            workspace_id=workspace_id,
            brain_id=brain_id,
            project_id=project_id,
            claim_id=assumption_in.claim_id,
            category=assumption_in.category.value if hasattr(assumption_in.category, "value") else str(assumption_in.category),
            statement=assumption_in.statement,
            importance=assumption_in.importance,
            uncertainty=assumption_in.uncertainty,
            impact=assumption_in.impact,
            risk_score=risk,
            source=assumption_in.source or "FOUNDER_CHAT",
            status=AssumptionStatus.UNTESTED.value,
            confidence=0.5,
            owner=assumption_in.owner,
        )
        db.add(assumption)
        db.commit()
        db.refresh(assumption)
        return assumption

    @staticmethod
    def update_assumption(
        db: Session,
        assumption_id: int,
        update_in: AssumptionUpdate,
    ) -> ValidationAssumption:
        assumption = db.get(ValidationAssumption, assumption_id)
        if not assumption:
            raise ValueError(f"Assumption {assumption_id} not found")

        if update_in.statement is not None:
            assumption.statement = update_in.statement
        if update_in.importance is not None:
            assumption.importance = update_in.importance
        if update_in.uncertainty is not None:
            assumption.uncertainty = update_in.uncertainty
        if update_in.impact is not None:
            assumption.impact = update_in.impact
        if update_in.status is not None:
            assumption.status = update_in.status.value if hasattr(update_in.status, "value") else str(update_in.status)
        if update_in.confidence is not None:
            assumption.confidence = update_in.confidence
        if update_in.owner is not None:
            assumption.owner = update_in.owner

        assumption.risk_score = assumption.importance * assumption.uncertainty
        assumption.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(assumption)
        return assumption

    @staticmethod
    def build_hypothesis(
        db: Session,
        workspace_id: int,
        brain_id: int,
        project_id: int,
        hypo_in: HypothesisCreate,
    ) -> ValidationHypothesis:
        # Check Quality Gate (F1.md §45): Action, Target, Metric, Threshold, Timeframe
        quality_gate_passed = bool(
            hypo_in.action.strip()
            and hypo_in.target_segment.strip()
            and hypo_in.metric.strip()
            and hypo_in.threshold.strip()
            and hypo_in.timeframe_days > 0
        )

        formatted_stmt = (
            f"IF [{hypo_in.action.strip()}] FOR [{hypo_in.target_segment.strip()}] "
            f"THEN [{hypo_in.metric.strip()}] WILL REACH [{hypo_in.threshold.strip()}] "
            f"WITHIN [{hypo_in.timeframe_days} DAYS]"
        )

        hypothesis = ValidationHypothesis(
            workspace_id=workspace_id,
            brain_id=brain_id,
            project_id=project_id,
            assumption_id=hypo_in.assumption_id,
            action=hypo_in.action,
            target_segment=hypo_in.target_segment,
            metric=hypo_in.metric,
            threshold=hypo_in.threshold,
            timeframe_days=hypo_in.timeframe_days,
            statement=formatted_stmt,
            quality_gate_passed=quality_gate_passed,
            status="READY" if quality_gate_passed else "DRAFT",
        )
        db.add(hypothesis)
        db.commit()
        db.refresh(hypothesis)
        return hypothesis

    @staticmethod
    def create_experiment(
        db: Session,
        workspace_id: int,
        brain_id: int,
        project_id: int,
        exp_in: ExperimentCreate,
    ) -> ValidationExperiment:
        experiment = ValidationExperiment(
            workspace_id=workspace_id,
            brain_id=brain_id,
            project_id=project_id,
            hypothesis_id=exp_in.hypothesis_id,
            experiment_type=exp_in.experiment_type.value if hasattr(exp_in.experiment_type, "value") else str(exp_in.experiment_type),
            name=exp_in.name,
            description=exp_in.description,
            smallest_useful_scope=exp_in.smallest_useful_scope,
            success_threshold=exp_in.success_threshold,
            budget_amount=exp_in.budget_amount,
            duration_days=exp_in.duration_days,
            status="DRAFT",
        )
        db.add(experiment)
        db.commit()
        db.refresh(experiment)
        return experiment

    @staticmethod
    def record_evidence(
        db: Session,
        workspace_id: int,
        brain_id: int,
        project_id: int,
        evi_in: EvidenceCreate,
    ) -> ValidationEvidence:
        evidence = ValidationEvidence(
            workspace_id=workspace_id,
            brain_id=brain_id,
            project_id=project_id,
            assumption_id=evi_in.assumption_id,
            hypothesis_id=evi_in.hypothesis_id,
            experiment_id=evi_in.experiment_id,
            evidence_type=evi_in.evidence_type.value if hasattr(evi_in.evidence_type, "value") else str(evi_in.evidence_type),
            source_type=evi_in.source_type,
            source_ref=evi_in.source_ref,
            observation=evi_in.observation,
            metric_name=evi_in.metric_name,
            metric_value=evi_in.metric_value,
            relationship=evi_in.relationship.value if hasattr(evi_in.relationship, "value") else str(evi_in.relationship),
            confidence=evi_in.confidence,
            attachments_jsonb=evi_in.attachments or [],
        )
        db.add(evidence)
        db.commit()
        db.refresh(evidence)
        return evidence

    @staticmethod
    def create_review(
        db: Session,
        workspace_id: int,
        brain_id: int,
        project_id: int,
        review_in: ValidationReviewCreate,
    ) -> ValidationReview:
        review = ValidationReview(
            workspace_id=workspace_id,
            brain_id=brain_id,
            project_id=project_id,
            hypothesis_id=review_in.hypothesis_id,
            review_provider_type=review_in.review_provider_type.value if hasattr(review_in.review_provider_type, "value") else str(review_in.review_provider_type),
            verdict=review_in.verdict.value if hasattr(review_in.verdict, "value") else str(review_in.verdict),
            confidence_score=review_in.confidence_score,
            supported_points=review_in.supported_points,
            challenged_points=review_in.challenged_points,
            missing_evidence=review_in.missing_evidence,
            critical_risks=review_in.critical_risks,
            recommended_next_action=review_in.recommended_next_action,
            human_review_recommended=review_in.human_review_recommended,
            raw_report=review_in.raw_report,
        )
        db.add(review)
        db.commit()
        db.refresh(review)
        return review

    @staticmethod
    def record_decision(
        db: Session,
        workspace_id: int,
        brain_id: int,
        project_id: int,
        decision_in: ValidationDecisionCreate,
        user_id: Optional[int] = None,
    ) -> ValidationDecision:
        ai_rec = None
        if decision_in.review_id:
            review = db.get(ValidationReview, decision_in.review_id)
            if review:
                ai_rec = review.verdict

        decision = ValidationDecision(
            workspace_id=workspace_id,
            brain_id=brain_id,
            project_id=project_id,
            review_id=decision_in.review_id,
            ai_recommendation=ai_rec,
            founder_decision=decision_in.founder_decision.value if hasattr(decision_in.founder_decision, "value") else str(decision_in.founder_decision),
            rationale=decision_in.rationale,
            risks_acknowledged=decision_in.risks_acknowledged,
            decided_by=user_id,
        )
        db.add(decision)
        db.commit()
        db.refresh(decision)
        return decision

    @staticmethod
    def get_state_vector(
        db: Session,
        project_id: int,
    ) -> StateVectorResponse:
        project = db.get(Project, project_id)
        stage_name = project.project_stage if project else ProjectStage.IDEA.value

        # Fetch dimension states
        dim_states = db.scalars(
            select(DimensionState).where(DimensionState.project_id == project_id)
        ).all()

        dims_dict: Dict[str, DimensionStateResponse] = {}
        total_conf = 0.0

        for ds in dim_states:
            dims_dict[ds.dimension] = DimensionStateResponse(
                dimension=ds.dimension,
                pillar=ds.pillar,
                state=ds.state,
                confidence=ds.confidence,
                summary=ds.summary,
                updated_at=ds.updated_at,
            )
            total_conf += ds.confidence

        overall_conf = round(total_conf / len(dims_dict), 2) if dims_dict else 0.0

        # Critical assumptions count (risk >= 15)
        crit_count = len(
            db.scalars(
                select(ValidationAssumption).where(
                    and_(
                        ValidationAssumption.project_id == project_id,
                        ValidationAssumption.risk_score >= 15,
                    )
                )
            ).all()
        )

        # Active experiments count
        active_exp_count = len(
            db.scalars(
                select(ValidationExperiment).where(
                    and_(
                        ValidationExperiment.project_id == project_id,
                        ValidationExperiment.status.in_(["SCHEDULED", "RUNNING"]),
                    )
                )
            ).all()
        )

        return StateVectorResponse(
            project_id=project_id,
            project_stage=stage_name,
            workflow_state=ValidationWorkflowState.DATA_COLLECTION.value,
            overall_confidence=overall_conf,
            dimensions=dims_dict,
            critical_assumptions_count=crit_count,
            active_experiments_count=active_exp_count,
            primary_next_best_action="Validate critical problem and customer willingness before scaling.",
        )
