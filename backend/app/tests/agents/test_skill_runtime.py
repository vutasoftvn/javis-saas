import pytest
from unittest.mock import MagicMock, patch
from pydantic import ValidationError

from app.workforce.agents.execution.errors import ExecutionErrorCode, ExecutionRuntimeError
from app.workforce.agents.execution.manager import execution_provider_manager
from app.workforce.agents.execution.models import ExecutionJob
from app.workforce.agents.execution.skills.manifest import (
    SkillManifest,
    SkillPermissions,
    SkillResources,
    validate_manifest_to_policy,
)
from app.workforce.agents.execution.skills.runtime_service import SkillRuntimeService
from app.workforce.agents.execution.tools import run_skill
from app.core.snowflake import generate_snowflake_id


def test_valid_skill_manifest_to_policy():
    manifest = SkillManifest(
        name="custom_lead_scorer",
        version="1.2.0",
        description="Scores incoming leads using statistical model",
        runtime="python:3.11-slim",
        entrypoint="score_leads.py",
        permissions=SkillPermissions(
            network=["api.hunter.io", "api.clearbit.com"],
            credentials=["openrouter"],
        ),
        resources=SkillResources(
            cpu=1.5,
            memory_mb=1024,
            timeout_seconds=120,
        ),
    )

    policy = validate_manifest_to_policy(manifest)
    assert policy.name == "skill_custom_lead_scorer"
    assert policy.cpu == 1.5
    assert policy.memory_mb == 1024
    assert policy.network_default == "deny"
    assert "api.hunter.io" in policy.network_allow
    assert "openrouter" in policy.credentials_allow


@pytest.mark.parametrize("bad_host", [
    "localhost",
    "127.0.0.1",
    "169.254.169.254",
    "10.0.1.5",
    "192.168.1.100",
    "172.16.0.1",
    "0.0.0.0",
])
def test_skill_manifest_blocks_forbidden_network_destinations(bad_host: str):
    manifest = SkillManifest(
        name="malicious_probe",
        entrypoint="probe.py",
        permissions=SkillPermissions(network=[bad_host]),
    )

    with pytest.raises(ExecutionRuntimeError) as exc_info:
        validate_manifest_to_policy(manifest)

    assert exc_info.value.code == ExecutionErrorCode.EXEC_POLICY_VIOLATION


def test_skill_manifest_rejects_excessive_resources():
    with pytest.raises(ValidationError):
        SkillResources(cpu=4.0)  # Max allowed is 2.0

    with pytest.raises(ValidationError):
        SkillResources(memory_mb=4096)  # Max allowed is 2048 MB

    with pytest.raises(ValidationError):
        SkillResources(timeout_seconds=1200)  # Max allowed is 600s


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
async def test_skill_runtime_executes_isolated_skill():
    await execution_provider_manager.start()

    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    run_id = generate_snowflake_id()
    db = _mock_db_with_session()

    manifest = SkillManifest(
        name="sentiment_analyzer",
        entrypoint="main.py",
        permissions=SkillPermissions(),
        resources=SkillResources(cpu=1.0, memory_mb=512, timeout_seconds=60),
    )

    script_files = {
        "main.py": "print('Skill sentiment analysis complete.')\n"
    }

    with patch("app.workforce.agents.execution.artifacts.put_object"):
        res = await SkillRuntimeService.execute_skill_now(
            db=db,
            workspace_id=ws_id,
            user_id=user_id,
            manifest=manifest,
            script_files=script_files,
            input_payload={"text": "Excellent customer response time"},
            agent_run_id=run_id,
            provider="mock",
        )

    assert res.status.value in ["completed", "queued"]
    assert res.provider == "mock"
    assert db.add.called
    assert db.commit.called


def test_run_skill_tool_enqueues_job():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = _mock_db_with_session()

    manifest_dict = {
        "name": "data_cleaner",
        "entrypoint": "clean.py",
        "permissions": {"network": ["api.github.com"]},
        "resources": {"cpu": 1.0, "memory_mb": 512, "timeout_seconds": 60},
    }

    res = run_skill(
        db=db,
        workspace_id=ws_id,
        user_id=user_id,
        agent_key="generic",
        manifest_dict=manifest_dict,
        script_files={"clean.py": "print('cleaned')"},
        input_payload={"records": 100},
    )

    assert res["status"] == "queued"
    assert "job_id" in res
    assert db.add.called
    assert db.commit.called
