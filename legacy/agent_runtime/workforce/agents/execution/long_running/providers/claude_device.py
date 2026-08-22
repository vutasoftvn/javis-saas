from workforce.agents.execution.long_running.providers.device import DeviceWorkProvider


class ClaudeDeviceExecutor(DeviceWorkProvider):
    executor_kind = "claude"
    required_capabilities = ("claude_code", "git")
