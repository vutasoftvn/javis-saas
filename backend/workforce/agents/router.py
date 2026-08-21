from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from workforce.agents.runtime.errors import AgentRuntimeError
from workforce.agents.runtime.manager import agent_runtime_manager
from workforce.agents.runtime.types import (
    AgentRunRequest,
    AgentRunResult,
    RuntimeHealth,
)
from core.auth import get_current_workspace_member
from core.feature_flags import FLAG_AGENT_RUNTIME_DEEPSEEK, is_enabled
from db.models import WorkspaceMember
from db.session import get_db

router = APIRouter()


@router.get("/health", response_model=RuntimeHealth)
async def get_runtime_health(
    runtime_name: Optional[str] = Query(None, description="Runtime name to check (e.g. mock, deepseek_harness)"),
) -> RuntimeHealth:
    """Get the health and readiness status of the specified AgentRuntime."""
    runtime = agent_runtime_manager.get_runtime(runtime_name)
    return await runtime.health()


@router.post("/run", response_model=AgentRunResult)
async def execute_agent_run(
    request: AgentRunRequest,
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
) -> AgentRunResult:
    """Execute an agent task via configured AgentRuntime under workspace tenant isolation."""
    workspace_id = current_member.workspace_id
    company_id = str(getattr(current_member, "company_id", workspace_id))

    # Tenant scoping enforcement
    if str(request.workspace_id) != str(workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Workspace mismatch",
        )

    target_runtime_name = request.context.get("runtime_name", "mock")

    # If deepseek harness runtime is requested, check workspace feature flag
    if target_runtime_name == "deepseek_harness":
        if not is_enabled(db, FLAG_AGENT_RUNTIME_DEEPSEEK, workspace_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"DeepSeek Harness runtime is disabled for workspace {workspace_id}",
            )

    runtime = agent_runtime_manager.get_runtime(target_runtime_name)

    try:
        result = await runtime.run(request)
        return result
    except AgentRuntimeError as err:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if err.code == "AGENT_RUNTIME_UNAVAILABLE":
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif err.code == "AGENT_RUNTIME_TIMEOUT":
            status_code = status.HTTP_504_GATEWAY_TIMEOUT
        elif err.code in ("AGENT_POLICY_DENIED", "AGENT_APPROVAL_REQUIRED"):
            status_code = status.HTTP_403_FORBIDDEN
        elif err.code == "AGENT_CONTEXT_ERROR":
            status_code = status.HTTP_400_BAD_REQUEST

        raise HTTPException(
            status_code=status_code,
            detail=err.to_dict(),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "AGENT_UNKNOWN_ERROR",
                "message": f"Unexpected runtime error: {exc}",
                "retryable": False,
            },
        )
