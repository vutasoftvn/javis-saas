"""Founder OS Domain Master Router"""
from fastapi import APIRouter

from app.founder_os.strategy import router as strategy
from app.founder_os.strategy import okrs_router as okrs
from app.founder_os.strategy import execution_router as execution
from app.founder_os.strategy import portfolio_router as portfolios
from app.founder_os.strategy import next_action_router as next_actions
from app.founder_os.tasks import router as tasks
from app.founder_os.tasks import agents_router as agents
from app.founder_os.outcomes.router import router as outcomes_router
from app.founder_os.workspace.router import router as workspace_router

router = APIRouter()

router.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
router.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
router.include_router(strategy.router, prefix="/api/v1/strategy", tags=["strategy"])
router.include_router(okrs.router, prefix="/api/v1/okrs", tags=["okrs"])
router.include_router(execution.router, prefix="/api/v1/execution", tags=["execution"])
router.include_router(portfolios.router, prefix="/api/v1/portfolios", tags=["portfolios"])
router.include_router(next_actions.router, prefix="/api/v1/next-actions", tags=["next-actions"])
router.include_router(outcomes_router, prefix="/api/v1/outcomes", tags=["outcomes"])
router.include_router(workspace_router, prefix="/api/v1/workspace", tags=["workspace"])

