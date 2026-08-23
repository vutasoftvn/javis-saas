from __future__ import annotations

from typing import Optional

from agent_core.governance.accumulator import InvocationGovernanceState
from agent_core.governance.contracts import (
    ApprovalEvidence,
    PinnedSpecIdentity,
    PolicyDecision,
    SpecResolutionManifest,
)


class InMemoryGovernanceStateStore:
    """Cài đặt GovernanceStateStore không cần Postgres — default cho
    ToolCallStep khi không truyền governance_store, và cho unit test không
    cần DB thật. Cùng 6 method với PostgresGovernanceStateStore
    (packages/agent_core/governance/providers/postgres.py) để 2 cài đặt
    hoán đổi được cho nhau qua Protocol GovernanceStateStore."""

    def __init__(self) -> None:
        self._manifests: dict[str, SpecResolutionManifest] = {}
        self._states: dict[tuple[str, str], InvocationGovernanceState] = {}
        self._evidence: dict[str, list[ApprovalEvidence]] = {}

    async def save_manifest_entry(self, run_id: str, entry: PinnedSpecIdentity) -> None:
        manifest = self._manifests.get(run_id, SpecResolutionManifest())
        self._manifests[run_id] = manifest.with_entry(entry)

    async def load_manifest(self, run_id: str) -> SpecResolutionManifest:
        return self._manifests.get(run_id, SpecResolutionManifest())

    async def save_governance_state(
        self, state: InvocationGovernanceState, *, observation: PolicyDecision, source: str
    ) -> None:
        self._states[(state.run_id, state.tool_call_id)] = state

    async def load_governance_state(
        self, run_id: str, tool_call_id: str
    ) -> Optional[InvocationGovernanceState]:
        return self._states.get((run_id, tool_call_id))

    async def save_evidence(self, evidence: ApprovalEvidence) -> None:
        self._evidence.setdefault(evidence.scope, []).append(evidence)

    async def list_evidence(self, scope: str) -> list[ApprovalEvidence]:
        return list(self._evidence.get(scope, []))
