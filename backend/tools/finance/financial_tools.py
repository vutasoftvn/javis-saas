"""
COSA Financial Tools (P&L, TT58 & Runway)
"""
from typing import Any, Dict
from tools.base import BaseTool, RiskLevel, ToolResult


class QueryPnLTool(BaseTool):
    id = "finance.query_pnl"
    description = "Tra cứu báo cáo kết quả hoạt động kinh doanh (P&L) theo Thông tư 58"
    risk_level = RiskLevel.LOW
    permissions_required = ["finance.read"]
    input_schema = {
        "type": "object",
        "properties": {
            "quarter": {"type": "string", "description": "Quý cần tra cứu (ví dụ: Q1-2026)"}
        }
    }

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        quarter = input_data.get("quarter", "Q1-2026")
        data = {
            "period": quarter,
            "revenue": 250000000,
            "cogs": 50000000,
            "gross_profit": 200000000,
            "operating_expenses": 120000000,
            "net_profit": 80000000,
            "margin_percentage": 32.0
        }
        return ToolResult(
            status="success",
            data=data,
            presenter_payload={
                "view_type": "pnl_statement_card",
                "title": f"Báo cáo P&L ({quarter})",
                "metrics": [
                    {"label": "Doanh thu", "value": "250,000,000 đ", "trend": "positive"},
                    {"label": "Lợi nhuận ròng", "value": "80,000,000 đ", "trend": "positive"},
                    {"label": "Biên lợi nhuận", "value": "32.0%", "trend": "positive"}
                ]
            }
        )


class CalculateRunwayTool(BaseTool):
    id = "finance.calculate_runway"
    description = "Tính toán số tháng còn lại của dòng tiền (Cash Runway)"
    risk_level = RiskLevel.LOW
    permissions_required = ["finance.read"]
    input_schema = {
        "type": "object",
        "properties": {
            "cash_balance": {"type": "number", "description": "Số dư tiền mặt hiện tại"},
            "monthly_burn_rate": {"type": "number", "description": "Tốc độ đốt tiền hàng tháng"}
        },
        "required": ["cash_balance", "monthly_burn_rate"]
    }

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        cash = input_data.get("cash_balance", 1200000000)
        burn = input_data.get("monthly_burn_rate", 100000000)
        runway_months = cash / burn if burn > 0 else 999.0

        return ToolResult(
            status="success",
            data={"cash_balance": cash, "burn_rate": burn, "runway_months": runway_months},
            presenter_payload={
                "view_type": "runway_gauge_card",
                "title": "Chỉ số Cash Runway",
                "runway_months": round(runway_months, 1),
                "status": "HEALTHY" if runway_months >= 12 else "WARNING"
            }
        )
