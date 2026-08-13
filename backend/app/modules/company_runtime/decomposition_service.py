from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.modules.strategy.models import WeeklyCommitment
from app.modules.tasks.models import Task
from app.modules.outcomes.models import Outcome
from app.modules.company_runtime.contract_service import WorkContractService
from app.modules.company_runtime.dependency_service import DependencyService


class DecompositionService:
    """Decomposes a Weekly Mission into coordinated Task + Outcome pairs linked by a DAG."""

    @classmethod
    def decompose_weekly_mission(
        cls,
        db: Session,
        workspace_id: int,
        weekly_commitment_id: int,
        user_id: int,
    ) -> Dict[str, Any]:
        commitment = (
            db.query(WeeklyCommitment)
            .filter(
                WeeklyCommitment.id == weekly_commitment_id,
                WeeklyCommitment.workspace_id == workspace_id,
            )
            .first()
        )
        if not commitment:
            raise ValueError(f"WeeklyCommitment {weekly_commitment_id} not found in workspace {workspace_id}")

        mission_title = commitment.title

        # Function blueprints
        blueprints = [
            {
                "function": "LEGAL",
                "title": f"Legal readiness & terms review for '{mission_title}'",
                "desired_result": "Approved privacy policy, user terms, and compliance signoff",
                "review_type": "EXPERT_REVIEW",
                "execution_mode": "HYBRID",
            },
            {
                "function": "TECH",
                "title": f"Deploy core components & landing for '{mission_title}'",
                "desired_result": "Working staging/production deployment and automated test pass",
                "review_type": "DETERMINISTIC_VALIDATION",
                "execution_mode": "AGENT",
            },
            {
                "function": "MARKETING",
                "title": f"Launch campaign & messaging for '{mission_title}'",
                "desired_result": "Targeted campaign copy and distribution materials published",
                "review_type": "COSA_REVIEW",
                "execution_mode": "AGENT",
            },
            {
                "function": "SALES",
                "title": f"Outreach & lead qualification for '{mission_title}'",
                "desired_result": "Target prospect list contacted and qualified responses gathered",
                "review_type": "FUNCTION_LEAD_REVIEW",
                "execution_mode": "HUMAN",
            },
            {
                "function": "FINANCE",
                "title": f"Receivable & budget reconciliation for '{mission_title}'",
                "desired_result": "Budget aligned, invoices issued, and transactions accounted",
                "review_type": "DETERMINISTIC_VALIDATION",
                "execution_mode": "AGENT",
            },
        ]

        created_tasks: Dict[str, Task] = {}
        created_outcomes: Dict[str, Outcome] = {}

        for bp in blueprints:
            fn = bp["function"]
            # 1. Create Task
            task = Task(
                id=generate_snowflake_id(),
                workspace_id=workspace_id,
                weekly_commitment_id=weekly_commitment_id,
                title=bp["title"],
                function=fn,
                execution_mode=bp["execution_mode"],
                status="todo",
                priority="high" if fn in {"LEGAL", "TECH"} else "medium",
                created_at=datetime.utcnow(),
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            created_tasks[fn] = task

            # 2. Create Outcome
            outcome = Outcome(
                id=generate_snowflake_id(),
                workspace_id=workspace_id,
                task_id=task.id,
                function=fn,
                title=f"Outcome: {bp['title']}",
                desired_result=bp["desired_result"],
                review_type=bp["review_type"],
                requested_by=user_id,
                status="planning",
                created_at=datetime.utcnow(),
            )
            db.add(outcome)
            db.commit()
            db.refresh(outcome)
            created_outcomes[fn] = outcome

        # 3. Wire DAG Dependencies
        # Marketing depends on Legal
        DependencyService.add_dependency(
            db=db,
            task_id=created_tasks["MARKETING"].id,
            depends_on_task_id=created_tasks["LEGAL"].id,
            dependency_type="REQUIRES_APPROVAL",
        )
        # Marketing depends on Tech
        DependencyService.add_dependency(
            db=db,
            task_id=created_tasks["MARKETING"].id,
            depends_on_task_id=created_tasks["TECH"].id,
            dependency_type="REQUIRES_OUTPUT",
        )
        # Sales depends on Marketing
        DependencyService.add_dependency(
            db=db,
            task_id=created_tasks["SALES"].id,
            depends_on_task_id=created_tasks["MARKETING"].id,
            dependency_type="BLOCKS",
        )
        # Finance depends on Sales
        DependencyService.add_dependency(
            db=db,
            task_id=created_tasks["FINANCE"].id,
            depends_on_task_id=created_tasks["SALES"].id,
            dependency_type="REQUIRES_DOCUMENT",
        )

        return {
            "mission_id": str(weekly_commitment_id),
            "mission_title": mission_title,
            "tasks_created": [
                {"id": str(t.id), "function": t.function, "title": t.title}
                for t in created_tasks.values()
            ],
            "outcomes_created": [
                {"id": str(o.id), "function": o.function, "title": o.title}
                for o in created_outcomes.values()
            ],
            "dag_edges_count": 4,
        }
