import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.execution.adapters.mock import MockExecutor
from app.agents.execution.artifacts import collect_and_store_artifacts
from app.agents.execution.errors import ExecutionErrorCode, ExecutionRuntimeError
from app.agents.execution.types import SandboxPolicy


@pytest.mark.asyncio
async def test_collect_artifacts_success():
    db = MagicMock()
    provider = MockExecutor()
    policy = SandboxPolicy(max_artifact_bytes=10000, max_artifact_count=5)

    sbx_id = await provider.create_workspace(policy)
    await provider.upload_file(sbx_id, "/output/result.json", b'{"status": "ok"}')

    with patch("app.agents.execution.artifacts.put_object") as mock_put:
        artifacts = await collect_and_store_artifacts(
            db=db,
            workspace_id=1,
            user_id=2,
            job_id=3,
            sandbox_id=sbx_id,
            provider=provider,
            policy=policy,
        )

    assert len(artifacts) == 1
    assert artifacts[0].name == "result.json"
    assert mock_put.called
    assert db.add.called
    assert db.commit.called


@pytest.mark.asyncio
async def test_collect_artifacts_blocks_path_traversal():
    db = MagicMock()
    provider = MockExecutor()
    policy = SandboxPolicy(max_artifact_bytes=10000, max_artifact_count=5)

    sbx_id = await provider.create_workspace(policy)
    # Mock list_outputs to return a path containing '..'
    provider.list_outputs = AsyncMock(return_value=["/output/../secret.txt"])

    with pytest.raises(ExecutionRuntimeError) as exc_info:
        await collect_and_store_artifacts(
            db=db,
            workspace_id=1,
            user_id=2,
            job_id=3,
            sandbox_id=sbx_id,
            provider=provider,
            policy=policy,
        )

    assert exc_info.value.code == ExecutionErrorCode.EXEC_ARTIFACT_INVALID_PATH
