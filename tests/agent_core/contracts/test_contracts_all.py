from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent_core.contracts.capability import CapabilitySpec
from agent_core.contracts.identity import InvocationIdentity, PinnedSpecIdentity, SpecResolutionManifest
from agent_core.contracts.kernel import ExecutionKernel
from agent_core.contracts.run import RunRequest, RunResult, RunStatus
from agent_core.contracts.spec import AgentSpec
from agent_core.contracts.target import ExecutionTargetSnapshot
from agent_core.contracts.wait import WaitDescriptor, WaitKind
from agent_core.governance.contracts import (
    ApprovalPolicy,
    AutonomyLevel,
    CapabilityRisk,
    ExecutionMode,
    PolicyOutcome,
)


def test_agent_spec_definition_hash_determinism():
    spec1 = AgentSpec(
        id="finance-agent",
        version="1.0.0",
        instructions="Handle finance",
        autonomy_level=AutonomyLevel.L2,
        capability_refs=["finance.invoice.send"],
    )
    spec2 = AgentSpec(
        id="finance-agent",
        version="1.0.0",
        instructions="Handle finance",
        autonomy_level=AutonomyLevel.L2,
        capability_refs=["finance.invoice.send"],
    )
    spec3 = AgentSpec(
        id="finance-agent",
        version="1.0.0",
        instructions="Handle finance modified",
        autonomy_level=AutonomyLevel.L2,
        capability_refs=["finance.invoice.send"],
    )

    hash1 = spec1.compute_hash()
    hash2 = spec2.compute_hash()
    hash3 = spec3.compute_hash()

    assert len(hash1) == 64
    assert hash1 == hash2
    assert hash1 != hash3

    pinned = spec1.to_pinned_identity()
    assert pinned.spec_kind == "agent"
    assert pinned.spec_id == "finance-agent"
    assert pinned.spec_version == "1.0.0"
    assert pinned.definition_hash == hash1


def test_run_request_and_result_validation():
    # Valid RunRequest
    req = RunRequest(
        principal="founder_user_1",
        workspace_id="ws_123",
        root_executable_ref="finance-agent",
        input={"month": "2026-08"},
        execution_mode=ExecutionMode.AUTONOMOUS,
    )
    assert req.principal == "founder_user_1"
    assert req.execution_mode == ExecutionMode.AUTONOMOUS

    # Missing principal should fail
    with pytest.raises(ValidationError):
        RunRequest.model_validate({"input": {}})

    # Valid RunResult
    res = RunResult(
        run_id="run_abc",
        status=RunStatus.COMPLETED,
        final_output={"summary": "ok"},
        usage={"tokens": 150},
    )
    assert res.run_id == "run_abc"
    assert res.status == RunStatus.COMPLETED
    assert res.final_output["summary"] == "ok"


def test_invocation_identity_validation():
    ident = InvocationIdentity(
        run_id="run_1",
        tool_call_id="call_99",
        capability_id="operations.task.create",
        payload_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        idempotency_key="idem_1",
    )
    assert ident.run_id == "run_1"
    assert ident.tool_call_id == "call_99"
    assert ident.idempotency_key == "idem_1"

    # Missing required tool_call_id
    with pytest.raises(ValidationError):
        InvocationIdentity.model_validate({"run_id": "run_1", "capability_id": "cap_1"})


def test_execution_target_snapshot():
    target = ExecutionTargetSnapshot(
        capability_id="finance.invoice.send",
        connector_id="quickbooks_connector",
        connection_account_id="acc_main",
        capability_risk_at_request_time=CapabilityRisk.CRITICAL,
    )
    assert target.capability_id == "finance.invoice.send"
    assert target.capability_risk_at_request_time == CapabilityRisk.CRITICAL


def test_wait_descriptor():
    wait = WaitDescriptor(
        kind=WaitKind.APPROVAL,
        reason="Founder approval required for invoices > $10k",
        owner_responder="founder",
        resume_trigger="approval.decided",
        checkpoint_ref="ckpt_step_3",
        related_ref="appr_001",
    )
    assert wait.kind == WaitKind.APPROVAL
    assert wait.owner_responder == "founder"
    assert wait.checkpoint_ref == "ckpt_step_3"


def test_capability_spec():
    cap = CapabilitySpec(
        id="finance.invoice.create",
        description="Create a new draft invoice",
        risk=CapabilityRisk.MEDIUM,
        approval_policy=ApprovalPolicy.POLICY_DRIVEN,
        idempotency_semantics="key_based",
    )
    assert cap.id == "finance.invoice.create"
    assert cap.risk == CapabilityRisk.MEDIUM
    assert cap.approval_policy == ApprovalPolicy.POLICY_DRIVEN


def test_execution_kernel_protocol_conformance():
    class DummyKernel:
        async def run(self, request: RunRequest, spec: AgentSpec) -> RunResult:
            return RunResult(run_id="dummy", status=RunStatus.COMPLETED)

        async def resume(self, run_id: str, checkpoint_ref: str, updates: dict) -> RunResult:
            return RunResult(run_id=run_id, status=RunStatus.COMPLETED)

        async def cancel(self, run_id: str, reason: str | None = None) -> bool:
            return True

        async def stream(self, request: RunRequest, spec: AgentSpec):
            yield {"type": "message.delta", "content": "hello"}

    kernel = DummyKernel()
    assert isinstance(kernel, ExecutionKernel)
