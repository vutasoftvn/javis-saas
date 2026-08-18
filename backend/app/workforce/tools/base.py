from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.workforce.identity.context import ExecutionContext


class BaseToolAdapter(ABC):
    """Lớp giao diện cơ sở cho tất cả các loại Tool Transport (Local, MCP, A2A, n8n, Sandbox)."""

    @abstractmethod
    async def execute(self, context: ExecutionContext, tool_key: str, args: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Thực thi công cụ với context định danh và tham số đầu vào."""
        pass
