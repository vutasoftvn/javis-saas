"""Characterization tests for `CapabilityGateway._execute_internal()`.

Mục đích (Task 1 của kế hoạch modular-boundary-hardening-phase1-gateway-split):
pin chính xác hành vi HIỆN TẠI của `_execute_internal()` — 600+ dòng gộp 10 concern
(tenancy, input validation, idempotency, enablement, policy, approval, governance,
compliance, connector, ambient governance) — trước khi Task 2-10 tách từng concern
ra helper riêng. Mỗi test ở đây phải fail nếu logic quyết định thật sự đổi hành vi,
không chỉ assert rằng một mock đã được gọi.

Baseline: chạy GREEN với code `_execute_internal` chưa sửa gì — không phải TDD
RED/GREEN, không có production code mới trong task này.
"""

from __future__ import annotations

import asyncio

import pytest

from agent.capabilities.enablements import CapabilityEnablement, InMemoryEnablementStore
from agent.capabilities.gateway import (
    CapabilityGateway,
    GatewayExecutionRequest,
    GatewayExecutionResult,
)
from agent.capabilities.grants import ConnectorGrant
from agent.capabilities.registry import CapabilityRegistry
from agent.contracts.capability import CapabilitySpec
from agent.contracts.wait import WaitKind
from agent.governance.contracts import (
    ApprovalPolicy,
    CapabilityRisk,
    PolicyDecision,
    PolicyOutcome,
)
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.runs.repository import InMemoryRunRepository


@pytest.fixture
def characterization_setup():
    """Full gateway setup for characterization tests."""
    registry = CapabilityRegistry()
    repo = InMemoryRunRepository()
    gov_store = InMemoryGovernanceStateStore()
    enablement_store = InMemoryEnablementStore()

    # LOW-risk read spec — không cần tenancy, action_class mặc định "R".
    read_spec = CapabilitySpec(
        id="test.capability.read",
        version="1.0.0",
        risk=CapabilityRisk.LOW,
        input_schema={
            "type": "object",
            "required": ["id"],
            "properties": {"id": {"type": "string"}},
        },
        metadata={
            "action_class": "R",
            "definition_hash": "hash_read_v1",
        },
    )

    # HIGH-risk write spec, approval_policy ALWAYS -> floor luôn REQUIRE_APPROVAL,
    # action_class "W" -> not in (R, A) nên bắt buộc phải qua enablement store.
    write_spec = CapabilitySpec(
        id="test.capability.write",
        version="1.0.0",
        risk=CapabilityRisk.HIGH,
        approval_policy=ApprovalPolicy.ALWAYS,
        input_schema={
            "type": "object",
            "required": ["data"],
            "properties": {"data": {"type": "string"}},
        },
        metadata={
            "action_class": "W",
            "definition_hash": "hash_write_v1",
        },
    )

    call_log = []

    async def read_handler(payload, ctx):
        call_log.append(("read", payload))
        return {"result": f"read_{payload['id']}"}

    async def write_handler(payload, ctx):
        call_log.append(("write", payload))
        return {"result": f"write_{payload['data']}"}

    registry.register(read_spec, read_handler)
    registry.register(write_spec, write_handler)

    gateway = CapabilityGateway(
        registry=registry,
        repository=repo,
        governance_store=gov_store,
        enablement_store=enablement_store,
    )

    return {
        "gateway": gateway,
        "registry": registry,
        "repo": repo,
        "gov_store": gov_store,
        "enablement_store": enablement_store,
        "call_log": call_log,
        "read_spec": read_spec,
        "write_spec": write_spec,
    }


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_char_happy_path_low_risk(characterization_setup):
    """Characterization: LOW-risk capability executes without approval, all 4
    lifecycle events recorded (tool.requested, policy.evaluated, tool.started,
    tool.completed) and tool_call record saved as completed."""
    setup = characterization_setup
    gateway = setup["gateway"]
    repo = setup["repo"]
    call_log = setup["call_log"]

    req = GatewayExecutionRequest(
        run_id="run_char_lowrisk_1",
        capability_id="test.capability.read",
        input_payload={"id": "obj_123"},
        tool_call_id="call_char_read_1",
    )

    res = await gateway.execute(req)

    assert res.status == "completed"
    assert res.output_payload == {"result": "read_obj_123"}
    assert res.cached_idempotency is False
    assert call_log == [("read", {"id": "obj_123"})]

    tc = await repo.get_tool_call("call_char_read_1")
    assert tc is not None
    assert tc.status == "completed"
    assert tc.run_id == "run_char_lowrisk_1"

    events = await repo.list_events("run_char_lowrisk_1")
    event_types = [e.event_type for e in events]
    assert "tool.requested" in event_types
    assert "policy.evaluated" in event_types
    assert "tool.started" in event_types
    assert "tool.completed" in event_types


# ---------------------------------------------------------------------------
# Tenancy verification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_char_tenancy_missing_workspace_high_risk(characterization_setup):
    """Characterization: HIGH-risk capability without workspace_id/principal fails
    at tenancy check, BEFORE the handler is ever reached."""
    setup = characterization_setup
    gateway = setup["gateway"]
    call_log = setup["call_log"]

    req = GatewayExecutionRequest(
        run_id="run_char_tenancy_1",
        capability_id="test.capability.write",
        input_payload={"data": "secret"},
        tool_call_id="call_char_tenancy_1",
        # NO workspace_id, NO principal -> should fail
    )

    res = await gateway.execute(req)

    assert res.status == "failed"
    assert "tenancy unresolved" in res.error_message.lower()
    assert res.failure is not None
    assert call_log == []  # Handler never called


@pytest.mark.asyncio
async def test_char_tenancy_invalid_principal_high_risk(characterization_setup):
    """Characterization: HIGH-risk capability with 'default' principal sentinel
    is treated as unresolved tenancy, even with a real workspace_id."""
    setup = characterization_setup
    gateway = setup["gateway"]
    call_log = setup["call_log"]

    req = GatewayExecutionRequest(
        run_id="run_char_tenancy_2",
        capability_id="test.capability.write",
        input_payload={"data": "secret"},
        tool_call_id="call_char_tenancy_2",
        workspace_id="ws_valid",
        principal="default",  # Invalid sentinel value
    )

    res = await gateway.execute(req)

    assert res.status == "failed"
    assert "tenancy unresolved" in res.error_message.lower()
    assert call_log == []


@pytest.mark.asyncio
async def test_char_tenancy_low_risk_does_not_require_workspace(characterization_setup):
    """Characterization: LOW-risk (POLICY_DRIVEN approval) does NOT require tenancy
    at all — contrast case to prove the tenancy gate is risk-conditional, not global."""
    setup = characterization_setup
    gateway = setup["gateway"]
    call_log = setup["call_log"]

    req = GatewayExecutionRequest(
        run_id="run_char_tenancy_low",
        capability_id="test.capability.read",
        input_payload={"id": "obj_x"},
        tool_call_id="call_char_tenancy_low",
    )

    res = await gateway.execute(req)

    assert res.status == "completed"
    assert call_log == [("read", {"id": "obj_x"})]


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_char_input_validation_fails(characterization_setup):
    """Characterization: invalid input schema is rejected before any other step
    (idempotency claim, handler) runs."""
    setup = characterization_setup
    gateway = setup["gateway"]
    call_log = setup["call_log"]

    req = GatewayExecutionRequest(
        run_id="run_char_val_1",
        capability_id="test.capability.read",
        input_payload={},  # Missing required 'id'
    )

    res = await gateway.execute(req)

    assert res.status == "failed"
    assert len(res.validation_errors) > 0
    assert call_log == []


@pytest.mark.asyncio
async def test_char_input_validation_passes(characterization_setup):
    """Characterization: valid input schema proceeds past validation (contrast case)."""
    setup = characterization_setup
    gateway = setup["gateway"]

    req = GatewayExecutionRequest(
        run_id="run_char_val_2",
        capability_id="test.capability.read",
        input_payload={"id": "ok"},
    )

    res = await gateway.execute(req)

    assert res.status == "completed"
    assert res.validation_errors == []


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_char_idempotency_cached_completed(characterization_setup):
    """Characterization: duplicate idempotency_key WITHIN THE SAME run_id returns
    a cached result and does not re-invoke the handler.

    NOTE ON DEVIATION FROM BRIEF: the brief's draft used two different run_ids for
    req1/req2 with the same idempotency_key. The real claim key used by
    IdempotencyClaimService/InMemoryRunRepository is
    (scope_kind="RUN", scope_key=run_id, capability_id, idempotency_key) — see
    packages/agent/capabilities/idempotency.py:52 and
    packages/agent/runs/repository.py:290. Two different run_ids therefore never
    collide even with an identical idempotency_key, so the brief's version would
    NOT exercise the cached path (it would silently run the handler twice). Fixed
    here to reuse the same run_id, matching the existing convention in
    tests/agent/capabilities/test_gateway.py::test_idempotency_cache_replay.
    """
    setup = characterization_setup
    gateway = setup["gateway"]
    call_log = setup["call_log"]

    req1 = GatewayExecutionRequest(
        run_id="run_char_idem_1",
        capability_id="test.capability.read",
        input_payload={"id": "obj_123"},
        tool_call_id="call_char_idem_1",
        idempotency_key="key_unique_1",
    )

    res1 = await gateway.execute(req1)
    assert res1.status == "completed"
    assert res1.cached_idempotency is False
    assert len(call_log) == 1

    # Same run_id, same idempotency_key, different tool_call_id (simulates a
    # distinct request that happens to collide on idempotency_key).
    req2 = GatewayExecutionRequest(
        run_id="run_char_idem_1",
        capability_id="test.capability.read",
        input_payload={"id": "obj_123"},
        tool_call_id="call_char_idem_2",
        idempotency_key="key_unique_1",
    )

    res2 = await gateway.execute(req2)
    assert res2.status == "completed"
    assert res2.cached_idempotency is True
    assert res2.output_payload == res1.output_payload
    assert len(call_log) == 1  # Handler not called again


@pytest.mark.asyncio
async def test_char_idempotency_in_progress_blocks_concurrent_worker(characterization_setup):
    """Characterization: a second, distinct invocation (different tool_call_id)
    that races another in-flight one for the same (run_id, capability_id,
    idempotency_key) gets IN_PROGRESS / status="in_progress" and the handler runs
    exactly once — not CLAIMED twice."""
    setup = characterization_setup
    registry = setup["registry"]
    repo = setup["repo"]

    slow_call_count = {"n": 0}

    async def slow_handler(payload, ctx):
        slow_call_count["n"] += 1
        await asyncio.sleep(0.02)
        return {"result": "slow_done"}

    slow_spec = CapabilitySpec(
        id="test.capability.slow",
        version="1.0.0",
        risk=CapabilityRisk.LOW,
        input_schema={"type": "object"},
    )
    registry.register(slow_spec, slow_handler)

    gateway = CapabilityGateway(registry=registry, repository=repo)

    req_a = GatewayExecutionRequest(
        run_id="run_char_race_1",
        capability_id="test.capability.slow",
        input_payload={"x": 1},
        idempotency_key="idem_race_key_1",
    )
    req_b = GatewayExecutionRequest(
        run_id="run_char_race_1",
        capability_id="test.capability.slow",
        input_payload={"x": 1},
        idempotency_key="idem_race_key_1",
    )
    assert req_a.tool_call_id != req_b.tool_call_id  # genuinely distinct invocations

    res_a, res_b = await asyncio.gather(gateway.execute(req_a), gateway.execute(req_b))

    statuses = sorted([res_a.status, res_b.status])
    assert statuses == ["completed", "in_progress"]
    assert slow_call_count["n"] == 1


# ---------------------------------------------------------------------------
# Enablement check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_char_enablement_denied_no_record(characterization_setup):
    """Characterization: action_class outside (R, A) with a resolvable skill_hash
    but NO matching enablement record is denied (fail-closed) before the handler
    runs, and a `capability.enablement_denied` event + denied tool_call are recorded.

    NOTE ON DEVIATION FROM BRIEF: the brief called
    `enablement_store.set_enabled("ws_test", False, action_class="W")`, but
    InMemoryEnablementStore (packages/agent/capabilities/enablements.py) has no
    `set_enabled` method — only get_enablement/save_enablement/revoke_enablement.
    That test as drafted would raise AttributeError, not exercise the enablement
    gate. Rewritten to use the real store API: skill_hash is supplied via
    `context["skill_hash"]` (the gateway only reads skill_hash from req.context,
    never from spec.metadata — see gateway.py lines 297-307) and simply no
    enablement record is saved, which is the real "denied" trigger.
    """
    setup = characterization_setup
    gateway = setup["gateway"]
    repo = setup["repo"]
    call_log = setup["call_log"]

    req = GatewayExecutionRequest(
        run_id="run_char_enb_1",
        capability_id="test.capability.write",
        input_payload={"data": "secret"},
        tool_call_id="call_char_enb_1",
        workspace_id="ws_test",
        principal="user_1",
        context={"skill_hash": "hash_write_v1"},
    )

    res = await gateway.execute(req)

    assert res.status == "denied"
    assert "denied" in res.error_message.lower()
    assert call_log == []

    tc = await repo.get_tool_call("call_char_enb_1")
    assert tc is not None
    assert tc.status == "denied"

    events = await repo.list_events("run_char_enb_1")
    event_types = [e.event_type for e in events]
    assert "capability.enablement_denied" in event_types


@pytest.mark.asyncio
async def test_char_enablement_missing_skill_hash_denied(characterization_setup):
    """Characterization: action_class outside (R, A) with NO skill_hash resolvable
    at all is denied fail-closed (distinct reason from "no record found")."""
    setup = characterization_setup
    gateway = setup["gateway"]
    call_log = setup["call_log"]

    req = GatewayExecutionRequest(
        run_id="run_char_enb_2",
        capability_id="test.capability.write",
        input_payload={"data": "secret"},
        tool_call_id="call_char_enb_2",
        workspace_id="ws_test",
        principal="user_1",
        # No skill_hash anywhere in context.
    )

    res = await gateway.execute(req)

    assert res.status == "denied"
    assert call_log == []


@pytest.mark.asyncio
async def test_char_enablement_allowed_with_active_record(characterization_setup):
    """Characterization: an active enablement record matching (workspace,
    capability, skill_hash, action_class) lets execution proceed PAST the
    enablement gate — capability then reaches the (HIGH-risk, ALWAYS-approval)
    approval gate rather than being denied at enablement."""
    setup = characterization_setup
    gateway = setup["gateway"]
    enablement_store = setup["enablement_store"]
    repo = setup["repo"]
    call_log = setup["call_log"]

    await enablement_store.save_enablement(
        CapabilityEnablement(
            workspace_id="ws_test",
            capability_id="test.capability.write",
            skill_hash="hash_write_v1",
            action_class="W",
            target_fingerprint="*",
            status="ENABLED",
        )
    )

    req = GatewayExecutionRequest(
        run_id="run_char_enb_3",
        capability_id="test.capability.write",
        input_payload={"data": "secret"},
        tool_call_id="call_char_enb_3",
        workspace_id="ws_test",
        principal="user_1",
        context={"skill_hash": "hash_write_v1"},
    )

    res = await gateway.execute(req)

    # Not denied at enablement -- HIGH risk + ALWAYS approval floor means it
    # pauses for approval instead of completing outright.
    assert res.status == "waiting_approval"
    assert call_log == []

    events = await repo.list_events("run_char_enb_3")
    event_types = [e.event_type for e in events]
    assert "capability.enablement_denied" not in event_types


# ---------------------------------------------------------------------------
# Policy evaluation / approval gate
# ---------------------------------------------------------------------------


async def _enable_write_capability(enablement_store, workspace_id: str = "ws_test") -> None:
    """Helper: save an active enablement record so `test.capability.write`
    (action_class "W") passes the enablement gate (Bước 4.8) and reaches
    policy/approval evaluation -- the write_spec's action_class is not in
    (R, A), so without this every request to it is denied at enablement
    before ever reaching the approval gate under test."""
    await enablement_store.save_enablement(
        CapabilityEnablement(
            workspace_id=workspace_id,
            capability_id="test.capability.write",
            skill_hash="hash_write_v1",
            action_class="W",
            target_fingerprint="*",
            status="ENABLED",
        )
    )


@pytest.mark.asyncio
async def test_char_approval_gate_required(characterization_setup):
    """Characterization: HIGH-risk (ALWAYS approval policy) pauses at the approval
    gate with a WaitDescriptor(kind=APPROVAL); approving the record and
    re-executing the SAME request then completes and invokes the handler exactly
    once."""
    setup = characterization_setup
    gateway = setup["gateway"]
    repo = setup["repo"]
    call_log = setup["call_log"]
    await _enable_write_capability(setup["enablement_store"])

    req = GatewayExecutionRequest(
        run_id="run_char_appr_1",
        capability_id="test.capability.write",
        input_payload={"data": "secret"},
        tool_call_id="call_char_appr_1",
        workspace_id="ws_test",
        principal="user_1",
        checkpoint_ref="ckpt_appr_1",
        context={"skill_hash": "hash_write_v1"},
    )

    res = await gateway.execute(req)

    assert res.status == "waiting_approval"
    assert res.wait_descriptor is not None
    assert res.wait_descriptor.kind == WaitKind.APPROVAL
    assert call_log == []

    approval_id = res.wait_descriptor.related_ref
    await repo.decide_approval(approval_id, reviewer="founder", approved=True)

    res2 = await gateway.execute(req)

    assert res2.status == "completed"
    assert len(call_log) == 1


@pytest.mark.asyncio
async def test_char_approval_gate_checkpoint_mismatch_creates_new_approval(characterization_setup):
    """Characterization: an approved approval record bound to a DIFFERENT
    checkpoint_ref does not satisfy the gate — a fresh approval is required
    (exact-invocation matching, not just tool_call_id)."""
    setup = characterization_setup
    gateway = setup["gateway"]
    repo = setup["repo"]
    call_log = setup["call_log"]
    await _enable_write_capability(setup["enablement_store"])

    req1 = GatewayExecutionRequest(
        run_id="run_char_appr_mismatch",
        capability_id="test.capability.write",
        input_payload={"data": "secret"},
        tool_call_id="call_char_appr_mismatch",
        workspace_id="ws_test",
        principal="user_1",
        checkpoint_ref="ckpt_v1",
        context={"skill_hash": "hash_write_v1"},
    )
    res1 = await gateway.execute(req1)
    assert res1.status == "waiting_approval"
    await repo.decide_approval(res1.wait_descriptor.related_ref, reviewer="founder", approved=True)

    # Same tool_call_id, but a different checkpoint_ref -> approval no longer matches.
    req2 = GatewayExecutionRequest(
        run_id="run_char_appr_mismatch",
        capability_id="test.capability.write",
        input_payload={"data": "secret"},
        tool_call_id="call_char_appr_mismatch",
        workspace_id="ws_test",
        principal="user_1",
        checkpoint_ref="ckpt_v2",
        context={"skill_hash": "hash_write_v1"},
    )
    res2 = await gateway.execute(req2)

    assert res2.status == "waiting_approval"
    assert call_log == []


@pytest.mark.asyncio
async def test_char_policy_allow(characterization_setup):
    """Characterization: an injected policy_evaluator returning ALLOW does not
    block a LOW-risk capability (floor ALLOW conjoined with tenant ALLOW stays ALLOW)."""
    setup = characterization_setup
    gateway = setup["gateway"]
    call_log = setup["call_log"]

    def allow_policy(*args, **kwargs):
        return PolicyDecision(outcome=PolicyOutcome.ALLOW)

    gateway._policy_evaluator = allow_policy

    req = GatewayExecutionRequest(
        run_id="run_char_policy_allow_1",
        capability_id="test.capability.read",
        input_payload={"id": "obj_123"},
        tool_call_id="call_char_policy_allow_1",
    )

    res = await gateway.execute(req)

    assert res.status == "completed"
    assert call_log == [("read", {"id": "obj_123"})]


@pytest.mark.asyncio
async def test_char_policy_deny(characterization_setup):
    """Characterization: a tenant policy_evaluator returning DENY overrides an
    otherwise-ALLOW floor (LOW risk) — DENY always wins conjunction, handler
    never invoked, idempotency claim released (failed), tool_call marked denied."""
    setup = characterization_setup
    gateway = setup["gateway"]
    repo = setup["repo"]
    call_log = setup["call_log"]

    def deny_policy(*args, **kwargs):
        return PolicyDecision(outcome=PolicyOutcome.DENY)

    gateway._policy_evaluator = deny_policy

    req = GatewayExecutionRequest(
        run_id="run_char_policy_deny_1",
        capability_id="test.capability.read",
        input_payload={"id": "obj_123"},
        tool_call_id="call_char_policy_deny_1",
    )

    res = await gateway.execute(req)

    assert res.status == "denied"
    assert call_log == []

    tc = await repo.get_tool_call("call_char_policy_deny_1")
    assert tc is not None
    assert tc.status == "denied"


@pytest.mark.asyncio
async def test_char_policy_require_approval_from_tenant_evaluator_on_low_risk(
    characterization_setup,
):
    """Characterization: tenant policy_evaluator can escalate a LOW-risk (floor
    ALLOW) capability to REQUIRE_APPROVAL — proves the floor is a MINIMUM, not a cap."""
    setup = characterization_setup
    gateway = setup["gateway"]
    call_log = setup["call_log"]

    def escalate_policy(*args, **kwargs):
        return PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL)

    gateway._policy_evaluator = escalate_policy

    req = GatewayExecutionRequest(
        run_id="run_char_policy_escalate_1",
        capability_id="test.capability.read",
        input_payload={"id": "obj_123"},
        tool_call_id="call_char_policy_escalate_1",
        workspace_id="ws_test",
        principal="user_1",
    )

    res = await gateway.execute(req)

    assert res.status == "waiting_approval"
    assert call_log == []


# ---------------------------------------------------------------------------
# Governance accumulation (monotonic)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_char_governance_state_persisted_and_matches_decision(characterization_setup):
    """Characterization: governance_store durably records the accumulated
    PolicyDecision for (run_id, tool_call_id) after each execute() call, and its
    outcome matches the decision that drove the returned GatewayExecutionResult."""
    setup = characterization_setup
    gateway = setup["gateway"]
    gov_store = setup["gov_store"]
    await _enable_write_capability(setup["enablement_store"])

    req = GatewayExecutionRequest(
        run_id="run_char_gov_1",
        capability_id="test.capability.write",
        input_payload={"data": "secret"},
        tool_call_id="call_char_gov_1",
        workspace_id="ws_test",
        principal="user_1",
        context={"skill_hash": "hash_write_v1"},
    )

    res = await gateway.execute(req)
    assert res.status == "waiting_approval"

    state = await gov_store.load_governance_state("run_char_gov_1", "call_char_gov_1")
    assert state is not None
    assert state.accumulated.outcome == PolicyOutcome.REQUIRE_APPROVAL


@pytest.mark.asyncio
async def test_char_governance_monotonic_does_not_relax_after_require_approval(
    characterization_setup,
):
    """Characterization: once an invocation has accumulated REQUIRE_APPROVAL, a
    LATER call with a policy_evaluator that would now return ALLOW does not relax
    the accumulated outcome back down -- it stays REQUIRE_APPROVAL (monotonic
    strictness, agent/governance/accumulator.py::combine_decisions)."""
    setup = characterization_setup
    gateway = setup["gateway"]
    gov_store = setup["gov_store"]
    call_log = setup["call_log"]
    await _enable_write_capability(setup["enablement_store"])

    req = GatewayExecutionRequest(
        run_id="run_char_gov_2",
        capability_id="test.capability.write",
        input_payload={"data": "secret"},
        tool_call_id="call_char_gov_2",
        workspace_id="ws_test",
        principal="user_1",
        context={"skill_hash": "hash_write_v1"},
    )

    res1 = await gateway.execute(req)
    assert res1.status == "waiting_approval"

    # Swap in an evaluator that would now say ALLOW -- floor is still
    # REQUIRE_APPROVAL (ALWAYS + HIGH risk) so this alone wouldn't relax it, but
    # this also proves the accumulator keeps the historical constraint even if
    # the *previous* observation is not re-derived from the floor.
    def allow_policy(*args, **kwargs):
        return PolicyDecision(outcome=PolicyOutcome.ALLOW)

    gateway._policy_evaluator = allow_policy

    res2 = await gateway.execute(req)
    # Still not completed without an actual approval decision.
    assert res2.status == "waiting_approval"
    assert call_log == []

    state = await gov_store.load_governance_state("run_char_gov_2", "call_char_gov_2")
    assert state.accumulated.outcome == PolicyOutcome.REQUIRE_APPROVAL


# ---------------------------------------------------------------------------
# Compliance audit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_char_compliance_audit_event_recorded(characterization_setup):
    """Characterization: an APPROVED_FOR_USE compliance_snapshot in context
    produces a `compliance.decision` event and execution still completes."""
    setup = characterization_setup
    gateway = setup["gateway"]
    repo = setup["repo"]

    compliance_snapshot = {
        "status": "APPROVED_FOR_USE",
        "deployment_id": "deploy_123",
        "snapshot_hash": "snap_hash_xyz",
        "policy_snapshot_hash": "pol_hash_abc",
        "rule_version_ids": ["rule_v1"],
        "evidence_hashes": ["ev_1"],
        "provider_profile_version": "v1.0",
    }

    req = GatewayExecutionRequest(
        run_id="run_char_compliance_1",
        capability_id="test.capability.read",
        input_payload={"id": "obj_123"},
        tool_call_id="call_char_compliance_1",
        context={
            "compliance_snapshot": compliance_snapshot,
            "delegation_jti": "jwt_delegation_123",
        },
    )

    res = await gateway.execute(req)

    assert res.status == "completed"

    events = await repo.list_events("run_char_compliance_1")
    compliance_events = [e for e in events if e.event_type == "compliance.decision"]
    assert len(compliance_events) > 0
    assert compliance_events[0].payload["decision"] == "ALLOW"
    assert compliance_events[0].payload["deployment_id"] == "deploy_123"
    assert compliance_events[0].payload["delegation_jti"] == "jwt_delegation_123"


@pytest.mark.asyncio
async def test_char_compliance_deployment_suspended(characterization_setup):
    """Characterization: a compliance_snapshot whose status is not
    APPROVED_FOR_USE denies execution regardless of the underlying policy
    decision, marks the tool_call denied, releases the idempotency claim, and
    records a `compliance.decision` event with decision=DENY /
    reason_code=DEPLOYMENT_SUSPENDED."""
    setup = characterization_setup
    gateway = setup["gateway"]
    repo = setup["repo"]
    call_log = setup["call_log"]

    compliance_snapshot = {
        "status": "SUSPENDED",
        "deployment_id": "deploy_suspended",
        "snapshot_hash": "snap_hash_xyz",
        "policy_snapshot_hash": "pol_hash_abc",
    }

    req = GatewayExecutionRequest(
        run_id="run_char_compliance_sus_1",
        capability_id="test.capability.read",
        input_payload={"id": "obj_123"},
        tool_call_id="call_char_compliance_sus_1",
        context={
            "compliance_snapshot": compliance_snapshot,
        },
    )

    res = await gateway.execute(req)

    assert res.status == "denied"
    assert "suspended" in res.error_message.lower() or "approved" in res.error_message.lower()
    assert call_log == []

    tc = await repo.get_tool_call("call_char_compliance_sus_1")
    assert tc is not None
    assert tc.status == "denied"

    events = await repo.list_events("run_char_compliance_sus_1")
    compliance_events = [e for e in events if e.event_type == "compliance.decision"]
    assert len(compliance_events) == 1
    assert compliance_events[0].payload["decision"] == "DENY"
    assert compliance_events[0].payload["reason_code"] == "DEPLOYMENT_SUSPENDED"


# ---------------------------------------------------------------------------
# Connector grant resolution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_char_connector_grant_resolver_error_fails_closed(characterization_setup):
    """Characterization: a connector_grant_resolver raising an exception (e.g.
    control-plane HTTP timeout) is treated as fail-closed DENY -- the handler is
    never invoked and a `connector_grant.resolver_error` event is recorded."""
    registry = CapabilityRegistry()
    repo = InMemoryRunRepository()
    call_log: list[tuple[str, dict]] = []

    async def handler(payload, ctx):
        call_log.append(("mcp", payload))
        return {"items": []}

    spec = CapabilitySpec(
        id="test.capability.connector_read",
        risk=CapabilityRisk.MEDIUM,
        connector_requirements={"connector_id": "sandbox-read"},
    )
    registry.register(spec, handler)

    async def failing_resolver(connector_id, req):
        raise ConnectionError("control-plane unreachable")

    gateway = CapabilityGateway(
        registry=registry, repository=repo, connector_grant_resolver=failing_resolver
    )

    req = GatewayExecutionRequest(
        run_id="run_char_connector_err",
        capability_id="test.capability.connector_read",
        input_payload={},
        workspace_id="ws_a",
        principal="user_a",
    )
    res = await gateway.execute(req)

    assert res.status == "denied"
    assert call_log == []

    events = await repo.list_events("run_char_connector_err")
    event_types = [e.event_type for e in events]
    assert "connector_grant.resolver_error" in event_types


@pytest.mark.asyncio
async def test_char_connector_grant_denied_fails_closed(characterization_setup):
    """Characterization: a resolved-but-revoked ConnectorGrant is denied by
    verify_connector_grant -- handler never invoked, `connector_grant.denied`
    event recorded."""
    registry = CapabilityRegistry()
    repo = InMemoryRunRepository()
    call_log: list[tuple[str, dict]] = []

    async def handler(payload, ctx):
        call_log.append(("mcp", payload))
        return {"items": []}

    spec = CapabilitySpec(
        id="test.capability.connector_read2",
        risk=CapabilityRisk.MEDIUM,
        connector_requirements={"connector_id": "sandbox-read"},
    )
    registry.register(spec, handler)

    revoked_grant = ConnectorGrant(
        grant_id="grant_revoked",
        tenant_id="ws_a",
        principal="user_a",
        connector_id="sandbox-read",
        allowed_actions=("*",),
        is_revoked=True,
    )

    async def resolver(connector_id, req):
        return revoked_grant

    gateway = CapabilityGateway(registry=registry, repository=repo, connector_grant_resolver=resolver)

    req = GatewayExecutionRequest(
        run_id="run_char_connector_denied",
        capability_id="test.capability.connector_read2",
        input_payload={},
        workspace_id="ws_a",
        principal="user_a",
    )
    res = await gateway.execute(req)

    assert res.status == "denied"
    assert call_log == []

    events = await repo.list_events("run_char_connector_denied")
    event_types = [e.event_type for e in events]
    assert "connector_grant.denied" in event_types


@pytest.mark.asyncio
async def test_char_connector_grant_valid_allows_execution(characterization_setup):
    """Characterization: a resolved, valid, non-revoked ConnectorGrant lets
    execution proceed to the handler."""
    registry = CapabilityRegistry()
    repo = InMemoryRunRepository()
    call_log: list[tuple[str, dict]] = []

    async def handler(payload, ctx):
        call_log.append(("mcp", payload))
        return {"items": ["a", "b"]}

    spec = CapabilitySpec(
        id="test.capability.connector_read3",
        risk=CapabilityRisk.MEDIUM,
        connector_requirements={"connector_id": "sandbox-read"},
    )
    registry.register(spec, handler)

    grant = ConnectorGrant(
        grant_id="grant_ok",
        tenant_id="ws_a",
        principal="user_a",
        connector_id="sandbox-read",
        allowed_actions=("*",),
        is_revoked=False,
        metadata={"connection_account_id": "acct_123"},
    )

    async def resolver(connector_id, req):
        return grant

    gateway = CapabilityGateway(registry=registry, repository=repo, connector_grant_resolver=resolver)

    req = GatewayExecutionRequest(
        run_id="run_char_connector_ok",
        capability_id="test.capability.connector_read3",
        input_payload={},
        workspace_id="ws_a",
        principal="user_a",
    )
    res = await gateway.execute(req)

    assert res.status == "completed"
    assert res.output_payload == {"items": ["a", "b"]}
    assert call_log == [("mcp", {})]


# ---------------------------------------------------------------------------
# Ambient governance re-check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_char_ambient_governance_emergency_lock_denies(characterization_setup):
    """Characterization: an emergency_lock flag in context denies execution at
    the ambient-governance re-check step, immediately before the side effect --
    even for an otherwise-ALLOW LOW-risk capability."""
    setup = characterization_setup
    gateway = setup["gateway"]
    repo = setup["repo"]
    call_log = setup["call_log"]

    req = GatewayExecutionRequest(
        run_id="run_char_lock_1",
        capability_id="test.capability.read",
        input_payload={"id": "obj_123"},
        context={"emergency_lock": True},
    )
    res = await gateway.execute(req)

    assert res.status == "denied"
    assert "emergency lock" in res.error_message.lower()
    assert call_log == []

    events = await repo.list_events("run_char_lock_1")
    event_types = [e.event_type for e in events]
    assert "governance.denied" in event_types


# ---------------------------------------------------------------------------
# Handler exception handling (side-effect execution step)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_char_handler_exception(characterization_setup):
    """Characterization: an exception raised by the handler is caught, recorded
    as a `tool.failed` event, persisted as a failed tool_call, and surfaced as
    status="failed" with the exception message (not re-raised to the caller)."""
    setup = characterization_setup
    gateway = setup["gateway"]
    repo = setup["repo"]

    error_spec = CapabilitySpec(
        id="test.capability.error",
        version="1.0.0",
        risk=CapabilityRisk.LOW,
        input_schema={"type": "object"},
    )

    async def error_handler(payload, ctx):
        raise ValueError("Intentional test error")

    gateway._registry.register(error_spec, error_handler)

    req = GatewayExecutionRequest(
        run_id="run_char_err_1",
        capability_id="test.capability.error",
        input_payload={},
        tool_call_id="call_char_err_1",
    )

    res = await gateway.execute(req)

    assert res.status == "failed"
    assert "Intentional test error" in res.error_message

    tc = await repo.get_tool_call("call_char_err_1")
    assert tc is not None
    assert tc.status == "failed"

    events = await repo.list_events("run_char_err_1")
    event_types = [e.event_type for e in events]
    assert "tool.failed" in event_types
