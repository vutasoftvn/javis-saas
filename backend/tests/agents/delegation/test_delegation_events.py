from core.snowflake import generate_snowflake_id
from db.session import SessionLocal
from founder_os.outcomes.models import Outcome, OutcomeRun, RunEvent
from platform_core.auth.models import User, Workspace


def test_append_run_event_allocates_order_and_is_idempotent():
    """Concurrent-safe event keys prevent duplicate business transitions."""
    from workforce.agents.delegation.events import append_run_event

    db = SessionLocal()
    try:
        user_id = generate_snowflake_id()
        workspace_id = generate_snowflake_id()
        outcome_id = generate_snowflake_id()
        run_id = generate_snowflake_id()

        db.add(User(id=user_id, email=f"phase-c-{user_id}@example.invalid"))
        db.add(Workspace(id=workspace_id, name=f"Phase C {workspace_id}"))
        db.flush()
        db.add(
            Outcome(
                id=outcome_id,
                workspace_id=workspace_id,
                title="Phase C event ordering",
                desired_result="Ordered durable events",
                requested_by=user_id,
            )
        )
        db.flush()
        db.add(OutcomeRun(id=run_id, outcome_id=outcome_id, status="running"))
        db.flush()

        first = append_run_event(
            db,
            run_id,
            "step.assigned",
            {"step_id": "1"},
            "assign:1:1",
        )
        duplicate = append_run_event(
            db,
            run_id,
            "step.assigned",
            {"step_id": "1"},
            "assign:1:1",
        )
        second = append_run_event(
            db,
            run_id,
            "step.delegation_queued",
            {"step_id": "1"},
            "queue:1:1",
        )

        assert duplicate.id == first.id
        assert (first.sequence, second.sequence) == (1, 2)
        assert (
            db.query(RunEvent)
            .filter(RunEvent.run_id == run_id)
            .count()
            == 2
        )
    finally:
        db.rollback()
        db.close()
