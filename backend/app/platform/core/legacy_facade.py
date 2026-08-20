from fastapi import APIRouter, Depends, Response
from typing import Any
import warnings

# This router acts as a compatibility layer for old endpoints
router = APIRouter()

@router.post("/legacy/agent/run")
async def legacy_agent_run(response: Response, payload: dict) -> dict:
    """
    [DEPRECATED] Sử dụng /v1/workflows/run thay thế.
    Facade này chỉ forward request sang canonical service.
    """
    # Thêm headers deprecation theo chuẩn HTTP
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "Thu, 31 Dec 2026 23:59:59 GMT"
    response.headers["Link"] = '<https://api.javis.com/v1/workflows/run>; rel="replacement"'
    
    # Ghi log structured warning event
    warnings.warn(
        "Endpoint /legacy/agent/run is deprecated and will be removed. "
        "Use /v1/workflows/run instead.",
        DeprecationWarning
    )
    
    # Forward logic to canonical service (mocked here)
    return {"status": "forwarded_to_canonical", "run_id": "new_run_123"}
