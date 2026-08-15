import pytest
from unittest.mock import MagicMock, patch

from app.agents.execution.policies import DEFAULT_PRESETS, load_policy
from app.agents.execution.tools import run_browser_research
from app.core.feature_flags import FLAG_AGENT_EXECUTION_BROWSER
from app.core.snowflake import generate_snowflake_id


def test_research_policy_preset_configuration():
    research = DEFAULT_PRESETS["research"]
    assert "playwright" in research.image or "python" in research.image
    assert research.network_default == "allow" or len(research.network_allow) > 0
    assert research.cpu >= 1.0
    assert research.memory_mb >= 1024


def test_run_browser_research_tool_enqueues_job():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = MagicMock()

    res = run_browser_research(
        db=db,
        workspace_id=ws_id,
        user_id=user_id,
        agent_key="researcher",
        script_content="import urllib.request\nprint('crawling data')",
        target_urls=["https://wikipedia.org"],
    )

    assert res["status"] == "queued"
    assert "job_id" in res
    assert db.add.called
    assert db.commit.called
