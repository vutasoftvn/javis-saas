"""
COSA Task Executors Package
"""
from executors.base import BaseExecutor, BuildSpec, ExecutorResult
from executors.claude_code_executor import ClaudeCodeExecutor, N8nAutomationExecutor
from executors.registry import (
    ExecutorRegistry,
    executor_registry,
    register_all_standard_executors,
)
from executors.sandboxed_shell_executor import SandboxedShellExecutor

__all__ = [
    "BaseExecutor",
    "BuildSpec",
    "ClaudeCodeExecutor",
    "ExecutorRegistry",
    "ExecutorResult",
    "N8nAutomationExecutor",
    "SandboxedShellExecutor",
    "executor_registry",
    "register_all_standard_executors",
]
