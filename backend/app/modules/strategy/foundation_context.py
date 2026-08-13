from typing import Optional

from sqlalchemy.orm import Session

from app.modules.strategy.models import CoreValue, StrategyCanvas, StrategyFoundation, StrategyRevision


def fetch_foundation_context(db: Session, workspace_id: int) -> Optional[dict]:
    """Vision/Mission/Core Values from the workspace's approved Foundation, for
    AI prompts that need it (design §"AI routing assessment consumes the
    Foundation..."). Returns None if the workspace has no canvas, no approved
    revision, or no foundation yet - callers must treat that as "no strategy
    context available" rather than an error."""
    canvas = (
        db.query(StrategyCanvas)
        .filter(StrategyCanvas.workspace_id == workspace_id)
        .order_by(StrategyCanvas.created_at.desc())
        .first()
    )
    if canvas is None:
        return None

    revision = (
        db.query(StrategyRevision)
        .filter(StrategyRevision.canvas_id == canvas.id, StrategyRevision.status == "approved")
        .order_by(StrategyRevision.revision_no.desc())
        .first()
    )
    if revision is None:
        return None

    foundation = (
        db.query(StrategyFoundation)
        .filter(StrategyFoundation.strategy_revision_id == revision.id)
        .first()
    )
    if foundation is None:
        return None

    values = (
        db.query(CoreValue)
        .filter(CoreValue.foundation_id == foundation.id)
        .order_by(CoreValue.slot_no.asc())
        .all()
    )
    return {
        "vision": foundation.vision,
        "mission": foundation.mission,
        "core_values": [
            {"title": v.title, "description": v.description, "decision_rule": v.decision_rule}
            for v in values
        ],
    }
