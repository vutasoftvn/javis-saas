"""AI Workforce Domain Master Router"""
from fastapi import APIRouter

from app.workforce.chat import router as chat
from app.workforce.chat import ai_api as ai
from app.workforce.memory import router as agent_memory
from app.workforce.skills import router as skills_router
from app.workforce.ai_team import router as ai_team
from app.workforce.api.admin_api import router as admin_api
from app.workforce.automation import router as automations_router
from app.workforce.runtime_router import router as runtime_router

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
router.include_router(automations_router.router, prefix="/api/v1/automations", tags=["automations"])
router.include_router(admin_api, prefix="/api/v1/agent-platform", tags=["agent-platform"])
router.include_router(admin_api, prefix="/api/v1/workforce", tags=["workforce-admin"])
router.include_router(runtime_router, prefix="/api/v1/runtime", tags=["runtime-diagnostics"])
router.include_router(ai_programs_router, prefix="/api/v1/internal/ai/programs", tags=["ai-programs-internal"])



