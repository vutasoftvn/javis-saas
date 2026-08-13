from unittest.mock import MagicMock
from datetime import datetime, date
from decimal import Decimal
import pytest

from app.core.snowflake import generate_snowflake_id
from app.modules.company_runtime.runtime_manager import CompanyRuntimeManager
from app.modules.company_runtime.decomposition_service import DecompositionService
from app.modules.company_runtime.blocker_router import BlockerRouter
from app.modules.company_runtime.review_service import ReviewService
from app.modules.company_runtime.checkpoint_service import CheckpointService
from app.modules.company_runtime.handoff_service import HandoffService
from app.modules.company_runtime.models import Blocker, NeedsYouItem, WorkReview, Handoff, RuntimeCheckpoint
from app.modules.strategy.models import WeeklyCommitment
from app.modules.tasks.models import Task, TaskDependency
from app.modules.outcomes.models import Outcome
from app.modules.finance.domain.exception_engine import detect_exceptions


def test_golden_scenario_1_beta_launch_decomposition():
    """Golden Scenario 1: Prepare Beta Launch decomposes into 5 functions with wired DAG dependencies."""
    db = MagicMock()
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    mission_id = generate_snowflake_id()

    commitment = WeeklyCommitment(id=mission_id, workspace_id=ws_id, title="Prepare beta launch", status="todo")
    db.query.return_value.filter.return_value.first.return_value = commitment
    db.query.return_value.all.return_value = []

    res = DecompositionService.decompose_weekly_mission(
        db=db,
        workspace_id=ws_id,
        weekly_commitment_id=mission_id,
        user_id=user_id,
    )

    assert len(res["tasks_created"]) == 5
    assert len(res["outcomes_created"]) == 5
    assert res["dag_edges_count"] == 4


def test_golden_scenario_2_finance_exception_wiring():
    """Golden Scenario 2: Transaction missing source document generates Blocker and surfaces in Needs You."""
    db = MagicMock()
    ws_id = generate_snowflake_id()

    tx_data = {
        "transaction_date": date(2026, 8, 13),
        "description": "Server hosting monthly fee",
        "amount": Decimal("150.00"),
        "direction": "OUT",
        "category": "Software",
        "document_id": None,  # Missing document
    }

    exceptions = detect_exceptions(tx_data, today=date(2026, 8, 13))
    assert any(e["type"] == "MISSING_DOCUMENT" for e in exceptions)

    # Trigger Blocker creation
    blocker = BlockerRouter.create_blocker(
        db=db,
        workspace_id=ws_id,
        blocker_type="MISSING_DOCUMENT",
        description="Missing invoice receipt for server hosting fee",
        assigned_function="FINANCE",
    )
    assert blocker.assigned_function == "FINANCE"
    assert db.add.called
    assert db.commit.called


def test_golden_scenario_3_marketing_rework_loop():
    """Golden Scenario 3: Marketing copy review rejection triggers REWORK_REQUIRED and increments count."""
    db = MagicMock()
    ws_id = generate_snowflake_id()
    task_id = generate_snowflake_id()
    outcome_id = generate_snowflake_id()

    task = Task(id=task_id, workspace_id=ws_id, title="Launch campaign copy", status="waiting_approval")
    outcome = Outcome(id=outcome_id, workspace_id=ws_id, task_id=task_id, title="Campaign Copy", desired_result="Published Copy", status="running", rework_count=0)

    db.query.return_value.filter.return_value.first.side_effect = [outcome, task]

    # Rework requested
    review = ReviewService.create_review(
        db=db,
        workspace_id=ws_id,
        outcome_id=outcome_id,
        reviewer_type="COSA_REVIEW",
        result="REWORK_REQUIRED",
        feedback="CTA does not support current KR target",
    )

    assert review.result == "REWORK_REQUIRED"
    assert outcome.rework_count == 1
    assert task.status == "in_progress"


def test_golden_scenario_4_runtime_resume():
    """Golden Scenario 4: Desktop sleep/restart reconciles state from checkpoint without duplicate work."""
    db = MagicMock()
    ws_id = generate_snowflake_id()

    task = Task(id=generate_snowflake_id(), workspace_id=ws_id, title="Active Claude Code Task", status="in_progress")
    ckpt = RuntimeCheckpoint(id=generate_snowflake_id(), workspace_id=ws_id, sequence=1, checkpoint_reason="DEVICE_SLEEP")

    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = ckpt
    db.query.return_value.filter.return_value.all.return_value = [task]
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.count.return_value = 0

    resume_summary = CheckpointService.resume(db, ws_id)
    assert resume_summary["status"] == "resumed"
    assert resume_summary["checkpoint_id"] == str(ckpt.id)
    assert resume_summary["reconciled_tasks_count"] == 1


def test_golden_scenario_5_cross_function_blocker_and_handoff():
    """Golden Scenario 5: Sales requires pricing from Finance, creating a cross-function handoff."""
    db = MagicMock()
    ws_id = generate_snowflake_id()

    handoff = HandoffService.create_handoff(
        db=db,
        workspace_id=ws_id,
        from_function="SALES",
        to_function="FINANCE",
        handoff_type="REQUEST_INPUT",
        requested_action="Provide custom enterprise pricing margin for customer deal",
    )

    assert handoff.from_function == "SALES"
    assert handoff.to_function == "FINANCE"
    assert handoff.status == "PENDING"
