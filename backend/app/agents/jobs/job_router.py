"""Job Router for COSA Agents.

Binds Gate decisions, Scope sets, and Domain Skills into structured AgentRuns and Plans.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.agents.context.scope_resolver import ScopeResolver, ScopeSet
from app.agents.control_plane.models import AgentGoal, AgentPlan
from app.agents.governance.models import AgentRun
from app.agents.skills_library.resolver import SkillManifest, SkillResolver
from app.core.protected_resources import service as protected_resource_service
from app.core.snowflake import generate_snowflake_id
from app.modules.chat.conversation_gate import GateDecision

logger = logging.getLogger(__name__)


def route_to_job(
    db: Session,
    workspace_id: int,
    user_id: int,
    gate_decision: Optional[GateDecision] = None,
    job_type: str = "general_work",
    domain: str = "founder",
    project_id: Optional[int] = None,
    agent_key: str = "orchestrator",
    payload: Optional[dict] = None,
    title: Optional[str] = None,
) -> dict[str, Any]:
    """Resolve scope and skills, bind effective prompt revision, and instantiate an AgentRun."""
    now = datetime.now(timezone.utc)

    # 1. Resolve Scope
    scope = ScopeResolver.resolve(
        workspace_id=workspace_id,
        gate_decision=gate_decision,
        project_id=project_id,
        job_type=job_type,
        domain=domain,
    )

    # 2. Resolve Skill Manifest
    skill = SkillResolver.resolve(job_type=job_type, domain=domain)
    skills_data = []
    if skill:
        skills_data.append({
            "name": skill.name,
            "domain": skill.domain,
            "required_context": skill.required_context,
            "tool_permissions": skill.tool_permissions,
        })

    # 3. Read effective prompt revision for the agent
    prompt_res = protected_resource_service.get_effective(
        db=db,
        workspace_id=workspace_id,
        resource_type="agent_prompt",
        resource_key=f"agent:{agent_key}:system_prompt",
    )

    # 4. Instantiate AgentRun
    run_id = generate_snowflake_id()
    run = AgentRun(
        id=run_id,
        workspace_id=workspace_id,
        user_id=user_id,
        agent_key=agent_key,
        job_type=job_type,
        project_id=project_id,
        status="created",
        permission_profile="read_only",
        started_at=now,
        metadata_jsonb={
            "job_type": job_type,
            "domain": domain,
            "bound_scope": {
                "workspace_id": scope.workspace_id,
                "project_id": scope.project_id,
                "token_budget": scope.token_budget,
                "needs_heavy_priming": scope.needs_heavy_priming,
                "allowed_namespaces": list(scope.allowed_namespaces),
            },
            "skills": [s["name"] for s in skills_data],
            "bound_prompt_revision": prompt_res.get("system_prompt", ""),
            "payload": payload or {},
        },
    )
    db.add(run)

    # 5. Create Goal & Plan
    goal_id = generate_snowflake_id()
    goal = AgentGoal(
        id=goal_id,
        workspace_id=workspace_id,
        user_id=user_id,
        goal_type=f"{domain}_goal",
        title=title or f"Job {job_type}",
        status="active",
        created_at=now,
        updated_at=now,
    )
    db.add(goal)

    plan_id = generate_snowflake_id()
    plan = AgentPlan(
        id=plan_id,
        goal_id=goal_id,
        workspace_id=workspace_id,
        user_id=user_id,
        title=f"Plan for {title or job_type}",
        skills_jsonb=skills_data,
        status="draft",
        version=1,
        created_at=now,
        updated_at=now,
    )
    db.add(plan)

    db.commit()
    db.refresh(run)

    return {
        "run_id": str(run.id),
        "goal_id": str(goal.id),
        "plan_id": str(plan.id),
        "status": run.status,
        "job_type": run.job_type,
        "domain": domain,
        "skills": [s["name"] for s in skills_data],
        "scope": {
            "token_budget": scope.token_budget,
            "needs_heavy_priming": scope.needs_heavy_priming,
            "allowed_namespaces": list(scope.allowed_namespaces),
        },
    }
