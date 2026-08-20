"""
COSA Sandboxed Shell Execution Tool (Risk Level: HIGH - Bắt buộc Founder duyệt)
"""
from typing import Any, Dict
from tools.base import BaseTool, RiskLevel, ToolResult


class SandboxedShellTool(BaseTool):
    id = "shell.execute"
    description = "Thực thi câu lệnh terminal trong Workspace (BẮT BUỘC duyệt trước khi chạy)"
    risk_level = RiskLevel.HIGH
    permissions_required = ["shell.execute"]
    input_schema = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Câu lệnh bash/zsh cần thực thi"}
        },
        "required": ["command"]
    }

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        command = input_data.get("command", "")
        # Mock execution after approval
        return ToolResult(
            status="success",
            data={"command": command, "stdout": f"Executed: {command}\nSuccess", "exit_code": 0},
            presenter_payload={
                "view_type": "terminal_output_card",
                "title": f"Lệnh: {command}",
                "exit_code": 0,
                "output": f"Executed: {command}\nSuccess"
            }
        )
