"""
Market Analysis Workflow Definition
"""
from workflows.base import WorkflowDefinition, WorkflowStep, WorkflowStepType


def get_market_analysis_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        id="wf-market-analysis",
        name="Quy trình Phân tích Thị trường & Đối thủ",
        domain="marketing",
        description="Áp dụng kiến thức định vị, chạy song song tìm kiếm web và sinh báo cáo đối thủ",
        steps=[
            WorkflowStep(
                id="step_skill",
                name="Nạp tri thức Market Research",
                type=WorkflowStepType.SKILL,
                target="market-research"
            ),
            WorkflowStep(
                id="step_parallel_search",
                name="Tìm kiếm và trích xuất dữ liệu đối thủ",
                type=WorkflowStepType.PARALLEL_TOOLS,
                target="web.search,web.fetch",
                params={"query": "B2B SaaS Vietnam Competitors", "url": "https://example.com/market-report"}
            ),
            WorkflowStep(
                id="step_save_artifact",
                name="Tạo file báo cáo định vị",
                type=WorkflowStepType.TOOL,
                target="filesystem.write",
                params={"file_path": "docs/reports/market_analysis.md", "content": "# Báo cáo phân tích đối thủ\n..."}
            )
        ]
    )
