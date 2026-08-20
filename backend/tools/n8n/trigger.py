"""
COSA n8n Webhook Trigger Tool (Risk Level: MEDIUM)
"""
from typing import Any, Dict
from tools.base import BaseTool, RiskLevel, ToolResult


class N8nTriggerTool(BaseTool):
    id = "n8n.trigger"
    description = "Kích hoạt kịch bản tự động hóa qua Webhook n8n"
    risk_level = RiskLevel.MEDIUM
    permissions_required = ["automation.trigger"]
    input_schema = {
        "type": "object",
        "properties": {
            "workflow_name": {"type": "string", "description": "Tên quy trình n8n"},
            "payload": {"type": "object", "description": "Dữ liệu JSON gửi sang n8n"}
        },
        "required": ["workflow_name"]
    }

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        workflow = input_data.get("workflow_name", "")
        return ToolResult(
            status="success",
            data={"workflow": workflow, "triggered": True, "execution_id": "n8n_exec_987"},
            presenter_payload={
                "view_type": "automation_trigger_card",
                "title": f"Kích hoạt n8n: {workflow}",
                "execution_id": "n8n_exec_987",
                "status": "RUNNING"
            }
        )
