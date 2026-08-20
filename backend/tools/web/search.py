"""
COSA Web Search & Fetch Tools (Risk Level: LOW)
"""
from typing import Any, Dict
from tools.base import BaseTool, RiskLevel, ToolResult


class WebSearchTool(BaseTool):
    id = "web.search"
    description = "Tìm kiếm thông tin trên internet qua các công cụ tìm kiếm"
    risk_level = RiskLevel.LOW
    permissions_required = ["web.search"]
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Từ khóa tìm kiếm"},
            "num_results": {"type": "integer", "default": 5}
        },
        "required": ["query"]
    }

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        query = input_data.get("query", "")
        # Mock search results for simulation
        results = [
            {"title": f"Kết quả 1 cho '{query}'", "url": "https://example.com/1", "snippet": "Tổng quan thị trường và đối thủ."},
            {"title": f"Báo cáo phân tích '{query}' 2026", "url": "https://example.com/2", "snippet": "Dữ liệu định cỡ thị trường SAM/SOM."}
        ]
        return ToolResult(
            status="success",
            data={"results": results, "query": query, "count": len(results)},
            presenter_payload={
                "view_type": "web_search_card",
                "title": f"Kết quả tìm kiếm: '{query}'",
                "sources_count": len(results),
                "items": results
            }
        )


class WebFetchTool(BaseTool):
    id = "web.fetch"
    description = "Trích xuất nội dung văn bản từ một URL cụ thể"
    risk_level = RiskLevel.LOW
    permissions_required = ["web.read"]
    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Đường dẫn trang web cần đọc"}
        },
        "required": ["url"]
    }

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        url = input_data.get("url", "")
        return ToolResult(
            status="success",
            data={"url": url, "content": f"Nội dung trích xuất từ {url}...", "status_code": 200},
            presenter_payload={
                "view_type": "web_page_card",
                "title": f"Trích xuất trang: {url}",
                "summary": f"Đã đọc thành công nội dung từ {url}"
            }
        )
