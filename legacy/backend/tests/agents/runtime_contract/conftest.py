import os
import pytest
from workforce.agents.runtime.adapters.mock import MockRuntime
from workforce.agents.runtime.adapters.deepseek_harness import DeepSeekHarnessAdapter
from workforce.agents.runtime.types import AgentRunRequest
from core.snowflake import generate_snowflake_str

# Live DeepSeek Harness runs need a real DEEPSEEK_API_KEY and real network egress.
# CI must stay green without either (MockRuntime is the default test path per the
# adjustment plan), so tests that need a genuine completed run are skipped unless a
# real key is present in the environment. With no real key, DeepSeekHarnessAdapter is
# still exercised for its no-key/no-SDK error paths (see test_runtime_crash.py).
DSH_LIVE_AVAILABLE = bool(os.environ.get("DEEPSEEK_API_KEY", "").strip())
skip_without_dsh_live = pytest.mark.skipif(
    not DSH_LIVE_AVAILABLE,
    reason="requires a real DEEPSEEK_API_KEY for a live DeepSeek Harness run",
)


@pytest.fixture
def mock_runtime() -> MockRuntime:
    return MockRuntime()


@pytest.fixture
def dsh_runtime() -> DeepSeekHarnessAdapter:
    return DeepSeekHarnessAdapter(api_key=os.environ.get("DEEPSEEK_API_KEY") or "test_sandbox_key")


@pytest.fixture
def sample_request() -> AgentRunRequest:
    return AgentRunRequest(
        company_id=generate_snowflake_str(),
        workspace_id=generate_snowflake_str(),
        user_id=generate_snowflake_str(),
        agent_key="runtime_test_agent",
        task="Evaluate new inbound lead from website contact form",
        context={"source": "unit_test"},
        permission_profile="read_only",
        timeout_seconds=5,
    )
