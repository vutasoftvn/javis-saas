"""ComplianceCoordination — narrower interface for compliance orchestration."""

from __future__ import annotations

from typing import Any

from agent.capabilities.registry import CapabilityRegistry
from agent.governance.store import GovernanceStateStore


class ComplianceCoordination:
    """Encapsulates compliance-related dependencies (policy engine, capability registry, governance store, compliance resolver)."""

    def __init__(
        self,
        policy_engine: Any,
        capability_registry: CapabilityRegistry,
        governance_store: GovernanceStateStore,
        compliance_resolver: Any | None = None,
    ) -> None:
        self.policy_engine = policy_engine
        self.capability_registry = capability_registry
        self.governance_store = governance_store
        self.compliance_resolver = compliance_resolver


class IComplianceCoordination:
    """Public interface for consumers — type hint only."""

    policy_engine: Any
    capability_registry: CapabilityRegistry
    governance_store: GovernanceStateStore
    compliance_resolver: Any | None
