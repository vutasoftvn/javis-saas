from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.snowflake import generate_snowflake_id
from app.modules.agent_memory.claude_code_capture import capture_developer_job_completion
from app.modules.devices.models import DeveloperJob


def _job(status: str, **overrides) -> MagicMock:
    job = MagicMock(spec=DeveloperJob)
    job.id = overrides.get("id", generate_snowflake_id())
    job.title = overrides.get("title", "Implement Portfolio Impact Matrix")
    job.status = status
    job.diff_summary = overrides.get("diff_summary")
    job.test_results = overrides.get("test_results")
    job.worktree_path = overrides.get("worktree_path")
    return job


@pytest.mark.asyncio
async def test_capture_fires_for_succeeded_job():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    job = _job("SUCCEEDED", diff_summary="+ 15 lines in auth_middleware.dart")

    mock_gateway = MagicMock()
    mock_gateway.capture = AsyncMock()

    with patch("app.modules.agent_memory.claude_code_capture.get_gateway", return_value=mock_gateway):
        await capture_developer_job_completion(db, ws_id, job)

    mock_gateway.capture.assert_awaited_once()
    event = mock_gateway.capture.call_args[0][0]
    assert event["workspace_id"] == ws_id
    assert event["job_id"] == str(job.id)
    assert event["status"] == "SUCCEEDED"
    assert event["diff_summary"] == "+ 15 lines in auth_middleware.dart"


@pytest.mark.asyncio
async def test_capture_redacts_secrets_in_diff_summary():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    job = _job("SUCCEEDED", diff_summary="added OPENAI_API_KEY=sk-abcdefghijklmnopqrst1234 to .env")

    mock_gateway = MagicMock()
    mock_gateway.capture = AsyncMock()

    with patch("app.modules.agent_memory.claude_code_capture.get_gateway", return_value=mock_gateway):
        await capture_developer_job_completion(db, ws_id, job)

    event = mock_gateway.capture.call_args[0][0]
    assert "sk-abcdefghijklmnopqrst1234" not in event["diff_summary"]
    assert "[REDACTED:openai_api_key]" in event["diff_summary"]


@pytest.mark.asyncio
async def test_capture_fires_for_failed_job():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    job = _job("FAILED")

    mock_gateway = MagicMock()
    mock_gateway.capture = AsyncMock()

    with patch("app.modules.agent_memory.claude_code_capture.get_gateway", return_value=mock_gateway):
        await capture_developer_job_completion(db, ws_id, job)

    mock_gateway.capture.assert_awaited_once()


@pytest.mark.asyncio
async def test_capture_skips_non_terminal_status():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    job = _job("RUNNING")

    mock_gateway = MagicMock()
    mock_gateway.capture = AsyncMock()

    with patch("app.modules.agent_memory.claude_code_capture.get_gateway", return_value=mock_gateway):
        await capture_developer_job_completion(db, ws_id, job)

    mock_gateway.capture.assert_not_awaited()


@pytest.mark.asyncio
async def test_capture_never_raises_when_gateway_fails():
    """A memory-engine failure must never break the job-completion path
    (spec §210.16)."""
    db = MagicMock()
    ws_id = generate_snowflake_id()
    job = _job("SUCCEEDED")

    mock_gateway = MagicMock()
    mock_gateway.capture = AsyncMock(side_effect=RuntimeError("sidecar exploded"))

    with patch("app.modules.agent_memory.claude_code_capture.get_gateway", return_value=mock_gateway):
        await capture_developer_job_completion(db, ws_id, job)  # must not raise
