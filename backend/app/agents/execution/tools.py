from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.feature_flags import (
    FLAG_AGENT_EXECUTION,
    FLAG_AGENT_EXECUTION_BROWSER,
    FLAG_AGENT_EXECUTION_CODING,
    FLAG_AGENT_EXECUTION_SKILLS,
)
from app.core.snowflake import generate_snowflake_id
from app.core.tool_registry import register
from app.agents.execution.models import ExecutionJob
from app.agents.execution.types import ExecutionStatus


@register(
    namespace="execution",
    name="run_python",
    flag_key=FLAG_AGENT_EXECUTION,
    chat_schema=None,  # Intentionally null: Chat LLM cannot trigger sandbox directly
    risk_level="medium",
    permission_level="scoped_write",
    idempotency=False,
    allowed_agent_keys=[
        "sales_data_agent",
        "data_analyst",
        "researcher",
        "chief_of_staff",
        "coding_agent",
        "developer",
    ],
)
def run_python(
    db: Session,
    workspace_id: int,
    user_id: int,
    agent_key: str,
    commands: List[str],
    policy_name: str = "safe_analysis",
    input_files: Optional[Dict[str, str]] = None,
    agent_run_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Enqueue an isolated Python execution job in the sandbox."""
    meta = {
        "commands": commands,
        "policy_name": policy_name,
        "input_files": input_files or {},
    }

    job = ExecutionJob(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        user_id=user_id,
        agent_key=agent_key,
        agent_run_id=agent_run_id,
        status=ExecutionStatus.QUEUED.value,
        metadata_jsonb=meta,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return {
        "status": "queued",
        "job_id": str(job.id),
        "workspace_id": workspace_id,
    }


@register(
    namespace="execution",
    name="run_browser_research",
    flag_key=FLAG_AGENT_EXECUTION_BROWSER,
    chat_schema=None,
    risk_level="medium",
    permission_level="scoped_write",
    idempotency=False,
    allowed_agent_keys=["researcher", "data_analyst", "chief_of_staff"],
)
def run_browser_research(
    db: Session,
    workspace_id: int,
    user_id: int,
    agent_key: str,
    script_content: str,
    target_urls: Optional[List[str]] = None,
    agent_run_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Enqueue an isolated browser research job in the sandbox using research policy."""
    meta = {
        "commands": ["python /input/research_script.py"],
        "policy_name": "research",
        "input_files": {
            "research_script.py": script_content,
        },
        "target_urls": target_urls or [],
    }

    job = ExecutionJob(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        user_id=user_id,
        agent_key=agent_key,
        agent_run_id=agent_run_id,
        status=ExecutionStatus.QUEUED.value,
        metadata_jsonb=meta,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return {
        "status": "queued",
        "job_id": str(job.id),
        "workspace_id": workspace_id,
    }


@register(
    namespace="execution",
    name="run_coding_task",
    flag_key=FLAG_AGENT_EXECUTION_CODING,
    chat_schema=None,
    risk_level="high",
    permission_level="scoped_write",
    idempotency=False,
    allowed_agent_keys=["coding_agent", "developer", "chief_of_staff"],
)
def run_coding_task(
    db: Session,
    workspace_id: int,
    user_id: int,
    agent_key: str,
    repo_url: str,
    task_prompt: str,
    base_branch: str = "main",
    agent_run_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Enqueue an isolated coding and patch generation task in sandbox."""
    from app.agents.execution.coding_service import CodingExecutionService

    job = CodingExecutionService.create_coding_job(
        db=db,
        workspace_id=workspace_id,
        user_id=user_id,
        repo_url=repo_url,
        task_prompt=task_prompt,
        base_branch=base_branch,
        agent_run_id=agent_run_id,
    )
    return {
        "status": "queued",
        "job_id": str(job.id),
        "workspace_id": workspace_id,
    }


@register(
    namespace="execution",
    name="run_skill",
    flag_key=FLAG_AGENT_EXECUTION_SKILLS,
    chat_schema=None,
    risk_level="high",
    permission_level="scoped_write",
    idempotency=False,
    allowed_agent_keys=["generic", "chief_of_staff", "developer", "data_analyst"],
)
def run_skill(
    db: Session,
    workspace_id: int,
    user_id: int,
    agent_key: str,
    manifest_dict: Dict[str, Any],
    script_files: Dict[str, str],
    input_payload: Optional[Dict[str, Any]] = None,
    agent_run_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Enqueue an isolated skill execution task in sandbox."""
    from app.agents.execution.skills.manifest import SkillManifest
    from app.agents.execution.skills.runtime_service import SkillRuntimeService

    manifest = SkillManifest.model_validate(manifest_dict)
    job = SkillRuntimeService.create_skill_job(
        db=db,
        workspace_id=workspace_id,
        user_id=user_id,
        manifest=manifest,
        script_files=script_files,
        input_payload=input_payload,
        agent_key=agent_key,
        agent_run_id=agent_run_id,
    )
    return {
        "status": "queued",
        "job_id": str(job.id),
        "workspace_id": workspace_id,
    }
