"""
Lead Outreach Workflow Definition
"""
from workflows.base import WorkflowDefinition, WorkflowStep, WorkflowStepType


def get_lead_outreach_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        id="wf-lead-outreach",
        name="Quy trình Tiếp cận Khách hàng B2B",
        domain="sales",
        description="Nạp tiêu chuẩn ICP, quét leads từ CRM, dừng chờ Founder phê duyệt trước khi lưu lead mới",
        steps=[
            WorkflowStep(
                id="step_skill",
                name="Nạp tiêu chuẩn Lead Generation",
                type=WorkflowStepType.SKILL,
                target="lead-generation"
            ),
            WorkflowStep(
                id="step_search",
                name="Tìm kiếm danh sách leads tiềm năng",
                type=WorkflowStepType.TOOL,
                target="crm.search_leads",
                params={"query": "SaaS CTO"}
            ),
            WorkflowStep(
                id="step_approval",
                name="Chờ Founder phê duyệt danh sách tiếp cận",
                type=WorkflowStepType.HUMAN_APPROVAL,
                target="founder_approval",
                params={"action_summary": "Phê duyệt gửi email tiếp cận cho 5 leads mới"}
            ),
            WorkflowStep(
                id="step_create_lead",
                name="Tạo lead chính thức vào CRM",
                type=WorkflowStepType.TOOL,
                target="crm.create_lead",
                params={"name": "Nguyễn Văn A", "email": "a@vuta.vn", "company": "VutaTech"}
            )
        ]
    )
