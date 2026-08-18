import os
import pytest
from unittest.mock import MagicMock

from app.workforce.agents.execution.adapters.mock import MockExecutor
from app.workforce.agents.execution.adapters.opensandbox import OpenSandboxExecutor
from app.workforce.agents.execution.policies import DEFAULT_PRESETS
from app.workforce.agents.execution.types import SandboxPolicy


@pytest.fixture
def mock_executor() -> MockExecutor:
    return MockExecutor()


@pytest.fixture
def sample_policy() -> SandboxPolicy:
    return DEFAULT_PRESETS["safe_analysis"].model_copy(deep=True)


@pytest.fixture(params=["mock", "opensandbox_mocked"])
def executor(request, mock_executor) -> MockExecutor:
    """Fixture providing executors for contract testing."""
    if request.param == "mock":
        return mock_executor
    elif request.param == "opensandbox_mocked":
        # Returns an OpenSandboxExecutor with mocked SDK for unit/contract tests
        sbx_exec = OpenSandboxExecutor(domain="http://127.0.0.1:8080", api_key="test-key")
        return sbx_exec
