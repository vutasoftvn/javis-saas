import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy.orm import Session
from workforce.tools.invocation.dispatchers import NativeDispatcher
from workforce.tools.invocation.contracts import ToolInvocationRequest
from core.tool_registry import ToolSpec
from workforce.agents.runtime.execution_scope import ExecutionScope

def sync_tool(workspace_id: int, arg: str):
    return f"sync {workspace_id} {arg}"

async def async_tool(workspace_id: int, arg: str):
    return f"async {workspace_id} {arg}"

@pytest.fixture
def dummy_request():
    scope = ExecutionScope(
        workspace_id=42,
        company_id=1,
        principal_user_id=1,
        principal_member_id=1,
        principal_role="owner",
        operating_unit_id=None,
        offering_id=None,
        initiative_id=None,
        profile_id=None,
        session_id=None,
        grants=()
    )
    return ToolInvocationRequest(
        scope=scope,
        tool_flat_name="test_tool",
        arguments={"arg": "hello"},
        source="chat"
    )

@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)

@pytest.mark.asyncio
async def test_native_dispatcher_sync(dummy_request, mock_db):
    spec = ToolSpec(namespace="test", name="tool", callable=sync_tool)
    dispatcher = NativeDispatcher()
    
    # Execution should inject workspace_id from scope, and map other parameters
    result = await dispatcher.dispatch(mock_db, dummy_request, spec, {"arg": "hello"})
    
    assert result == "sync 42 hello"

@pytest.mark.asyncio
async def test_native_dispatcher_async(dummy_request, mock_db):
    spec = ToolSpec(namespace="test", name="tool", callable=async_tool)
    dispatcher = NativeDispatcher()
    
    result = await dispatcher.dispatch(mock_db, dummy_request, spec, {"arg": "hello"})
    
    assert result == "async 42 hello"

@pytest.mark.asyncio
async def test_native_dispatcher_cancellation(dummy_request, mock_db):
    async def slow_tool():
        await asyncio.sleep(2)
        return "done"
        
    spec = ToolSpec(namespace="test", name="tool", callable=slow_tool, timeout_seconds=1)
    dispatcher = NativeDispatcher()
    
    with pytest.raises(asyncio.TimeoutError):
        await dispatcher.dispatch(mock_db, dummy_request, spec, {})
