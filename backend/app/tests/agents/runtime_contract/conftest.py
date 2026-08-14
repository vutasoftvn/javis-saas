import pytest
from app.agents.runtime.adapters.mock import MockRuntime
from app.agents.runtime.adapters.deepseek_harness import DeepSeekHarnessAdapter
from app.agents.runtime.types import AgentRunRequest
from app.core.snowflake import generate_snowflake_str


@pytest.fixture
def mock_runtime() -> MockRuntime:
    return MockRuntime()


@pytest.fixture
def dsh_runtime() -> DeepSeekHarnessAdapter:
    return DeepSeekHarnessAdapter(api_key="test_sandbox_key")


@pytest.fixture
def sample_request() -> AgentRunRequest:
    return AgentRunRequest(
        company_id=generate_snowflake_str(),
        workspace_id=generate_snowflake_str(),
        user_id=generate_snowflake_str(),
        agent_key="sales_lead_qualifier",
        task="Evaluate new inbound lead from website contact form",
        context={"source": "unit_test"},
        permission_profile="read_only",
        timeout_seconds=5,
    )
