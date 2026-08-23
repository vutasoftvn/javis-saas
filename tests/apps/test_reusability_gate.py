from __future__ import annotations

import pytest

from agent_core.capabilities.approval_service import DurableApprovalService
from agent_core.capabilities.gateway import (
    CapabilityGateway,
    GatewayExecutionRequest,
)
from agent_core.capabilities.registry import CapabilityRegistry
from agent_core.contracts.capability import CapabilitySpec
from agent_core.contracts.spec import AgentSpec
from agent_core.contracts.wait import WaitKind
from agent_core.governance.contracts import (
    AutonomyLevel,
    CapabilityRisk,
    PolicyDecision,
    PolicyOutcome,
    RoleApproval,
)
from agent_core.kernel.openai_agents_kernel import OpenAIAgentsKernel
from agent_core.runs.repository import InMemoryRunRepository
from agent_core.workflows.definition_registry import WorkflowDefinitionRegistry
from agent_core.workflows.engine import WorkflowEngine
from agent_core.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec
from agent_core.workflows.steps import DeterministicStep


@pytest.mark.asyncio
async def test_reusability_gate_second_app_independence():
    """Reusability Gate Check (Master Guide §4.2 & §42).
    
    Chứng minh: Một ứng dụng độc lập hoàn toàn (vd. 'HealthClinicAgentPlane') có thể được
    xây dựng 100% bằng cách sử dụng các abstractions từ `packages/agent_core/*`
    mà KHÔNG CẦN bất kỳ dòng code hay business logic nào của COSA / `services/company`.
    """
    # 1. Khởi tạo Substrate của Second App
    repo = InMemoryRunRepository()
    cap_registry = CapabilityRegistry()

    prescriptions_committed = []

    # 2. Định nghĩa Capabilities của domain Y Tế (Healthcare)
    spec_patient_lookup = CapabilitySpec(
        id="healthcare.patient.lookup",
        risk=CapabilityRisk.LOW,
        input_schema={
            "type": "object",
            "required": ["patient_id"],
            "properties": {"patient_id": {"type": "string"}},
        },
    )

    spec_prescription_order = CapabilitySpec(
        id="healthcare.prescription.order",
        risk=CapabilityRisk.HIGH,  # Bắt buộc Bác sĩ trưởng duyệt
        input_schema={
            "type": "object",
            "required": ["patient_id", "medication", "dosage", "idempotency_key"],
            "properties": {
                "patient_id": {"type": "string"},
                "medication": {"type": "string"},
                "dosage": {"type": "string"},
                "idempotency_key": {"type": "string"},
            },
        },
    )

    async def handle_patient_lookup(payload, ctx):
        return {"patient_id": payload["patient_id"], "name": "John Doe", "allergies": ["Penicillin"]}

    async def handle_prescription_order(payload, ctx):
        record = {
            "order_id": f"rx_{len(prescriptions_committed) + 1}",
            "medication": payload["medication"],
            "patient_id": payload["patient_id"],
            "status": "dispensed",
        }
        prescriptions_committed.append(record)
        return record

    cap_registry.register(spec_patient_lookup, handle_patient_lookup)
    cap_registry.register(spec_prescription_order, handle_prescription_order)

    # 3. Healthcare Policy Evaluator
    def healthcare_policy_evaluator(capability_id, payload, ctx):
        if "prescription" in capability_id:
            if payload.get("medication") == "ControlledSubstance_X":
                return PolicyDecision(
                    outcome=PolicyOutcome.REQUIRE_APPROVAL,
                    requirement=RoleApproval(role="chief_medical_officer"),
                    reasons=("Controlled substance prescription requires CMO approval",),
                )
            return PolicyDecision(
                outcome=PolicyOutcome.REQUIRE_APPROVAL,
                requirement=RoleApproval(role="attending_physician"),
                reasons=("Prescription requires physician sign-off",),
            )
        return PolicyDecision(outcome=PolicyOutcome.ALLOW)

    # 4. Gateway & Approval Service
    approval_svc = DurableApprovalService(repository=repo, policy_evaluator=healthcare_policy_evaluator)
    gateway = CapabilityGateway(
        registry=cap_registry,
        repository=repo,
        policy_evaluator=healthcare_policy_evaluator,
    )

    # 5. Chạy Capability Read
    res_read = await gateway.execute(
        GatewayExecutionRequest(
            run_id="run_clinic_1",
            capability_id="healthcare.patient.lookup",
            input_payload={"patient_id": "p_888"},
            tool_call_id="call_patient_lookup_1",
        )
    )
    assert res_read.status == "completed"
    assert res_read.output_payload["name"] == "John Doe"

    # 6. Chạy Capability Write (High Risk) -> Yêu cầu Duyệt
    req_rx = GatewayExecutionRequest(
        run_id="run_clinic_1",
        capability_id="healthcare.prescription.order",
        input_payload={
            "patient_id": "p_888",
            "medication": "ControlledSubstance_X",
            "dosage": "50mg",
            "idempotency_key": "idem_rx_001",
        },
        tool_call_id="call_rx_001",
        checkpoint_ref="ckpt_rx_001",
        idempotency_key="idem_rx_001",
    )
    res_rx_pause = await gateway.execute(req_rx)
    assert res_rx_pause.status == "waiting_approval"
    appr_id = res_rx_pause.wait_descriptor.related_ref

    # 7. Bác sĩ trưởng (CMO) phê duyệt
    await approval_svc.submit_decision(
        approval_id=appr_id,
        reviewer="dr_smith_cmo",
        approved=True,
        reason="Approved clinical indication",
    )

    # 8. Gateway resume và hoàn tất đơn thuốc
    res_rx_done = await gateway.execute(req_rx)
    assert res_rx_done.status == "completed"
    assert len(prescriptions_committed) == 1
    assert prescriptions_committed[0]["medication"] == "ControlledSubstance_X"
