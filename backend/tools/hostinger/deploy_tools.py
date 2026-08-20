"""
COSA Deployment Tools (Risk Level: HIGH & CRITICAL - Bắt buộc phê duyệt)
"""
from typing import Any, Dict
from tools.base import BaseTool, RiskLevel, ToolResult


class DeployStagingTool(BaseTool):
    id = "deployment.deploy_staging"
    description = "Triển khai mã nguồn lên môi trường kiểm thử Staging (Risk: HIGH)"
    risk_level = RiskLevel.HIGH
    permissions_required = ["deployment.staging"]
    input_schema = {
        "type": "object",
        "properties": {
            "branch": {"type": "string", "default": "main"}
        }
    }

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        branch = input_data.get("branch", "main")
        return ToolResult(
            status="success",
            data={"environment": "staging", "branch": branch, "deployed": True},
            presenter_payload={
                "view_type": "deployment_status_card",
                "title": f"Triển khai Staging thành công ({branch})",
                "environment": "STAGING",
                "status": "HEALTHY",
                "url": "https://staging.cosa.ai"
            }
        )


class DeployProductionTool(BaseTool):
    id = "deployment.deploy_production"
    description = "Triển khai mã nguồn lên môi trường Production (Risk: CRITICAL - Phê duyệt 2 lớp)"
    risk_level = RiskLevel.CRITICAL
    permissions_required = ["deployment.production"]
    input_schema = {
        "type": "object",
        "properties": {
            "version_tag": {"type": "string", "description": "Phiên bản release (e.g., v1.2.0)"}
        },
        "required": ["version_tag"]
    }

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        tag = input_data.get("version_tag", "v1.0.0")
        return ToolResult(
            status="success",
            data={"environment": "production", "version": tag, "deployed": True},
            presenter_payload={
                "view_type": "deployment_status_card",
                "title": f"Triển khai Production thành công ({tag})",
                "environment": "PRODUCTION",
                "status": "LIVE",
                "url": "https://cosa.ai"
            }
        )
