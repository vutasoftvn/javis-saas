from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from core.snowflake import generate_snowflake_id
from workforce.agents.execution.models import ExecutionJob
from workforce.agents.execution.service import run_execution_job
from workforce.agents.execution.templates import get_finance_analysis_script, get_sales_analysis_script
from workforce.agents.execution.types import ExecutionJobResult, ExecutionStatus


class DomainAnalysisService:
    """Service to prepare and execute domain-specific data analysis jobs in sandboxes."""

    @classmethod
    def create_sales_analysis_job(
        cls,
        db: Session,
        workspace_id: int,
        user_id: int,
        csv_content: str,
        agent_run_id: Optional[int] = None,
        provider: Optional[str] = None,
    ) -> ExecutionJob:
        """Enqueue a Sales CSV data analysis job in an isolated sandbox."""
        meta = {
            "policy_name": "safe_analysis",
            "commands": ["python /input/analyze_sales.py"],
            "input_files": {
                "sales.csv": csv_content,
                "analyze_sales.py": get_sales_analysis_script(),
            },
        }

        job = ExecutionJob(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            user_id=user_id,
            agent_key="sales_data_agent",
            agent_run_id=agent_run_id,
            provider=provider or "mock",
            status=ExecutionStatus.QUEUED.value,
            metadata_jsonb=meta,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @classmethod
    def create_finance_analysis_job(
        cls,
        db: Session,
        workspace_id: int,
        user_id: int,
        csv_content: str,
        agent_run_id: Optional[int] = None,
        provider: Optional[str] = None,
    ) -> ExecutionJob:
        """Enqueue a Finance CSV data analysis job in an isolated sandbox."""
        meta = {
            "policy_name": "safe_analysis",
            "commands": ["python /input/analyze_finance.py"],
            "input_files": {
                "finance.csv": csv_content,
                "analyze_finance.py": get_finance_analysis_script(),
            },
        }

        job = ExecutionJob(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            user_id=user_id,
            agent_key="finance_data_agent",
            agent_run_id=agent_run_id,
            provider=provider or "mock",
            status=ExecutionStatus.QUEUED.value,
            metadata_jsonb=meta,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @classmethod
    async def run_sales_analysis_now(
        cls,
        db: Session,
        workspace_id: int,
        user_id: int,
        csv_content: str,
        agent_run_id: Optional[int] = None,
        provider: Optional[str] = None,
    ) -> ExecutionJobResult:
        """Create and run a Sales CSV data analysis job immediately."""
        job = cls.create_sales_analysis_job(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
            csv_content=csv_content,
            agent_run_id=agent_run_id,
            provider=provider,
        )
        return await run_execution_job(db, job.id)

    @classmethod
    async def run_finance_analysis_now(
        cls,
        db: Session,
        workspace_id: int,
        user_id: int,
        csv_content: str,
        agent_run_id: Optional[int] = None,
        provider: Optional[str] = None,
    ) -> ExecutionJobResult:
        """Create and run a Finance CSV data analysis job immediately."""
        job = cls.create_finance_analysis_job(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
            csv_content=csv_content,
            agent_run_id=agent_run_id,
            provider=provider,
        )
        return await run_execution_job(db, job.id)
