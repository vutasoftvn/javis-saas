from __future__ import annotations

from agent.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec

__all__ = ["COSA_PAYOUT_APPROVAL_WORKFLOW_SPEC"]

COSA_PAYOUT_APPROVAL_WORKFLOW_SPEC = WorkflowSpec(
    id="cosa.workflows.payout_approval",
    name="COSA Standard Payout Approval Workflow",
    version="1.0.0",
    description="Quy trình thanh toán giải ngân có kiểm duyệt an toàn và bù trừ hoàn tác.",
    steps=[
        WorkflowStepSpec(
            id="prepare_payout",
            name="Prepare Payout Payload",
            type=StepType.DETERMINISTIC,
        ),
        WorkflowStepSpec(
            id="approval_gate",
            name="Founder/Finance Lead Approval Gate",
            type=StepType.APPROVAL_GATE,
            depends_on=["prepare_payout"],
        ),
        WorkflowStepSpec(
            id="execute_payout",
            name="Execute Bank Transfer via Encore",
            type=StepType.TOOL_CALL,
            tool="finance.payout.execute",
            depends_on=["approval_gate"],
            on_failure="notify_failure",
        ),
        WorkflowStepSpec(
            id="notify_failure",
            name="Notify Failure Compensation",
            type=StepType.COMPENSATING,
        ),
    ],
)
