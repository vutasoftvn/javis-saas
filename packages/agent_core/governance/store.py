from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from agent_core.governance.accumulator import InvocationGovernanceState
from agent_core.governance.contracts import (
    ApprovalEvidence,
    PinnedSpecIdentity,
    PolicyDecision,
    SpecResolutionManifest,
)


@runtime_checkable
class GovernanceStateStore(Protocol):
    """Durable persistence contract cho Identity Plane (SpecResolutionManifest)
    và Governance Plane (InvocationGovernanceState + ApprovalEvidence) — cùng
    mẫu Protocol với agentos/memory/base.py::MemoryStore và
    agentos/knowledge/store.py::KnowledgeStore."""

    async def save_manifest_entry(self, run_id: str, entry: PinnedSpecIdentity) -> None: ...

    async def load_manifest(self, run_id: str) -> SpecResolutionManifest: ...

    async def save_governance_state(
        self, state: InvocationGovernanceState, *, observation: PolicyDecision, source: str
    ) -> None: ...

    async def load_governance_state(
        self, run_id: str, tool_call_id: str
    ) -> Optional[InvocationGovernanceState]: ...

    async def save_evidence(self, evidence: ApprovalEvidence) -> None: ...

    async def list_evidence(self, scope: str) -> list[ApprovalEvidence]: ...
