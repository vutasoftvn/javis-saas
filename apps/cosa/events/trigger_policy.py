from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional, Protocol, Tuple


@dataclass(frozen=True)
class PinnedSpecIdentity:
    id: str
    version: str
    definition_hash: str


@dataclass(frozen=True)
class EventTriggerRule:
    rule_id: str
    workspace_id: str
    event_type: str
    agent_spec: PinnedSpecIdentity
    mode: Literal["artifact_only", "proposal", "write"]
    max_runs_per_aggregate_per_day: int
    required_capabilities: Tuple[str, ...]
    aggregate_filter: Optional[dict] = None
    owner: str = "operator"
    enabled: bool = False
    eval_evidence_ref: Optional[str] = None
    event_schema_version: int = 1


@dataclass(frozen=True)
class TriggerDecision:
    outcome: Literal["accepted", "ignored_rule_disabled", "policy_denied"]
    rule: Optional[EventTriggerRule] = None
    reason: Optional[str] = None


class TriggerRuleStoreProtocol(Protocol):
    async def find(self, workspace_id: str, event_type: str, aggregate: dict) -> Optional[EventTriggerRule]:
        ...


class RunCounterProtocol(Protocol):
    async def today(self, workspace_id: str, rule_id: str, aggregate_id: str) -> int:
        ...


class CapabilityCheckerProtocol(Protocol):
    def has(self, workspace_id: str, capability: str) -> bool:
        ...


class TriggerPolicyService:
    def __init__(
        self,
        store: Any,
        capabilities: Any,
        run_counter: Any,
        *,
        evidence_store: Any = None,
        fingerprint_provider: Any = None,
        policy_version: str = "p1",
    ) -> None:
        self.store = store
        self.capabilities = capabilities
        self.run_counter = run_counter
        # P1 Task 8: khi cả hai được wire, resolve() re-check eval/promotion
        # evidence cho rule proposal/write. Chưa wire ⇒ bỏ qua (backward-compat).
        self.evidence_store = evidence_store
        self.fingerprint_provider = fingerprint_provider
        self.policy_version = policy_version

    async def resolve(
        self,
        *,
        workspace_id: str,
        event_type: str,
        aggregate: dict,
    ) -> TriggerDecision:
        rule: Optional[EventTriggerRule] = await self.store.find(workspace_id, event_type, aggregate)
        if rule is None or not rule.enabled:
            return TriggerDecision(outcome="ignored_rule_disabled")

        aggregate_id = aggregate.get("id", "")
        runs_today = await self.run_counter.today(workspace_id, rule.rule_id, aggregate_id)
        if runs_today >= rule.max_runs_per_aggregate_per_day:
            return TriggerDecision(outcome="policy_denied", reason="rate_limited")

        missing = [c for c in rule.required_capabilities if not self.capabilities.has(workspace_id, c)]
        if missing:
            return TriggerDecision(outcome="policy_denied", reason=f"missing_capability:{missing[0]}")

        # P1 Task 8: rule proposal/write phải có immutable eval/promotion evidence
        # khớp fingerprint hiện tại. artifact_only không có side effect ⇒ bỏ qua.
        if rule.mode != "artifact_only" and self.evidence_store is not None and self.fingerprint_provider is not None:
            from apps.cosa.events.trigger_promotion import can_enable_trigger

            evidence = None
            if rule.eval_evidence_ref:
                evidence = await self.evidence_store.load(rule.eval_evidence_ref)
            fingerprints = await self.fingerprint_provider.current(rule)
            gate = can_enable_trigger(rule, evidence, fingerprints, policy_version=self.policy_version)
            if not gate.allowed:
                return TriggerDecision(outcome="policy_denied", reason="stale_eval_evidence")

        return TriggerDecision(outcome="accepted", rule=rule)
