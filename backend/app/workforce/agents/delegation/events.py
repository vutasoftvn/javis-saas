from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.founder_os.outcomes.models import OutcomeRun, RunEvent


def append_run_event(
    db: Session,
    run_id: int,
    event_type: str,
    payload: dict[str, Any],
    event_key: str,
) -> RunEvent:
    """Append one ordered event, returning the existing row on replay."""
    outcome_run = (
        db.query(OutcomeRun)
        .filter(OutcomeRun.id == run_id)
        .with_for_update()
        .one_or_none()
    )
    if outcome_run is None:
        raise ValueError(f"OutcomeRun {run_id} not found")

    existing = (
        db.query(RunEvent)
        .filter(
            RunEvent.run_id == run_id,
            RunEvent.event_key == event_key,
        )
        .one_or_none()
    )
    if existing is not None:
        return existing

    last_sequence = (
        db.query(func.max(RunEvent.sequence))
        .filter(RunEvent.run_id == run_id)
        .scalar()
    )
    event = RunEvent(
        id=generate_snowflake_id(),
        run_id=run_id,
        sequence=int(last_sequence or 0) + 1,
        event_key=event_key,
        event_type=event_type,
        payload_jsonb=payload,
    )
    db.add(event)
    db.flush()
    return event
