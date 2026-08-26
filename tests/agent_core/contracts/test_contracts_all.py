from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent_core.contracts.capability import (
    CapabilityImplementationIdentity,
    CapabilityReadiness,
    CapabilityReadinessReason,
    CapabilitySpec,
)
from agent_core.contracts.context import (
    ContextFragment,
    ContextIntent,
    ContextLifetime,
    ContextSnapshot,
)
from agent_core.contracts.model_policy import ModelPolicySpec
from agent_core.contracts.prompt import PromptSpec
from agent_core.contracts.identity import InvocationIdentity, PinnedSkillRef, PinnedSpecIdentity, SpecResolutionManifest
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


def test_context_contracts():
    fragment_stable = ContextFragment(
        source_kind="rpc",
        source_ref="services.company.operations.task",
        lifetime=ContextLifetime.STABLE,
        content="Tenant workspace configuration",
        token_estimate=12,
        sensitivity="internal",
    )
    assert fragment_stable.lifetime == ContextLifetime.STABLE
    assert fragment_stable.token_estimate == 12

    fragment_run = ContextFragment(
        source_kind="rpc",
        source_ref="services.company.strategy.project",
        lifetime=ContextLifetime.RUN,
        content="Current Q3 Goal: Launch v2",
        token_estimate=15,
    )

    snapshot = ContextSnapshot(
        run_id="run_ctx_001",
        principal_id="user_founder_1",
        tenant_id="ws_cosa_dev",
        fragments=[fragment_stable, fragment_run],
        budget_tokens_remaining=15973,
    )
    assert snapshot.run_id == "run_ctx_001"
    assert len(snapshot.fragments) == 2
    assert snapshot.total_estimated_tokens() == 27
    assert snapshot.memory_access_enabled is True

    intent = ContextIntent(kind="strategic_review", domain="operations")
    assert intent.kind == "strategic_review"
    assert intent.domain == "operations"


def test_capability_readiness():
    ready_status = CapabilityReadiness(
        capability_id="operations.task.read",
        ready=True,
        reason_code=CapabilityReadinessReason.READY,
    )
    assert ready_status.ready is True
    assert ready_status.reason_code == CapabilityReadinessReason.READY

    offline_status = CapabilityReadiness(
        capability_id="finance.stripe.charge",
        ready=False,
        reason_code=CapabilityReadinessReason.CONNECTOR_OFFLINE,
        connector_ref="stripe_live",
    )
    assert offline_status.ready is False
    assert offline_status.reason_code == CapabilityReadinessReason.CONNECTOR_OFFLINE
    assert offline_status.connector_ref == "stripe_live"


def test_pinned_skill_ref_converts_to_pinned_spec_identity():
    ref = PinnedSkillRef(skill_id="research", version="12", definition_hash="b" * 64)

    identity = ref.to_pinned_identity()

    assert identity == PinnedSpecIdentity(
        spec_kind="skill", spec_id="research", spec_version="12", definition_hash="b" * 64
    )


def test_agent_spec_defaults_have_no_pinned_dependency_refs():
    spec = AgentSpec(id="test.agent.m2_1")

    assert spec.prompt_ref is None
    assert spec.model_policy_ref is None
    assert spec.tool_contract_refs == []


def test_agent_spec_fingerprint_changes_when_prompt_ref_is_set():
    prompt = PromptSpec(id="cofounder/system", version="1", text="Nội dung").with_hash()
    base = AgentSpec(id="test.agent.m2_2")
    with_prompt = base.model_copy(update={"prompt_ref": prompt.to_pinned_identity()})

    assert base.compute_hash() != with_prompt.compute_hash()


def test_agent_spec_fingerprint_changes_when_model_policy_ref_drifts():
    policy_v1 = ModelPolicySpec(id="default-deepseek-policy", version="1", model="deepseek-chat").with_hash()
    policy_v2 = ModelPolicySpec(id="default-deepseek-policy", version="1", model="deepseek-reasoner").with_hash()

    spec_v1 = AgentSpec(id="test.agent.m2_3", model_policy_ref=policy_v1.to_pinned_identity())
    spec_v2 = AgentSpec(id="test.agent.m2_3", model_policy_ref=policy_v2.to_pinned_identity())

    assert spec_v1.compute_hash() != spec_v2.compute_hash()


def test_agent_spec_fingerprint_changes_when_tool_contract_refs_change():
    base = AgentSpec(id="test.agent.m2_4")
    with_contract = base.model_copy(
        update={
            "tool_contract_refs": [
                CapabilityImplementationIdentity(capability_id="company.strategy.read", handler_version="2.0.0")
            ]
        }
    )

    assert base.compute_hash() != with_contract.compute_hash()


from agent_core.knowledge.snapshot import KnowledgeSnapshot


def test_agent_spec_defaults_to_no_knowledge_snapshot_ref():
    spec = AgentSpec(id="test.agent.m6_1")

    assert spec.knowledge_snapshot_ref is None


def test_agent_spec_fingerprint_changes_when_knowledge_snapshot_ref_is_set():
    snapshot = KnowledgeSnapshot(
        id="workspace-abc.default_kb",
        version="1",
        workspace_id="workspace-abc",
        embedding_model="text-embedding-3-small",
        embedding_version="1",
    ).with_hash()
    base = AgentSpec(id="test.agent.m6_2")
    with_ref = base.model_copy(update={"knowledge_snapshot_ref": snapshot.to_pinned_identity()})

    assert base.compute_hash() != with_ref.compute_hash()


def test_contracts_init_exports_same_class_as_target_module():
    """Xác nhận rằng ExecutionTargetSnapshot được export từ agent_core.contracts
    là cùng class với agent_core.contracts.target.ExecutionTargetSnapshot.
    """
    from agent_core.contracts import ExecutionTargetSnapshot as FromInit
    from agent_core.contracts.target import ExecutionTargetSnapshot as FromTarget
    assert FromInit is FromTarget

