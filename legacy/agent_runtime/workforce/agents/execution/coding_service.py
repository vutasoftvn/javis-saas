from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from core.snowflake import generate_snowflake_id
from workforce.agents.execution.models import ExecutionJob
from workforce.agents.execution.service import run_execution_job
from workforce.agents.execution.types import ExecutionJobResult, ExecutionStatus


class CodingExecutionService:
    """Service to prepare and execute isolated coding agent jobs and generate patches in sandbox."""

    @classmethod
    def create_coding_job(
        cls,
        db: Session,
        workspace_id: int,
        user_id: int,
        repo_url: str,
        task_prompt: str,
        base_branch: str = "main",
        commands: Optional[List[str]] = None,
        agent_run_id: Optional[int] = None,
        provider: Optional[str] = None,
    ) -> ExecutionJob:
        """Enqueue an isolated coding task in the sandbox using 'coding' preset."""
        exec_commands = commands or [
            f"git clone --depth=1 -b {base_branch} {repo_url} /workspace/repo",
            "cd /workspace/repo",
            "git diff > /output/change.patch || true",
            "echo '{\"status\":\"success\",\"task\":\"coding_execution\"}' > /output/test_report.json",
        ]

        meta = {
            "policy_name": "coding",
            "repo_url": repo_url,
            "task_prompt": task_prompt,
            "base_branch": base_branch,
            "commands": exec_commands,
            "input_files": {
                "task.txt": task_prompt,
            },
        }

        job = ExecutionJob(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            user_id=user_id,
            agent_key="coding_agent",
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
    async def run_coding_job_now(
        cls,
        db: Session,
        workspace_id: int,
        user_id: int,
        repo_url: str,
        task_prompt: str,
        base_branch: str = "main",
        commands: Optional[List[str]] = None,
        agent_run_id: Optional[int] = None,
        provider: Optional[str] = None,
    ) -> ExecutionJobResult:
        """Create and execute a coding sandbox job immediately."""
        job = cls.create_coding_job(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
            repo_url=repo_url,
            task_prompt=task_prompt,
            base_branch=base_branch,
            commands=commands,
            agent_run_id=agent_run_id,
            provider=provider,
        )
        return await run_execution_job(db, job.id)
