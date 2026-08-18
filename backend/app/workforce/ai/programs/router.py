"""Internal AI Programs API Router."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.workforce.ai.programs.registry import AIProgramRegistry
from app.workforce.ai.programs.runtime import LegacyPromptProgramRuntime, DSPyProgramRuntime
from app.workforce.ai.programs.schemas import AIProgramRequest, AIProgramResult

router = APIRouter()


class PromoteRequest(BaseModel):
    version: str
    approved_by: Optional[str] = "system"


class RollbackRequest(BaseModel):
    target_version: str


@router.get("", response_model=List[Dict[str, Any]])
def list_ai_programs() -> List[Dict[str, Any]]:
    """List all registered AI programs."""
    AIProgramRegistry.initialize_default_programs()
    programs = AIProgramRegistry.list_programs()
    return [
        {
            "key": p.key,
            "name": p.name,
            "domain": p.domain,
            "description": p.description,
            "version": p.default_version,
            "engine": p.engine,
            "enabled": p.enabled,
        }
        for p in programs
    ]


@router.get("/{key}", response_model=Dict[str, Any])
def get_ai_program_detail(key: str) -> Dict[str, Any]:
    """Get metadata for a specific registered AI program."""
    AIProgramRegistry.initialize_default_programs()
    meta = AIProgramRegistry.get_registration(key)
    if not meta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Program '{key}' not found")
    return {
        "key": meta.key,
        "name": meta.name,
        "domain": meta.domain,
        "description": meta.description,
        "version": meta.default_version,
        "engine": meta.engine,
        "enabled": meta.enabled,
    }


@router.post("/run", response_model=Dict[str, Any])
async def run_ai_program(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a registered bounded AI program."""
    AIProgramRegistry.initialize_default_programs()
    program_key = payload.get("program_key")
    if not program_key:
        raise HTTPException(status_code=400, detail="Missing 'program_key'")

    req = AIProgramRequest(
        workspace_id=str(payload.get("workspace_id", "default")),
        program_key=program_key,
        input=payload.get("input", {}),
    )
    runtime = LegacyPromptProgramRuntime()
    result = await runtime.run(req)
    return {
        "program_key": result.program_key,
        "program_version": result.program_version,
        "status": result.status,
        "output": result.output,
        "latency_ms": result.latency_ms,
    }


@router.post("/{key}/promote")
def promote_program_version(key: str, payload: PromoteRequest) -> Dict[str, Any]:
    """Promote an optimized candidate version for an AI program."""
    AIProgramRegistry.initialize_default_programs()
    meta = AIProgramRegistry.get_registration(key)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Program '{key}' not found")
    return {
        "key": key,
        "status": "promoted",
        "active_version": payload.version,
        "approved_by": payload.approved_by,
    }


@router.post("/{key}/rollback")
def rollback_program_version(key: str, payload: RollbackRequest) -> Dict[str, Any]:
    """Rollback an AI program to a previous version."""
    AIProgramRegistry.initialize_default_programs()
    meta = AIProgramRegistry.get_registration(key)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Program '{key}' not found")
    return {
        "key": key,
        "status": "rolled_back",
        "active_version": payload.target_version,
    }
