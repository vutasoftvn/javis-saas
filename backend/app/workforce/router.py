"""AI Workforce Domain Master Router"""
from fastapi import APIRouter

from app.workforce.chat import router as chat
from app.workforce.chat import ai_api as ai
from app.workforce.memory import router as agent_memory
from app.workforce.skills import router as skills_router
from app.workforce.ai_team import router as ai_team
from app.workforce.api.admin_api import router as admin_api
from app.workforce.automation import router as automation_router
from app.workforce.agents.router import router as agent_runtime_router
from app.workforce.agents.execution_router import router as agent_execution_router
from app.workforce.agents.approvals_router import router as agent_approvals_router
from app.workforce.agents.proposals.router import router as agent_proposals_router
from app.workforce.agents.orchestrator.router import router as agent_orchestrator_router
from app.workforce.agents.orchestration.router import router as mission_control_router
from app.workforce.runtime_router import router as runtime_router
from app.workforce.extensions.router import router as extension_router

from app.workforce.ai.programs.router import router as ai_programs_router
from app.workforce.api.cofounder_api import router as cofounder_api
from app.workforce.api.packs_api import router as packs_api

router = APIRouter()

router.include_router(cofounder_api, prefix="/api/v1")
router.include_router(packs_api, prefix="/api/v1")
router.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
router.include_router(ai.router, prefix="/api/v1/ai", tags=["ai"])
router.include_router(agent_memory.router, prefix="/api/v1/agent-memory", tags=["agent-memory"])
router.include_router(skills_router.router, prefix="/api/v1/skills", tags=["skills"])
router.include_router(ai_team.router, prefix="/api/v1/functions", tags=["ai-team"])
router.include_router(automation_router.router, prefix="/api/v1/automations", tags=["automations"])
router.include_router(admin_api, prefix="/api/v1/workforce", tags=["workforce-admin"])
router.include_router(runtime_router, prefix="/api/v1/runtime", tags=["runtime-diagnostics"])
router.include_router(ai_programs_router, prefix="/api/v1/internal/ai/programs", tags=["ai-programs-internal"])

# Agent runtime surfaces are mounted individually rather than through the
# retired gateway package.  This keeps their public contract explicit and
# lets each surface be reviewed independently as the Harness evolves.
router.include_router(agent_runtime_router, prefix="/api/v1/agents/runtime", tags=["agents-runtime"])
router.include_router(agent_execution_router, prefix="/api/v1/agents/execution", tags=["agents-execution"])
router.include_router(agent_approvals_router, prefix="/api/v1/agents/approvals", tags=["agents-approvals"])
router.include_router(agent_proposals_router, tags=["agent-proposals"])
router.include_router(agent_orchestrator_router, tags=["agent-orchestrator"])
router.include_router(mission_control_router, prefix="/api/v1/agents/mission-control", tags=["mission-control"])
router.include_router(extension_router, tags=["extensions"])


@router.get("/api/v1/agents/_meta", tags=["agents"])
def get_agent_surfaces_metadata():
    """Describe the independently mounted Agent Harness HTTP surfaces."""
    return {
        "status": "active",
        "sub_surfaces": [
            {"name": "agents_runtime", "prefix": "/api/v1/agents/runtime"},
            {"name": "agents_execution", "prefix": "/api/v1/agents/execution"},
            {"name": "agents_approvals", "prefix": "/api/v1/agents/approvals"},
            {"name": "agent_proposals", "prefix": "/api/v1/agents/proposals"},
            {"name": "orchestrator", "prefix": "/api/v1/orchestrator"},
            {"name": "mission_control", "prefix": "/api/v1/agents/mission-control"},
            {"name": "capabilities", "prefix": "/api/v1/capabilities"},
        ],
    }


