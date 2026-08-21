import pytest


def test_sandbox_executor_requires_explicit_provider():
    from workforce.agents.execution.long_running.manager import (
        LongRunningProviderUnknown,
    )
    from workforce.agents.execution.long_running.providers.sandbox import (
        SandboxExecutor,
    )

    with pytest.raises(LongRunningProviderUnknown, match="explicit"):
        SandboxExecutor(provider_name=None)
