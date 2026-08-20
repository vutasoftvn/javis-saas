"""
Financial Health & Staging Deployment Workflows
"""
from workflows.base import WorkflowDefinition, WorkflowStep, WorkflowStepType


def get_financial_health_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        id="wf-financial-health",
        name="Quy trình Đánh giá Sức khỏe Tài chính",
        domain="finance",
        description="Truy vấn số liệu P&L, tính toán Runway và nạp quy chuẩn TT58",
        steps=[
            WorkflowStep(
                id="step_pnl",
                name="Truy vấn báo cáo lãi lỗ P&L",
                type=WorkflowStepType.TOOL,
                target="finance.query_pnl",
                params={"quarter": "Q1-2026"}
            ),
            WorkflowStep(
                id="step_runway",
                name="Tính toán số tháng dòng tiền sống còn",
                type=WorkflowStepType.TOOL,
                target="finance.calculate_runway",
                params={"cash_balance": 1500000000, "monthly_burn_rate": 120000000}
            ),
            WorkflowStep(
                id="step_skill",
                name="Áp dụng chuẩn mực TT58 đưa ra giải pháp",
                type=WorkflowStepType.SKILL,
                target="tt58-audit"
            )
        ]
    )


def get_staging_deployment_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        id="wf-staging-deployment",
        name="Quy trình Triển khai Môi trường Kiểm thử",
        domain="coding",
        description="Đọc file cấu hình, chờ Founder duyệt và kích hoạt deploy staging",
        steps=[
            WorkflowStep(
                id="step_read_config",
                name="Kiểm tra cấu hình môi trường",
                type=WorkflowStepType.TOOL,
                target="filesystem.read",
                params={"file_path": "backend/Dockerfile.api"}
            ),
            WorkflowStep(
                id="step_approval",
                name="Chờ Founder phê duyệt Deploy Staging",
                type=WorkflowStepType.HUMAN_APPROVAL,
                target="founder_approval",
                params={"action_summary": "Phê duyệt triển khai bản vá lỗi lên Staging"}
            ),
            WorkflowStep(
                id="step_deploy",
                name="Kích hoạt triển khai Hostinger Staging",
                type=WorkflowStepType.TOOL,
                target="deployment.deploy_staging",
                params={"branch": "main"}
            )
        ]
    )
