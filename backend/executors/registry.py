"""
COSA Central Task Executor Registry
Quản lý đăng ký và tra cứu các hạ tầng thực thi ngoài (Structure.md Mục 7, 31).
"""
from typing import Dict, List, Optional
from executors.base import BaseExecutor
from executors.claude_code_executor import ClaudeCodeExecutor, N8nAutomationExecutor
from executors.sandboxed_shell_executor import SandboxedShellExecutor


class ExecutorRegistry:
    """Kho quản lý danh mục Task Executors của COSA"""

    def __init__(self):
        self._executors: Dict[str, BaseExecutor] = {}

    def register(self, executor: BaseExecutor) -> None:
        """Đăng ký một Executor vào hệ thống"""
        self._executors[executor.id] = executor

    def get(self, executor_id: str) -> Optional[BaseExecutor]:
        """Truy xuất Executor theo ID"""
        return self._executors.get(executor_id)

    def list_executors(self) -> List[BaseExecutor]:
        """Lấy danh sách tất cả Executors"""
        return list(self._executors.values())


# Singleton instance
executor_registry = ExecutorRegistry()

def register_all_standard_executors(registry: ExecutorRegistry = executor_registry) -> None:
    standard = [
        ClaudeCodeExecutor(),
        SandboxedShellExecutor(),
        N8nAutomationExecutor(),
    ]
    for e in standard:
        registry.register(e)


register_all_standard_executors()
