"""Internal API endpoints for AI Intelligence Programs, Evaluation, and Optimization."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.ai.programs.schemas import AIProgramRequest, AIProgramResult
from app.ai.programs.registry import AIProgramRegistry, ProgramRegistration
from app.ai.service import ai_program_service
from app.ai.evaluation.evaluators import AIProgramEvaluator
from app.ai.evaluation.metrics import ProgramEvaluationResult
from app.ai.optimization.gepa import (
    GEPAOptimizationConfig,
    GEPAOptimizationResult,
    GEPAOptimizerRunner,
)

router = APIRouter(tags=["ai-programs"])


class EvalRunRequest(BaseModel):
    program_key: str
    workspace_id: str = "eval_workspace"
    cases: List[Dict[str, Any]]


class GEPAOptimizationApiRequest(BaseModel):
    program_key: str
    base_version: str = "1.0.0"
    target_version: str = "1.1.0"
    model_policy: str = "fast_reasoning"
    train_cases: List[Dict[str, Any]] = []
    val_cases: List[Dict[str, Any]] = []


class VersionPromotionRequest(BaseModel):
    version: str
    approved_by: str = "admin"


class VersionRollbackRequest(BaseModel):
    target_version: str


@router.post("/programs/run", response_model=AIProgramResult)
async def run_ai_program(request: AIProgramRequest) -> AIProgramResult:
    """Execute a registered bounded AI program."""
    return await ai_program_service.run_program(request)


@router.get("/programs", response_model=List[ProgramRegistration])
def list_ai_programs() -> List[ProgramRegistration]:
    """List all registered AI programs and their metadata."""
    return AIProgramRegistry.list_programs()


@router.get("/programs/{key:path}", response_model=ProgramRegistration)
def get_ai_program(key: str) -> ProgramRegistration:
    """Get metadata for a specific AI program."""
    reg = AIProgramRegistry.get_registration(key)
    if not reg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Program key '{key}' not found in registry.",
        )
    return reg


@router.post("/evals/run", response_model=ProgramEvaluationResult)
async def run_evaluation(request: EvalRunRequest) -> ProgramEvaluationResult:
    """Run offline evaluation batch on a test dataset."""
    evaluator = AIProgramEvaluator()
    return await evaluator.evaluate_dataset(
        program_key=request.program_key,
        cases=request.cases,
        workspace_id=request.workspace_id,
    )


@router.post("/optimizers/gepa/run", response_model=GEPAOptimizationResult)
async def run_gepa_optimization(
    request: GEPAOptimizationApiRequest,
) -> GEPAOptimizationResult:
    """Trigger an offline GEPA optimization pass."""
    runner = GEPAOptimizerRunner()
    config = GEPAOptimizationConfig(
        program_key=request.program_key,
        base_version=request.base_version,
        target_version=request.target_version,
        model_policy=request.model_policy,
    )
    return await runner.run_optimization(
        config=config,
        train_cases=request.train_cases,
        val_cases=request.val_cases,
    )


@router.post("/programs/{key:path}/promote")
def promote_program_version(key: str, request: VersionPromotionRequest) -> Dict[str, Any]:
    """Promote an optimized candidate program version to active."""
    reg = AIProgramRegistry.get_registration(key)
    if not reg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Program '{key}' not found.",
        )
    reg.default_version = request.version
    return {
        "status": "promoted",
        "program_key": key,
        "active_version": request.version,
        "approved_by": request.approved_by,
    }


@router.post("/programs/{key:path}/rollback")
def rollback_program_version(key: str, request: VersionRollbackRequest) -> Dict[str, Any]:
    """Rollback an active program version to a previous stable version."""
    reg = AIProgramRegistry.get_registration(key)
    if not reg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Program '{key}' not found.",
        )
    reg.default_version = request.target_version
    return {
        "status": "rolled_back",
        "program_key": key,
        "active_version": request.target_version,
    }
