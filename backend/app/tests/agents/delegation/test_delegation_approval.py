from sqlalchemy import event

from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.db.session import SessionLocal
from app.platform.auth.models import User, Workspace
from app.workforce.agents.governance.approval_service import ApprovalService


def test_delegation_approval_is_transactional_and_matches_exact_resource():
    """An approval for another step on the same run must not authorize delegation."""
    db = SessionLocal()
    commit_count = 0

    def count_commit(_session):
        nonlocal commit_count
        commit_count += 1

    event.listen(db, "after_commit", count_commit)
    try:
        user_id = generate_snowflake_id()
        workspace_id = generate_snowflake_id()
        run_id = generate_snowflake_id()
        db.add(User(id=user_id, email=f"approval-{user_id}@example.invalid"))
        db.add(Workspace(id=workspace_id, name=f"Approval {workspace_id}"))
        db.flush()
        db.add(
            AgentRun(
                id=run_id,
                workspace_id=workspace_id,
                company_id=workspace_id,
                user_id=user_id,
                agent_key="chief_of_staff",
                runtime="mock",
                status="running",
            )
        )
        db.flush()

        wrong = ApprovalService.create_approval(
            db,
            workspace_id=workspace_id,
            agent_key="chief_of_staff",
            action_type="delegation.assign",
            tool_name="delegation.in_process",
            run_id=run_id,
            capability="agent.delegate",
            resource_type="run_step",
            resource_id="wrong-step",
            idempotency_key="delegation:wrong",
            commit=False,
        )
        exact = ApprovalService.create_approval(
            db,
            workspace_id=workspace_id,
            agent_key="chief_of_staff",
            action_type="delegation.assign",
            tool_name="delegation.in_process",
            run_id=run_id,
            capability="agent.delegate",
            resource_type="run_step",
            resource_id="target-step",
            idempotency_key="delegation:target",
            commit=False,
        )
        wrong.status = "approved"
        exact.status = "approved"
        db.flush()

        matched = ApprovalService.get_matching_delegation_approval(
            db,
            workspace_id=workspace_id,
            run_id=run_id,
            step_id="target-step",
            idempotency_key="delegation:target",
        )

        assert commit_count == 0
        assert matched is not None
        assert matched.id == exact.id
    finally:
        event.remove(db, "after_commit", count_commit)
        db.rollback()
        db.close()
