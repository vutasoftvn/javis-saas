import json
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.agents.execution.models import ExecutionJob
from app.agents.execution.service import run_execution_job
from app.agents.execution.skills.manifest import SkillManifest, validate_manifest_to_policy
from app.agents.execution.types import ExecutionJobResult, ExecutionStatus
from app.core.snowflake import generate_snowflake_id


class SkillRuntimeService:
    """Service to prepare, validate, and execute isolated custom & third-party skills in sandboxes."""

    @classmethod
    def create_skill_job(
        cls,
        db: Session,
        workspace_id: int,
        user_id: int,
        manifest: SkillManifest,
        script_files: Dict[str, str],
        input_payload: Optional[Dict[str, Any]] = None,
        agent_key: str = "generic",
        agent_run_id: Optional[int] = None,
        provider: Optional[str] = None,
    ) -> ExecutionJob:
        """Validate skill manifest, generate safe policy, and enqueue execution job."""
        policy = validate_manifest_to_policy(manifest)

        commands = manifest.commands or [
            f"python /input/{manifest.entrypoint}" if manifest.entrypoint.endswith(".py") else f"node /input/{manifest.entrypoint}"
        ]

        files_to_upload: Dict[str, str] = dict(script_files)
        if input_payload is not None:
            files_to_upload["input_data.json"] = json.dumps(input_payload)

        meta = {
            "policy_name": policy.name,
            "custom_policy": policy.model_dump(),
            "skill_name": manifest.name,
            "skill_version": manifest.version,
            "commands": commands,
            "input_files": files_to_upload,
            "requested_credentials": manifest.permissions.credentials,
        }

        job = ExecutionJob(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            user_id=user_id,
            agent_key=agent_key,
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
    async def execute_skill_now(
        cls,
        db: Session,
        workspace_id: int,
        user_id: int,
        manifest: SkillManifest,
        script_files: Dict[str, str],
        input_payload: Optional[Dict[str, Any]] = None,
        agent_key: str = "generic",
        agent_run_id: Optional[int] = None,
        provider: Optional[str] = None,
    ) -> ExecutionJobResult:
        """Create and run an isolated skill execution job immediately."""
        job = cls.create_skill_job(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
            manifest=manifest,
            script_files=script_files,
            input_payload=input_payload,
            agent_key=agent_key,
            agent_run_id=agent_run_id,
            provider=provider,
        )
        return await run_execution_job(db, job.id)
