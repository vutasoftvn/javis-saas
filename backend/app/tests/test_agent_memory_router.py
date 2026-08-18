from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.snowflake import generate_snowflake_id
from app.workforce.memory.health import UNAVAILABLE
from app.workforce.memory.router import get_memory_health, get_memory_status, get_task_context


def _member(workspace_id):
    m = MagicMock()
    m.workspace_id = workspace_id
    return m


def test_get_memory_status_cross_tenant_forbidden():
    member = _member(workspace_id=generate_snowflake_id())
    other_workspace_id = generate_snowflake_id()
    db = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        get_memory_status(workspace_id=other_workspace_id, member=member, db=db)

    assert exc_info.value.status_code == 403


def test_get_memory_status_reflects_flag_state():
    ws_id = generate_snowflake_id()
    member = _member(workspace_id=ws_id)
    db = MagicMock()

    with patch("app.workforce.memory.router.is_enabled", return_value=False):
        result = get_memory_status(workspace_id=ws_id, member=member, db=db)

    assert result == {"enabled": False}


@pytest.mark.asyncio
async def test_get_memory_health_reports_sidecar_status():
    result = await get_memory_health()

    # No sidecar running in this dev environment (by design) - real assertion
    # is that the endpoint itself doesn't raise and returns the expected shape.
    assert result["status"] == UNAVAILABLE
    assert result["backend"] == "tencentdb_agent_memory"
    assert "latency_ms" in result
    assert "last_error" in result


@pytest.mark.asyncio
async def test_get_task_context_cross_tenant_forbidden():
    member = _member(workspace_id=generate_snowflake_id())
    other_workspace_id = generate_snowflake_id()
    db = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await get_task_context(job_id="123", workspace_id=other_workspace_id, member=member, db=db)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_task_context_returns_gateway_result():
    ws_id = generate_snowflake_id()
    member = _member(workspace_id=ws_id)
    db = MagicMock()

    mock_gateway = MagicMock()
    mock_gateway.get_task_context = AsyncMock(return_value={"status": "SUCCEEDED", "files_changed": 3})

    with patch("app.workforce.memory.router.get_gateway", return_value=mock_gateway):
        result = await get_task_context(job_id="job-123", workspace_id=ws_id, member=member, db=db)

    mock_gateway.get_task_context.assert_awaited_once_with("job-123")
    assert result == {"job_id": "job-123", "context": {"status": "SUCCEEDED", "files_changed": 3}}


@pytest.mark.asyncio
async def test_get_task_context_returns_null_context_when_unavailable():
    """Flag off / sidecar unreachable -> null context, not an error - callers
    should treat this as "no prior context available"."""
    ws_id = generate_snowflake_id()
    member = _member(workspace_id=ws_id)
    db = MagicMock()

    with patch("app.workforce.memory.service.is_enabled", return_value=False):
        result = await get_task_context(job_id="job-999", workspace_id=ws_id, member=member, db=db)

    assert result == {"job_id": "job-999", "context": None}
