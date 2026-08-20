import asyncio
from sqlalchemy.orm import Session
from typing import Any, Dict
import inspect

from app.core.tool_registry import ToolSpec
from app.workforce.tools.invocation.contracts import ToolInvocationRequest

class NativeDispatcher:
    async def dispatch(self, db: Session, request: ToolInvocationRequest, spec: ToolSpec, sanitized_args: Dict[str, Any]) -> Any:
        # Dependency Injection mappings
        kwargs = dict(sanitized_args)
        
        # Inject known context parameters if the tool requires them
        sig = inspect.signature(spec.callable)
        params = sig.parameters
        
        if "db" in params:
            kwargs["db"] = db
        if "workspace_id" in params:
            kwargs["workspace_id"] = int(request.scope.workspace_id)
        if "user_id" in params and request.scope.principal_user_id is not None:
            kwargs["user_id"] = int(request.scope.principal_user_id)
        if "agent_key" in params:
            kwargs["agent_key"] = f"system_invocation_{request.source}"
        if "chat_session_id" in params:
            kwargs["chat_session_id"] = request.chat_session_id
            
        # Execute (with optional timeout)
        timeout = spec.timeout_seconds if spec.timeout_seconds else None
        
        if inspect.iscoroutinefunction(spec.callable):
            if timeout:
                return await asyncio.wait_for(spec.callable(**kwargs), timeout=timeout)
            return await spec.callable(**kwargs)
        else:
            # Run sync in threadpool
            def run_sync():
                return spec.callable(**kwargs)
            
            if timeout:
                # To properly timeout a thread, we use asyncio.to_thread wrapped in wait_for
                return await asyncio.wait_for(asyncio.to_thread(run_sync), timeout=timeout)
            return await asyncio.to_thread(run_sync)
