from __future__ import annotations

import pytest
from agent.capabilities.enablements import CapabilityEnablement, InMemoryEnablementStore
from agent.capabilities.gateway import GatewayExecutionRequest
from agent.capabilities.gateway_internals import (
    ComplianceAuditor,
    EnablementValidator,
    IdempotencyCoordinator,
    InputValidator,
    TenancyVerifier,
)
from agent.capabilities.idempotency import IdempotencyClaimService, IdempotencyOutcome
from agent.capabilities.registry import CapabilityRegistry
from agent.contracts.capability import CapabilitySpec
from agent.contracts.errors import TenancyUnresolvedError
from agent.governance.contracts import CapabilityRisk, PolicyDecision, PolicyOutcome
from agent.runs.repository import InMemoryRunRepository


@pytest.fixture
def tenancy_verifier():
    return TenancyVerifier()


@pytest.mark.asyncio
async def test_tenancy_verifier_high_risk_requires_workspace(tenancy_verifier):
    """HIGH-risk capability without workspace raises TenancyUnresolvedError."""
    spec = CapabilitySpec(
        id="test.high_risk",
        version="1.0.0",
        risk=CapabilityRisk.HIGH,
    )
    req = GatewayExecutionRequest(
        run_id="run_1",
        capability_id="test.high_risk",
        input_payload={},
        workspace_id=None,
        principal="user_1",
    )

    with pytest.raises(TenancyUnresolvedError):
        await tenancy_verifier.verify(spec, req)


@pytest.mark.asyncio
async def test_tenancy_verifier_high_risk_requires_principal(tenancy_verifier):
    """HIGH-risk capability without principal raises TenancyUnresolvedError."""
    spec = CapabilitySpec(
        id="test.high_risk",
        version="1.0.0",
        risk=CapabilityRisk.HIGH,
    )
    req = GatewayExecutionRequest(
        run_id="run_1",
        capability_id="test.high_risk",
        input_payload={},
        workspace_id="ws_1",
        principal=None,
    )

    with pytest.raises(TenancyUnresolvedError):
        await tenancy_verifier.verify(spec, req)


@pytest.mark.asyncio
async def test_tenancy_verifier_rejects_default_workspace(tenancy_verifier):
    """Tenancy check rejects 'default' or 'default_workspace' sentinel values."""
    spec = CapabilitySpec(
        id="test.high_risk",
        version="1.0.0",
        risk=CapabilityRisk.HIGH,
    )
    req = GatewayExecutionRequest(
        run_id="run_1",
        capability_id="test.high_risk",
        input_payload={},
        workspace_id="default_workspace",
        principal="user_1",
    )

    with pytest.raises(TenancyUnresolvedError):
        await tenancy_verifier.verify(spec, req)


@pytest.mark.asyncio
async def test_tenancy_verifier_low_risk_no_workspace_required(tenancy_verifier):
    """LOW-risk capability does not require workspace."""
    spec = CapabilitySpec(
        id="test.low_risk",
        version="1.0.0",
        risk=CapabilityRisk.LOW,
    )
    req = GatewayExecutionRequest(
        run_id="run_1",
        capability_id="test.low_risk",
        input_payload={},
        workspace_id=None,
    )

    ws, principal = await tenancy_verifier.verify(spec, req)
    assert ws == ""
    # GatewayExecutionRequest defaults `principal` to "system" khi không truyền
    # (không phải None) — LOW-risk không cần tenancy nên giá trị mặc định này
    # được trả nguyên vẹn, không bị verifier ép về rỗng.
    assert principal == "system"


@pytest.mark.asyncio
async def test_tenancy_verifier_fallback_from_context_dict(tenancy_verifier):
    """Tenancy verifier falls back to context dict for workspace/principal."""
    spec = CapabilitySpec(
        id="test.high_risk",
        version="1.0.0",
        risk=CapabilityRisk.HIGH,
    )
    req = GatewayExecutionRequest(
        run_id="run_1",
        capability_id="test.high_risk",
        input_payload={},
        context={"workspace_id": "ws_from_ctx", "principal": "user_from_ctx"},
    )

    ws, principal = await tenancy_verifier.verify(spec, req)
    assert ws == "ws_from_ctx"
    assert principal == "user_from_ctx"


@pytest.mark.asyncio
async def test_tenancy_verifier_explicit_req_overrides_context(tenancy_verifier):
    """Explicit workspace/principal in request overrides context."""
    spec = CapabilitySpec(
        id="test.high_risk",
        version="1.0.0",
        risk=CapabilityRisk.HIGH,
    )
    req = GatewayExecutionRequest(
        run_id="run_1",
        capability_id="test.high_risk",
        input_payload={},
        workspace_id="ws_req",
        principal="user_req",
        context={"workspace_id": "ws_ctx", "principal": "user_ctx"},
    )

    ws, principal = await tenancy_verifier.verify(spec, req)
    assert ws == "ws_req"
    assert principal == "user_req"


@pytest.fixture
def input_validator():
    return InputValidator(CapabilityRegistry())


def test_input_validator_valid(input_validator):
    """Valid input passes validation."""
    spec = CapabilitySpec(
        id="test.spec",
        version="1.0.0",
        input_schema={
            "type": "object",
            "required": ["id"],
            "properties": {"id": {"type": "string"}},
        },
    )
    errors = input_validator.validate(spec, {"id": "obj_123"})
    assert errors == []


def test_input_validator_missing_required(input_validator):
    """Missing required field returns error."""
    spec = CapabilitySpec(
        id="test.spec",
        version="1.0.0",
        input_schema={
            "type": "object",
            "required": ["id"],
            "properties": {"id": {"type": "string"}},
        },
    )
    errors = input_validator.validate(spec, {})
    assert len(errors) > 0


@pytest.fixture
def idempotency_coordinator():
    repo = InMemoryRunRepository()
    return IdempotencyCoordinator(IdempotencyClaimService(repo))


@pytest.mark.asyncio
async def test_idempotency_coordinator_claims_first_time(idempotency_coordinator):
    """First time: claim succeeds (CLAIMED or RETRIED), claim object returned."""
    outcome, claim = await idempotency_coordinator.coordinate(
        run_id="run_1",
        tool_call_id="call_1",
        capability_id="test.cap",
        idempotency_key="key_1",
        payload_hash="hash_1",
    )

    assert outcome in (IdempotencyOutcome.CLAIMED, IdempotencyOutcome.RETRIED)
    assert claim is not None
    assert not idempotency_coordinator.should_return_cached(outcome)
    assert not idempotency_coordinator.should_return_in_progress(outcome)


@pytest.mark.asyncio
async def test_idempotency_coordinator_cached_completed(idempotency_coordinator):
    """Duplicate key sau khi claim đầu tiên đã complete() -> CACHED_COMPLETED.

    NOTE: claim key thật là (scope_kind="RUN", scope_key=run_id, capability_id,
    idempotency_key) — xem packages/agent/capabilities/idempotency.py:52 và
    packages/agent/runs/repository.py:290. Hai lần gọi phải cùng run_id mới
    collide (khác tool_call_id để mô phỏng 2 request khác nhau), giống convention
    trong test_char_idempotency_cached_completed.
    """
    _outcome1, claim1 = await idempotency_coordinator.coordinate(
        run_id="run_1",
        tool_call_id="call_1",
        capability_id="test.cap",
        idempotency_key="key_dup",
        payload_hash="hash_1",
    )

    await idempotency_coordinator._idempotency.complete(
        claim1.claim_id, result_payload={"result": "ok"}, result_hash="result_hash_1"
    )

    outcome2, claim2 = await idempotency_coordinator.coordinate(
        run_id="run_1",
        tool_call_id="call_2",
        capability_id="test.cap",
        idempotency_key="key_dup",
        payload_hash="hash_1",
    )

    assert outcome2 == IdempotencyOutcome.CACHED_COMPLETED
    assert idempotency_coordinator.should_return_cached(outcome2)
    assert claim2.result_payload == {"result": "ok"}


@pytest.mark.asyncio
async def test_idempotency_coordinator_in_progress(idempotency_coordinator):
    """Claim còn đang chạy (chưa complete/fail) -> lần gọi thứ hai (cùng run_id,
    khác tool_call_id) trả IN_PROGRESS."""
    outcome1, claim1 = await idempotency_coordinator.coordinate(
        run_id="run_1",
        tool_call_id="call_1",
        capability_id="test.cap",
        idempotency_key="key_in_progress",
        payload_hash="hash_1",
    )
    assert outcome1 in (IdempotencyOutcome.CLAIMED, IdempotencyOutcome.RETRIED)

    outcome2, claim2 = await idempotency_coordinator.coordinate(
        run_id="run_1",
        tool_call_id="call_2",
        capability_id="test.cap",
        idempotency_key="key_in_progress",
        payload_hash="hash_1",
    )

    assert outcome2 == IdempotencyOutcome.IN_PROGRESS
    assert idempotency_coordinator.should_return_in_progress(outcome2)
    assert claim2.claim_id == claim1.claim_id


@pytest.fixture
def enablement_validator():
    return EnablementValidator(InMemoryEnablementStore())


def test_enablement_validator_extracts_action_class_from_dict(enablement_validator):
    """Extract action_class from context dict (dict wins over spec metadata)."""
    spec = CapabilitySpec(
        id="test.spec",
        version="1.0.0",
        metadata={"action_class": "R"},
    )

    action_class = enablement_validator.extract_action_class(spec, {"action_class": "W"})
    assert action_class == "W"


def test_enablement_validator_extracts_action_class_falls_back_to_spec(enablement_validator):
    """No action_class in context -> falls back to spec metadata."""
    spec = CapabilitySpec(
        id="test.spec",
        version="1.0.0",
        metadata={"action_class": "W"},
    )

    action_class = enablement_validator.extract_action_class(spec, {})
    assert action_class == "W"


def test_enablement_validator_extracts_skill_hash(enablement_validator):
    """Extract skill_hash from context dict."""
    skill_hash = enablement_validator.extract_skill_hash({"skill_hash": "hash_123"})
    assert skill_hash == "hash_123"


def test_enablement_validator_extracts_skill_hash_from_pinned_skill(enablement_validator):
    """Falls back to pinned_skill.definition_hash when skill_hash absent."""
    skill_hash = enablement_validator.extract_skill_hash(
        {"pinned_skill": {"definition_hash": "hash_pinned"}}
    )
    assert skill_hash == "hash_pinned"


def test_enablement_validator_extracts_skill_hash_none(enablement_validator):
    """No skill_hash anywhere in context -> None."""
    skill_hash = enablement_validator.extract_skill_hash({})
    assert skill_hash is None


@pytest.mark.asyncio
async def test_enablement_validator_enabled(enablement_validator):
    """No enablement records configured -> default-allow, validation passes."""
    spec = CapabilitySpec(
        id="test.spec",
        version="1.0.0",
        metadata={"action_class": "R"},
    )

    is_enabled, error = await enablement_validator.validate(
        spec=spec,
        capability_id="test.spec",
        workspace_id="ws_1",
        context={},
    )

    assert is_enabled is True
    assert error is None


@pytest.mark.asyncio
async def test_enablement_validator_denied_no_matching_record(enablement_validator):
    """action_class outside (R, A) with a resolvable skill_hash but NO matching
    enablement record for (workspace_id, capability_id, action_class, skill_hash)
    is denied fail-closed. Mirrors test_char_enablement_denied_no_record but
    exercises EnablementValidator.validate() directly, no gateway involved."""
    spec = CapabilitySpec(
        id="test.capability.write",
        version="1.0.0",
        metadata={"action_class": "W"},
    )

    is_enabled, error = await enablement_validator.validate(
        spec=spec,
        capability_id="test.capability.write",
        workspace_id="ws_test",
        context={"skill_hash": "hash_write_v1"},
    )

    assert is_enabled is False
    assert error is not None
    assert "No enablement record found" in error


@pytest.mark.asyncio
async def test_enablement_validator_denied_missing_skill_hash(enablement_validator):
    """action_class outside (R, A) with NO skill_hash resolvable anywhere in
    context is denied fail-closed, with a distinct reason from "no record
    found". Mirrors test_char_enablement_missing_skill_hash_denied."""
    spec = CapabilitySpec(
        id="test.capability.write",
        version="1.0.0",
        metadata={"action_class": "W"},
    )

    is_enabled, error = await enablement_validator.validate(
        spec=spec,
        capability_id="test.capability.write",
        workspace_id="ws_test",
        context={},
    )

    assert is_enabled is False
    assert error is not None
    assert "requires exact skill definition_hash" in error


@pytest.mark.asyncio
async def test_enablement_validator_allowed_with_active_record():
    """An active ENABLED record matching (workspace, capability, skill_hash,
    action_class) lets validate() report enabled with no error. Mirrors
    test_char_enablement_allowed_with_active_record."""
    store = InMemoryEnablementStore()
    await store.save_enablement(
        CapabilityEnablement(
            workspace_id="ws_test",
            capability_id="test.capability.write",
            skill_hash="hash_write_v1",
            action_class="W",
            target_fingerprint="*",
            status="ENABLED",
        )
    )
    validator = EnablementValidator(store)
    spec = CapabilitySpec(
        id="test.capability.write",
        version="1.0.0",
        metadata={"action_class": "W"},
    )

    is_enabled, error = await validator.validate(
        spec=spec,
        capability_id="test.capability.write",
        workspace_id="ws_test",
        context={"skill_hash": "hash_write_v1"},
    )

    assert is_enabled is True
    assert error is None


# ---------------------------------------------------------------------------
# ComplianceAuditor
# ---------------------------------------------------------------------------


@pytest.fixture
def compliance_repo():
    return InMemoryRunRepository()


@pytest.fixture
def compliance_auditor(compliance_repo):
    return ComplianceAuditor(compliance_repo)


def test_compliance_auditor_extract_snapshot_from_dict(compliance_auditor):
    """extract_compliance_snapshot reads compliance_snapshot straight off a dict context."""
    snap = compliance_auditor.extract_compliance_snapshot(
        {"compliance_snapshot": {"status": "APPROVED_FOR_USE"}}
    )
    assert snap == {"status": "APPROVED_FOR_USE"}


def test_compliance_auditor_extract_snapshot_missing(compliance_auditor):
    """No compliance_snapshot key anywhere -> None."""
    assert compliance_auditor.extract_compliance_snapshot({}) is None
    assert compliance_auditor.extract_compliance_snapshot(None) is None


@pytest.mark.asyncio
async def test_compliance_auditor_no_snapshot_continues(compliance_auditor, compliance_repo):
    """No compliance snapshot in context -> should_continue=True, no result, no event logged."""
    decision = PolicyDecision(outcome=PolicyOutcome.ALLOW)

    should_continue, result = await compliance_auditor.audit(
        context={},
        run_id="run_1",
        workspace_id="ws_1",
        tool_call_id="call_1",
        checkpoint_ref="ckpt_1",
        capability_id="test.cap",
        current_decision=decision,
        payload_hash="hash_1",
    )

    assert should_continue is True
    assert result is None
    events = await compliance_repo.list_events("run_1")
    assert [e for e in events if e.event_type == "compliance.decision"] == []


@pytest.mark.asyncio
async def test_compliance_auditor_approved_records_allow_event(
    compliance_auditor, compliance_repo
):
    """Happy path: APPROVED_FOR_USE snapshot -> continue, and a compliance.decision
    event is recorded with decision matching current_decision.outcome."""
    decision = PolicyDecision(outcome=PolicyOutcome.ALLOW)
    context = {
        "compliance_snapshot": {
            "status": "APPROVED_FOR_USE",
            "deployment_id": "deploy_ok",
            "snapshot_hash": "snap_hash",
            "policy_snapshot_hash": "pol_hash",
            "rule_version_ids": ["rule_v1"],
            "evidence_hashes": ["ev_1"],
            "provider_profile_version": "v1.0",
        },
        "delegation_jti": "jwt_123",
    }

    should_continue, result = await compliance_auditor.audit(
        context=context,
        run_id="run_allow",
        workspace_id="ws_1",
        tool_call_id="call_1",
        checkpoint_ref="ckpt_1",
        capability_id="test.cap",
        current_decision=decision,
        payload_hash="hash_1",
    )

    assert should_continue is True
    assert result is None

    events = await compliance_repo.list_events("run_allow")
    compliance_events = [e for e in events if e.event_type == "compliance.decision"]
    assert len(compliance_events) == 1
    payload = compliance_events[0].payload
    assert payload["decision"] == "ALLOW"
    assert payload["deployment_id"] == "deploy_ok"
    assert payload["delegation_jti"] == "jwt_123"
    assert payload["provider_model_ref"] == "v1.0"


@pytest.mark.asyncio
async def test_compliance_auditor_suspended_deployment_denies(
    compliance_auditor, compliance_repo
):
    """Deny path: a non-APPROVED_FOR_USE status returns should_continue=False with
    a denied GatewayExecutionResult, and still records a compliance.decision event
    with decision=DENY / reason_code=DEPLOYMENT_SUSPENDED (mirrors
    test_char_compliance_deployment_suspended)."""
    decision = PolicyDecision(outcome=PolicyOutcome.ALLOW)
    context = {
        "compliance_snapshot": {
            "status": "SUSPENDED",
            "deployment_id": "deploy_sus",
            "snapshot_hash": "snap_hash_xyz",
            "policy_snapshot_hash": "pol_hash_abc",
        }
    }

    should_continue, result = await compliance_auditor.audit(
        context=context,
        run_id="run_deny",
        workspace_id="ws_1",
        tool_call_id="call_1",
        checkpoint_ref="ckpt_1",
        capability_id="test.cap",
        current_decision=decision,
        payload_hash="hash_1",
    )

    assert should_continue is False
    assert result is not None
    assert result.status == "denied"
    assert "suspended" in result.error_message.lower() or "approved" in result.error_message.lower()

    events = await compliance_repo.list_events("run_deny")
    compliance_events = [e for e in events if e.event_type == "compliance.decision"]
    assert len(compliance_events) == 1
    assert compliance_events[0].payload["decision"] == "DENY"
    assert compliance_events[0].payload["reason_code"] == "DEPLOYMENT_SUSPENDED"
    assert compliance_events[0].payload["deployment_id"] == "deploy_sus"


@pytest.mark.asyncio
async def test_compliance_auditor_not_approved_status_denies(
    compliance_auditor, compliance_repo
):
    """Deny path variant: any status other than APPROVED_FOR_USE denies (not just
    SUSPENDED specifically) -- e.g. a PENDING_REVIEW deployment status."""
    decision = PolicyDecision(outcome=PolicyOutcome.ALLOW)
    context = {
        "compliance_snapshot": {
            "status": "PENDING_REVIEW",
            "deployment_id": "deploy_pending",
        }
    }

    should_continue, result = await compliance_auditor.audit(
        context=context,
        run_id="run_deny_2",
        workspace_id="ws_1",
        tool_call_id="call_1",
        checkpoint_ref="ckpt_1",
        capability_id="test.cap",
        current_decision=decision,
        payload_hash="hash_1",
    )

    assert should_continue is False
    assert result.status == "denied"
    assert result.tool_call_id == "call_1"
