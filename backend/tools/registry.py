"""
COSA Central Tool Registry Implementation
Quản lý đăng ký, tra cứu và xuất JSON Schema cho LLM Function Calling (Structure.md Mục 10).
"""
from typing import Any, Dict, List, Optional
from tools.base import BaseTool, RiskLevel


class ToolRegistry:
    """Kho lưu trữ và quản lý công cụ tập trung của COSA"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Đăng ký một công cụ vào hệ thống"""
        self._tools[tool.id] = tool

    def get(self, tool_id: str) -> Optional[BaseTool]:
        """Truy xuất công cụ theo mã định danh duy nhất"""
        return self._tools.get(tool_id)

    def list_tools(self, domain: Optional[str] = None) -> List[BaseTool]:
        """Lấy danh sách công cụ (có thể lọc theo domain prefix ví dụ: 'web', 'crm')"""
        if not domain:
            return list(self._tools.values())
        return [t for t in self._tools.values() if t.id.startswith(f"{domain}.")]

    def export_schemas_for_model(self, allowed_tool_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Xuất danh sách công cụ thành định dạng chuẩn JSON Schema cho LLM Function Calling"""
        schemas = []
        target_tools = (
            [self._tools[tid] for tid in allowed_tool_ids if tid in self._tools]
            if allowed_tool_ids is not None
            else self._tools.values()
        )

        for tool in target_tools:
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.id,
                    "description": tool.description,
                    "parameters": tool.input_schema or {"type": "object", "properties": {}},
                }
            })
        return schemas


# Singleton instance
tool_registry = ToolRegistry()
