from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from founder_os.outcomes.models import Outcome
from founder_os.strategy.models import OkrLink


class WorkContractService:
    """Service to configure and link work contracts to Outcomes and Key Results."""

    @classmethod
    def set_work_contract(
        cls,
        db: Session,
        outcome: Outcome,
        required_artifacts: Optional[Any] = None,
        reviewer_id: Optional[int] = None,
        review_type: Optional[str] = None,
        validation_rules: Optional[Any] = None,
        linked_kr_ids: Optional[List[int]] = None,
        task_id: Optional[int] = None,
    ) -> Outcome:
        if task_id is not None:
            outcome.task_id = task_id
        if required_artifacts is not None:
            outcome.required_artifacts = (
                {"items": required_artifacts} if isinstance(required_artifacts, list) else required_artifacts
            )
        if reviewer_id is not None:
            outcome.reviewer_id = reviewer_id
        if review_type is not None:
            outcome.review_type = review_type
        if validation_rules is not None:
            outcome.validation_rules = (
                {"rules": validation_rules} if isinstance(validation_rules, list) else validation_rules
            )

        outcome.updated_at = datetime.utcnow()
        db.add(outcome)

        # Handle OKR traceability links
        if linked_kr_ids is not None:
            # Clear old links for this outcome
            db.query(OkrLink).filter(
                OkrLink.workspace_id == outcome.workspace_id,
                OkrLink.from_entity_type == "outcome",
                OkrLink.from_entity_id == outcome.id,
                OkrLink.to_entity_type == "key_result",
            ).delete(synchronize_session=False)

            # Insert new links
            for kr_id in linked_kr_ids:
                link = OkrLink(
                    workspace_id=outcome.workspace_id,
                    from_entity_type="outcome",
                    from_entity_id=outcome.id,
                    to_entity_type="key_result",
                    to_entity_id=kr_id,
                    relation_type="supports",
                    created_at=datetime.utcnow(),
                )
                db.add(link)

        db.commit()
        db.refresh(outcome)
        return outcome
