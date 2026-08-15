"""Unified Agent Gateway Router.

Consolidates all 7 agent sub-surfaces into a unified gateway with identical route paths
and zero breaking changes for API consumers.
"""

from fastapi import APIRouter

from app.agents.router import router as agents_runtime_router
from app.agents.execution_router import router as agents_execution_router
from app.agents.approvals_router import router as agents_approvals_router
from app.agents.control_plane.router_api import router as agentic_control_plane_router
from app.agents.proposals.router import router as agent_proposals_router
from app.agents.orchestrator.router import router as orchestrator_router
from app.agents.orchestration.router import router as mission_control_router
from app.agents.capabilities.router import router as capabilities_router

router = APIRouter()

# 1. Mount the sub-surfaces with exact existing prefixes and tags
router.include_router(agents_runtime_router, prefix="/api/v1/agents/runtime", tags=["agents-runtime"])
router.include_router(agents_execution_router, prefix="/api/v1/agents/execution", tags=["agents-execution"])
router.include_router(agents_approvals_router, prefix="/api/v1/agents/approvals", tags=["agents-approvals"])
router.include_router(agentic_control_plane_router, prefix="/api/v1/agent", tags=["agentic-control-plane"])
router.include_router(agent_proposals_router, tags=["agent-proposals"])
router.include_router(orchestrator_router, tags=["orchestrator"])
router.include_router(mission_control_router, prefix="/api/v1/agents/mission-control", tags=["mission-control"])
router.include_router(capabilities_router, prefix="/api/v1/capabilities", tags=["agents-capabilities"])


@router.get("/api/v1/agents/_meta", tags=["agents-gateway"])
def get_agents_meta():
    """Returns overview metadata for all unified agent sub-surfaces."""
    return {
        "status": "active",
        "sub_surfaces": [
            {
                "name": "agents_runtime",
                "prefix": "/api/v1/agents/runtime",
                "description": "Agent runtime and tool execution bridge",
            },
            {
                "name": "agents_execution",
                "prefix": "/api/v1/agents/execution",
                "description": "Sandbox and asynchronous execution jobs",
            },
            {
                "name": "agents_approvals",
                "prefix": "/api/v1/agents/approvals",
                "description": "Human-in-the-loop governance approval management",
            },
            {
                "name": "agentic_control_plane",
                "prefix": "/api/v1/agent",
                "description": "Goals, decomposition planning, execution, and evaluation",
            },
            {
                "name": "agent_proposals",
                "prefix": "/api/v1/agents/proposals",
                "description": "Strategic proposals and change management",
            },
            {
                "name": "orchestrator",
                "prefix": "/api/v1/orchestrator",
                "description": "Deterministic command execution router",
            },
            {
                "name": "mission_control",
                "prefix": "/api/v1/agents/mission-control",
                "description": "Chief-of-Staff reasoning and multi-agent coordination",
            },
            {
                "name": "capabilities",
                "prefix": "/api/v1/capabilities",
                "description": "Capability Gateway authorization, grants, catalog, and execution",
            },
        ],
    }

