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
    ) -> None:
        self.store = store
        self.capabilities = capabilities
        self.run_counter = run_counter

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

        return TriggerDecision(outcome="accepted", rule=rule)
