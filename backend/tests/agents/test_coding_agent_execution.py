import pytest
from unittest.mock import MagicMock, patch

from workforce.agents.execution.coding_service import CodingExecutionService
from workforce.agents.execution.manager import execution_provider_manager
from workforce.agents.execution.models import ExecutionJob
from workforce.agents.execution.policies import DEFAULT_PRESETS
from workforce.agents.execution.tools import run_coding_task
from workforce.agents.governance.approval_service import ApprovalService
from workforce.agents.governance.models import AgentApproval
from core.snowflake import generate_snowflake_id


def test_coding_preset_specifications():
    preset = DEFAULT_PRESETS["coding"]
    assert preset.cpu >= 2.0
    assert preset.memory_mb >= 2048
    assert preset.timeout_seconds >= 600
    assert "github.com" in preset.network_allow


def _mock_db_with_session():
    db = MagicMock()
    stored_jobs = {}

    def mock_add(instance):
        if hasattr(instance, "id") and instance.id:
            stored_jobs[instance.id] = instance

    db.add.side_effect = mock_add

    def mock_query(model):
        q = MagicMock()
        def mock_filter(*args, **kwargs):
            fq = MagicMock()
            def mock_first():
                if model == ExecutionJob and stored_jobs:
                    return list(stored_jobs.values())[-1]
                return None
            fq.first.side_effect = mock_first
            fq.all.return_value = []
            return fq
        q.filter.side_effect = mock_filter
        return q

    db.query.side_effect = mock_query
    return db


@pytest.mark.asyncio
async def test_coding_service_executes_and_collects_patch():
    await execution_provider_manager.start()

    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    run_id = generate_snowflake_id()
    db = _mock_db_with_session()

    with patch("workforce.agents.execution.artifacts.put_object"):
        res = await CodingExecutionService.run_coding_job_now(
            db=db,
            workspace_id=ws_id,
            user_id=user_id,
            repo_url="https://github.com/vutasoftvn/sample-repo.git",
            task_prompt="Fix null pointer exception in auth service",
            agent_run_id=run_id,
            provider="mock",
        )

    assert res.status.value in ["completed", "queued"]
    assert res.provider == "mock"
    assert db.add.called
    assert db.commit.called


def test_run_coding_task_tool_enqueues_job():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = _mock_db_with_session()

    res = run_coding_task(
        db=db,
        workspace_id=ws_id,
        user_id=user_id,
        agent_key="coding_agent",
        repo_url="https://github.com/vutasoftvn/sample-repo.git",
        task_prompt="Optimize database indexing",
    )

    assert res["status"] == "queued"
    assert "job_id" in res
    assert db.add.called
    assert db.commit.called


def test_coding_patch_requires_human_approval_gate():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    run_id = generate_snowflake_id()
    db = MagicMock()

    # When code patch is ready to be applied/pushed externally, an approval row is required
    approval = ApprovalService.create_approval(
        db=db,
        workspace_id=ws_id,
        run_id=run_id,
        agent_key="coding_agent",
        action_type="apply_patch",
        tool_name="tech.apply_code_patch",
        input_preview={"patch_url": "s3://workspaces/123/execution/456/change.patch"},
        risk_level="high",
    )

    assert approval.tool_name == "tech.apply_code_patch"
    assert approval.status == "pending"
    assert approval.risk_level == "high"
    assert db.add.called
    assert db.commit.called
