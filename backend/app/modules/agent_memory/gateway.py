from abc import ABC, abstractmethod
from typing import Any, Optional


class AgentMemoryGateway(ABC):
    """Abstraction boundary for Agent Memory (mCOSA V12.3 §145, ADR-MEM-001).

    Domain code (Claude Code capture hooks, future DeepSeek chat context
    building, future LiveKit voice memory) must depend only on this
    interface, never on a concrete adapter or the underlying memory engine's
    own types. This is what lets the engine behind it be replaced (per the
    spec §177 go/no-go gate) without touching any caller.

    Every method is scoped by whatever identifiers the caller passes in
    `query`/`event` dicts (organization_id, project_id, agent_id, human_id,
    classification - spec §159) - the adapter, not this interface, is
    responsible for enforcing that scope before returning results.
    """

    @abstractmethod
    async def capture(self, event: dict) -> None:
        """Record a candidate memory event (spec §196-197). Must never raise
        for a well-formed event - capture failures degrade silently so they
        never block the caller's primary work (spec §210.16)."""

    @abstractmethod
    async def recall(self, query: dict) -> list[dict]:
        """Retrieve top relevant memories for `query` (spec §163-164:
        keyword + semantic + metadata + recency + authority, reranked)."""

    @abstractmethod
    async def search(self, query: dict) -> list[dict]:
        """Broader/less-ranked search than `recall`, for explicit lookups
        (e.g. a Memory Inspector UI, spec §205)."""

    @abstractmethod
    async def get_task_context(self, task_id: str) -> Optional[dict]:
        """Compact resume context for a specific task (spec §148 - the
        primary MEM-1 Claude Code use case)."""

    @abstractmethod
    async def get_scenario(self, scenario_id: str) -> Optional[dict]:
        """Project/task/operating-experience scenario memory (spec §143 L2)."""

    @abstractmethod
    async def get_profile(self, subject_id: str) -> Optional[dict]:
        """Founder/Agent operating-profile *candidate* (spec §143 L3) - never
        treated as confirmed; callers must route through governance before
        writing to the actual Founder Operating Profile (spec §153-154)."""

    @abstractmethod
    async def end_session(self, session_id: str) -> None:
        """Signal a session has ended, triggering async compaction (spec
        §195) - must not block the caller waiting for compaction to finish."""

    @abstractmethod
    async def promote_candidate(self, candidate_id: str) -> dict:
        """Promote a memory candidate toward governed Company Knowledge/SOP
        (spec §166-167). Never automatic - only called after human/governance
        approval of the corresponding `MemoryCandidate` row."""

    @abstractmethod
    async def forget(self, memory_id: str) -> None:
        """Delete a memory (spec §172) - must also remove any synced
        replicas/derived caches the adapter maintains."""

    @abstractmethod
    async def export(self, scope: dict) -> Any:
        """Export memories matching `scope`, for backup or migration between
        adapters (spec §182)."""
