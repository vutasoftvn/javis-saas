from app.workforce.agents.execution.long_running.providers.device import DeviceWorkProvider


class CodexDeviceExecutor(DeviceWorkProvider):
    executor_kind = "codex"
    required_capabilities = ("codex", "git")
