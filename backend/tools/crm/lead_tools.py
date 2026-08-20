"""
COSA CRM & Sales Tools (Risk Level: LOW & MEDIUM)
"""
from typing import Any, Dict
from tools.base import BaseTool, RiskLevel, ToolResult


class SearchLeadsTool(BaseTool):
    id = "crm.search_leads"
    description = "Tìm kiếm khách hàng tiềm năng trong hệ thống CRM"
    risk_level = RiskLevel.LOW
    permissions_required = ["crm.read"]
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Tên, email hoặc công ty cần tìm"},
            "limit": {"type": "integer", "default": 10}
        }
    }

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        query = input_data.get("query", "")
        leads = [
            {"id": "lead_01", "name": "Nguyễn Văn A", "company": "VutaTech", "score": 85, "status": "QUALIFIED"},
            {"id": "lead_02", "name": "Trần Thị B", "company": "GlobalEdu", "score": 92, "status": "HOT"}
        ]
        return ToolResult(
            status="success",
            data={"leads": leads, "total": len(leads)},
            presenter_payload={
                "view_type": "crm_lead_summary_card",
                "title": f"Tìm thấy {len(leads)} khách hàng tiềm năng",
                "metrics": [
                    {"label": "Tổng leads", "value": len(leads)},
                    {"label": "Lead nóng", "value": 1, "trend": "hot"}
                ],
                "items": leads
            }
        )


class CreateLeadTool(BaseTool):
    id = "crm.create_lead"
    description = "Tạo mới một khách hàng tiềm năng vào CRM"
    risk_level = RiskLevel.MEDIUM
    permissions_required = ["crm.write"]
    input_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Tên liên hệ"},
            "email": {"type": "string", "description": "Email"},
            "company": {"type": "string", "description": "Tên công ty"}
        },
        "required": ["name", "email"]
    }

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        name = input_data.get("name")
        email = input_data.get("email")
        company = input_data.get("company", "N/A")
        lead_id = "lead_new_123"
        return ToolResult(
            status="success",
            data={"lead_id": lead_id, "name": name, "email": email, "company": company},
            presenter_payload={
                "view_type": "lead_created_card",
                "title": f"Đã tạo Lead: {name}",
                "company": company,
                "email": email,
                "status": "NEW"
            }
        )
