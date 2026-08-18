from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.business.sales.models import Customer, SalesActivity, SalesOpportunity
from app.business.sales.domain.activities import ActivityService
from app.platform.license.handoff_service import HandoffService
from app.business.learning.service import create_lesson


LEGAL_OPPORTUNITY_TRANSITIONS = {
    "DISCOVERY": {"QUALIFIED", "LOST"},
    "QUALIFIED": {"SOLUTION", "LOST"},
    "SOLUTION": {"PROPOSAL", "LOST"},
    "PROPOSAL": {"NEGOTIATION", "LOST"},
    "NEGOTIATION": {"WON", "LOST"},
    "WON": set(),
    "LOST": set(),
}

VALID_LOST_REASONS = {
    "PRICE",
    "NO_NEED",
    "NO_BUDGET",
    "TIMING",
    "COMPETITOR",
    "TRUST",
    "FEATURE_GAP",
    "NO_RESPONSE",
    "LEGAL",
    "TECHNICAL",
    "OTHER",
}


class OpportunityStageService:
    @staticmethod
    def can_transition(current_stage: str, target_stage: str) -> bool:
        allowed = LEGAL_OPPORTUNITY_TRANSITIONS.get(current_stage.upper(), set())
        return target_stage.upper() in allowed


class OpportunityService:
    @staticmethod
    def create_opportunity(
        db: Session,
        workspace_id: int,
        account_id: int,
        cycle_id: Optional[int] = None,
        product: Optional[str] = None,
        primary_contact_id: Optional[int] = None,
        source_lead_id: Optional[int] = None,
        estimated_value: Optional[float] = None,
        currency: str = "VND",
        expected_close_date: Optional[datetime] = None,
        owner_id: Optional[int] = None,
        pain_points: Optional[List[str]] = None,
        needs: Optional[List[str]] = None,
        objections: Optional[List[str]] = None,
        competitors: Optional[List[str]] = None,
    ) -> SalesOpportunity:
        opp = SalesOpportunity(
            workspace_id=workspace_id,
            cycle_id=cycle_id,
            account_id=account_id,
            product=product,
            primary_contact_id=primary_contact_id,
            source_lead_id=source_lead_id,
            stage="DISCOVERY",
            estimated_value=estimated_value,
            currency=currency,
            expected_close_date=expected_close_date,
            owner_id=owner_id,
            pain_points=pain_points,
            needs=needs,
            objections=objections,
            competitors=competitors,
        )
        db.add(opp)
        db.commit()
        db.refresh(opp)

        ActivityService.create_activity(
            db=db,
            workspace_id=workspace_id,
            entity_type="opportunity",
            entity_id=opp.id,
            activity_type="STATUS_CHANGE",
            summary=f"Opportunity created in DISCOVERY stage",
            actor_id=owner_id,
        )
        return opp

    @staticmethod
    def transition_stage(
        db: Session,
        workspace_id: int,
        opportunity_id: int,
        target_stage: str,
        actor_id: Optional[int] = None,
    ) -> SalesOpportunity:
        opp = db.query(SalesOpportunity).filter(SalesOpportunity.id == opportunity_id, SalesOpportunity.workspace_id == workspace_id).first()
        if not opp:
            raise HTTPException(status_code=404, detail="Opportunity not found")

        target_stage = target_stage.upper()
        if target_stage in {"WON", "LOST"}:
            raise HTTPException(
                status_code=400,
                detail=f"Use /win or /lose endpoint to transition to {target_stage} with required reasons",
            )

        if not OpportunityStageService.can_transition(opp.stage, target_stage):
            raise HTTPException(
                status_code=400,
                detail=f"Illegal stage transition from {opp.stage} to {target_stage}",
            )

        old_stage = opp.stage
        opp.stage = target_stage
        db.add(opp)
        db.commit()
        db.refresh(opp)

        ActivityService.record_status_change(
            db=db,
            workspace_id=workspace_id,
            entity_type="opportunity",
            entity_id=opp.id,
            old_status=old_stage,
            new_status=target_stage,
            actor_id=actor_id,
        )
        return opp

    @staticmethod
    def win_opportunity(
        db: Session,
        workspace_id: int,
        opportunity_id: int,
        won_reason: str,
        evidence: Optional[str] = None,
        actor_id: Optional[int] = None,
    ) -> SalesOpportunity:
        opp = db.query(SalesOpportunity).filter(SalesOpportunity.id == opportunity_id, SalesOpportunity.workspace_id == workspace_id).first()
        if not opp:
            raise HTTPException(status_code=404, detail="Opportunity not found")

        if not OpportunityStageService.can_transition(opp.stage, "WON"):
            raise HTTPException(
                status_code=400,
                detail=f"Illegal stage transition from {opp.stage} to WON",
            )

        if not won_reason or not won_reason.strip():
            raise HTTPException(status_code=400, detail="won_reason is required when marking opportunity as WON")

        old_stage = opp.stage
        opp.stage = "WON"
        opp.won_reason = won_reason.strip().upper()
        db.add(opp)

        # 1. Create or update Customer entity
        customer = (
            db.query(Customer)
            .filter(Customer.workspace_id == workspace_id, Customer.account_id == opp.account_id)
            .first()
        )
        if not customer:
            customer = Customer(
                workspace_id=workspace_id,
                account_id=opp.account_id,
                acquired_from_opportunity_id=opp.id,
                lifecycle_status="ONBOARDING",
                health_status="HEALTHY",
                owner_id=opp.owner_id,
                first_purchase_at=datetime.utcnow(),
            )
            db.add(customer)

        db.commit()
        db.refresh(opp)

        # 2. Trigger Handoff to Finance
        HandoffService.create_handoff(
            db=db,
            workspace_id=workspace_id,
            from_function="SALES",
            to_function="FINANCE",
            handoff_type="HANDOFF_TO_NEXT_FUNCTION",
            requested_action="Record receivable for won deal",
            artifact_refs=[
                {
                    "opportunity_id": str(opp.id),
                    "estimated_value": opp.estimated_value,
                    "currency": opp.currency,
                    "account_id": str(opp.account_id),
                    "won_reason": opp.won_reason,
                    "evidence": evidence,
                }
            ],
            idempotency_key=f"sales-opportunity-won:{opp.id}",
            cycle_id=opp.cycle_id,
        )

        # 3. Create generic Lesson (learning)
        create_lesson(
            db,
            workspace_id=workspace_id,
            cycle_id=opp.cycle_id,
            function="SALES",
            observation=f"Opportunity {opp.id} won due to {opp.won_reason}. Evidence: {evidence or 'N/A'}",
            recommendation="Apply successful sales tactics to similar prospective accounts.",
            created_by=actor_id,
        )

        # 4. Record Activity
        ActivityService.record_status_change(
            db=db,
            workspace_id=workspace_id,
            entity_type="opportunity",
            entity_id=opp.id,
            old_status=old_stage,
            new_status="WON",
            reason=f"Won reason: {opp.won_reason}",
            actor_id=actor_id,
        )
        return opp

    @staticmethod
    def lose_opportunity(
        db: Session,
        workspace_id: int,
        opportunity_id: int,
        lost_reason: str,
        lost_reason_detail: Optional[str] = None,
        actor_id: Optional[int] = None,
    ) -> SalesOpportunity:
        opp = db.query(SalesOpportunity).filter(SalesOpportunity.id == opportunity_id, SalesOpportunity.workspace_id == workspace_id).first()
        if not opp:
            raise HTTPException(status_code=404, detail="Opportunity not found")

        if not OpportunityStageService.can_transition(opp.stage, "LOST"):
            raise HTTPException(
                status_code=400,
                detail=f"Illegal stage transition from {opp.stage} to LOST",
            )

        reason_code = lost_reason.strip().upper()
        if reason_code not in VALID_LOST_REASONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid lost_reason '{lost_reason}'. Must be one of {VALID_LOST_REASONS}",
            )

        old_stage = opp.stage
        opp.stage = "LOST"
        opp.lost_reason = reason_code
        opp.lost_reason_detail = lost_reason_detail
        db.add(opp)
        db.commit()
        db.refresh(opp)

        ActivityService.record_status_change(
            db=db,
            workspace_id=workspace_id,
            entity_type="opportunity",
            entity_id=opp.id,
            old_status=old_stage,
            new_status="LOST",
            reason=f"Lost reason: {reason_code} - {lost_reason_detail or ''}",
            actor_id=actor_id,
        )
        return opp

    @staticmethod
    def list_opportunities(
        db: Session,
        workspace_id: int,
        account_id: Optional[int] = None,
        stage: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[SalesOpportunity]:
        query = db.query(SalesOpportunity).filter(SalesOpportunity.workspace_id == workspace_id)
        if account_id:
            query = query.filter(SalesOpportunity.account_id == account_id)
        if stage:
            query = query.filter(SalesOpportunity.stage == stage.upper())
        return query.order_by(SalesOpportunity.created_at.desc()).offset(offset).limit(limit).all()

    @staticmethod
    def get_opportunity(db: Session, workspace_id: int, opportunity_id: int) -> Optional[SalesOpportunity]:
        return (
            db.query(SalesOpportunity)
            .filter(SalesOpportunity.id == opportunity_id, SalesOpportunity.workspace_id == workspace_id)
            .first()
        )
