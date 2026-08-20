from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Any, Optional
from app.workforce.events.contracts import BaseEvent
from app.workforce.events.projections.workflow_run import WorkflowRunProjection

router = APIRouter()

@router.get("/runs/{run_id}/events", response_model=List[Any])
async def get_run_events(run_id: str, after_cursor: Optional[int] = Query(None)) -> Any:
    """
    Lấy danh sách event của một run, hỗ trợ cursor (after_cursor).
    Sử dụng để reconnect và rebuild state ở client (Hologram/Run Inspector).
    """
    return []

@router.get("/runs/{run_id}/projection", response_model=WorkflowRunProjection)
async def get_run_projection(run_id: str) -> Any:
    """
    Lấy state của run đã được backend project sẵn từ chuỗi event.
    """
    # Placeholder
    raise HTTPException(status_code=404, detail="Run not found")
