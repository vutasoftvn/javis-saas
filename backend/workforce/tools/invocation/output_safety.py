import json
import dataclasses
from datetime import datetime
from pydantic import BaseModel
from typing import Any

from core.tool_registry import ToolSpec
from workforce.tools.invocation.contracts import ToolInvocationResult

def _serialize(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    elif dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    elif isinstance(obj, (dict, list, str, int, float, bool, type(None))):
        return obj
    else:
        # Fallback for other objects, trying to get dict or string representation
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return str(obj)

def format_output(
    spec: ToolSpec, 
    raw_output: Any, 
    correlation_id: str, 
    started_at: datetime, 
    finished_at: datetime
) -> ToolInvocationResult:
    
    serialized = _serialize(raw_output)
    
    # If ToolSpec defines an output_schema, we could validate it here.
    # Currently we just enforce the return contract.
    
    latency_ms = int((finished_at - started_at).total_seconds() * 1000)
    
    return ToolInvocationResult(
        correlation_id=correlation_id,
        status="success",
        output=serialized,
        started_at=started_at,
        finished_at=finished_at,
        latency_ms=latency_ms
    )
