from __future__ import annotations

import os
from typing import Optional, Protocol, runtime_checkable

from agent_core.governance.accumulator import InvocationGovernanceState
from agent_core.governance.contracts import (
    ApprovalEvidence,
    PinnedSpecIdentity,
    PolicyDecision,
    SpecResolutionManifest,
)

__all__ = ["GovernanceStateStore", "get_governance_store"]


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


def get_governance_store(database_url: Optional[str] = None) -> GovernanceStateStore:
    """Production mặc định dùng PostgresGovernanceStateStore — cùng nguyên tắc
    no-silent-fallback đã áp dụng cho get_memory_store()/get_knowledge_store()
    (DB_FINAL_CUTOVER.md §8-9). Muốn in-memory cho test/dev, dùng
    InMemoryGovernanceStateStore() trực tiếp."""
    resolved_url = database_url or os.environ.get("AGENT_CORE_DATABASE_URL")
    if not resolved_url:
        raise RuntimeError(
            "get_governance_store() requires AGENT_CORE_DATABASE_URL to be set — "
            "production must not silently fall back to InMemoryGovernanceStateStore. "
            "For tests/local dev, use InMemoryGovernanceStateStore() directly."
        )
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from agent_core.governance.providers.postgres import PostgresGovernanceStateStore

    engine = create_async_engine(resolved_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return PostgresGovernanceStateStore(db_session_factory=factory)
