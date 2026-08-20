"""
COSA Knowledge Search Tools (Risk Level: LOW)
"""
from typing import Any, Dict
from tools.base import BaseTool, RiskLevel, ToolResult


class KnowledgeSearchTool(BaseTool):
    id = "knowledge.search"
    description = "Tìm kiếm tài liệu và quy chuẩn tri thức nội bộ"
    risk_level = RiskLevel.LOW
    permissions_required = ["knowledge.read"]
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Nội dung cần tra cứu tri thức"}
        },
        "required": ["query"]
    }

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        query = input_data.get("query", "")
        results = [
            {"title": "Cẩm nang Chiến lược Doanh nghiệp", "path": "knowledge/strategy/handbook.md", "snippet": "Định hướng phát triển 12 tuần."},
            {"title": "Quy chuẩn Kế toán TT58", "path": "knowledge/finance/tt58.md", "snippet": "Quy tắc định khoản và phân bổ chi phí."}
        ]
        return ToolResult(
            status="success",
            data={"results": results, "query": query},
            presenter_payload={
                "view_type": "knowledge_doc_card",
                "title": f"Tri thức: '{query}'",
                "items": results
            }
        )
