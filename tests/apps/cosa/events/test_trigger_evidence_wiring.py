"""Task 4.3: TriggerPolicyService.resolve() re-checks eval/promotion evidence
for proposal/write rules — stale/absent evidence -> policy_denied."""
import pytest

from agent.evals.promotion import PromotionEvidence
from agent.evals.promotion_repository import InMemoryPromotionEvidenceRepository
from agent.governance.contracts import PinnedSpecIdentity as GovPinned
from apps.cosa.events.fingerprints import SpecFingerprintProvider
from apps.cosa.events.trigger_policy import EventTriggerRule, PinnedSpecIdentity, TriggerPolicyService

pytestmark = pytest.mark.asyncio

FP_MATCH = {"cosa.agent": "hash_A"}


class _Store:
    def __init__(self, rule):
        self._rule = rule

    async def find(self, ws, et, agg):
        return self._rule


class _Caps:
    def has(self, ws, cap):
        return True


class _Counter:
    async def today(self, ws, rid, aid):
        return 0


class _FP:
    def __init__(self, fps):
        self._fps = fps

    async def current(self, rule):
        return dict(self._fps)


def _rule(mode, evidence_ref):
    return EventTriggerRule(
        rule_id="r1", workspace_id="ws_1", event_type="operations.task.created.v1",
        agent_spec=PinnedSpecIdentity(id="cosa.agent", version="1.0.0", definition_hash="hash_A"),
        mode=mode, max_runs_per_aggregate_per_day=5, required_capabilities=(),
        enabled=True, eval_evidence_ref=evidence_ref, event_schema_version=1,
    )


def _evidence(passed=True, fps=None, boundary="write", schema=1):
    return PromotionEvidence(
        target_ref=GovPinned(spec_kind="agent", spec_id="cosa.agent",
                             spec_version="1.0.0", definition_hash="hash_A"),
        required_eval_run_ids=["run_1"],
        observed_fingerprints=dict(fps or FP_MATCH),
        policy_version="p1", policy_checks_passed=passed,
        check_details={"action_boundary": boundary, "event_schema_version": schema},
    )


async def _svc(rule, evidence=None, fps=FP_MATCH):
    repo = InMemoryPromotionEvidenceRepository()
    if evidence is not None:
        await repo.create(evidence)
        rule = rule.__class__(**{**rule.__dict__, "eval_evidence_ref": evidence.evidence_id})
    return TriggerPolicyService(
        _Store(rule), _Caps(), _Counter(),
        evidence_store=repo, fingerprint_provider=_FP(fps), policy_version="p1",
    )


async def test_artifact_only_rule_accepted_without_evidence():
    svc = await _svc(_rule("artifact_only", None))
    d = await svc.resolve(workspace_id="ws_1", event_type="operations.task.created.v1",
                          aggregate={"type": "task", "id": "t1"})
    assert d.outcome == "accepted"


async def test_proposal_rule_denied_without_evidence():
    svc = await _svc(_rule("proposal", None))
    d = await svc.resolve(workspace_id="ws_1", event_type="operations.task.created.v1",
                          aggregate={"type": "task", "id": "t1"})
    assert d.outcome == "policy_denied" and d.reason == "stale_eval_evidence"


async def test_proposal_rule_denied_on_stale_fingerprint():
    svc = await _svc(_rule("proposal", None), evidence=_evidence(fps={"cosa.agent": "hash_OLD"}),
                     fps={"cosa.agent": "hash_NEW"})
    d = await svc.resolve(workspace_id="ws_1", event_type="operations.task.created.v1",
                          aggregate={"type": "task", "id": "t1"})
    assert d.outcome == "policy_denied"


async def test_proposal_rule_accepted_with_fresh_matching_evidence():
    svc = await _svc(_rule("proposal", None), evidence=_evidence(boundary="write"))
    d = await svc.resolve(workspace_id="ws_1", event_type="operations.task.created.v1",
                          aggregate={"type": "task", "id": "t1"})
    assert d.outcome == "accepted"
